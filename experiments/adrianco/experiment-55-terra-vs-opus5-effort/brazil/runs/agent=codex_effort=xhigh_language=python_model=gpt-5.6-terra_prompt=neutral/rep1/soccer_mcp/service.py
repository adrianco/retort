"""In-memory, read-only query service for the bundled Brazilian soccer CSV data."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from .normalization import display_team, normalize_competition, normalize_team, normalize_text


_DATA_FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "brazilian_cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "extended_statistics": "BR-Football-Dataset.csv",
    "historical_brasileirao": "novo_campeonato_brasileiro.csv",
    "fifa_players": "fifa_data.csv",
}

_SOURCE_NAMES = {
    "brasileirao": "Brasileirão matches",
    "brazilian_cup": "Copa do Brasil matches",
    "libertadores": "Copa Libertadores matches",
    "extended_statistics": "Extended match statistics",
    "historical_brasileirao": "Historical Brasileirão",
    "fifa_players": "FIFA player database",
}

_SOURCE_ALIASES = {
    "brasileirao": "brasileirao",
    "brasileirao matches": "brasileirao",
    "brasileirao matches csv": "brasileirao",
    "brazilian cup": "brazilian_cup",
    "copa do brasil": "brazilian_cup",
    "libertadores": "libertadores",
    "extended": "extended_statistics",
    "extended statistics": "extended_statistics",
    "br football dataset": "extended_statistics",
    "historical": "historical_brasileirao",
    "historical brasileirao": "historical_brasileirao",
}

_PLAYER_ATTRIBUTES = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
    "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
    "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength",
    "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


@dataclass(frozen=True, slots=True)
class Match:
    source: str
    competition: str
    match_date: date | None
    season: int | None
    round: str | None
    stage: str | None
    home_team: str
    away_team: str
    home_key: str
    away_key: str
    home_goal: int | None
    away_goal: int | None
    details: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "date": self.match_date.isoformat() if self.match_date else None,
            "season": self.season,
            "competition": self.competition,
            "round": self.round,
            "stage": self.stage,
            "home_team": display_team(self.home_team),
            "away_team": display_team(self.away_team),
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "source": self.source,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload

    @property
    def is_completed(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _integer(value: object | None) -> int | None:
    text = _clean(value)
    if text is None or text.casefold() in {"nan", "na", "none", "null"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _parse_date(value: object | None) -> date | None:
    text = _clean(value)
    if text is None or text.casefold() in {"nan", "na"}:
        return None
    for pattern in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _query_date(value: str | date | None, argument: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    parsed = _parse_date(value)
    if parsed is None:
        raise ValueError(f"{argument} must be an ISO date (YYYY-MM-DD) or DD/MM/YYYY")
    return parsed


def _number_or_text(value: object | None) -> int | str | None:
    number = _integer(value)
    return number if number is not None else _clean(value)


class SoccerData:
    """Loaded data plus query operations suitable for direct use or MCP tools."""

    def __init__(self, matches: Iterable[Match], players: Iterable[Mapping[str, Any]], source_counts: Mapping[str, int]):
        self.matches = tuple(matches)
        self.players = tuple(dict(player) for player in players)
        self.source_counts = dict(source_counts)

    @classmethod
    def load(cls, data_dir: str | Path | None = None) -> "SoccerData":
        """Load and cache all six required CSV files from *data_dir*."""
        directory = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data" / "kaggle"
        return _load_cached(str(directory.resolve()))

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the process-wide CSV cache; useful for applications replacing data files."""
        _load_cached.cache_clear()

    def data_summary(self) -> dict[str, Any]:
        """Return dataset coverage and loaded record counts."""
        return {
            "match_count": len(self.matches),
            "player_count": len(self.players),
            "sources": [
                {"id": source, "name": _SOURCE_NAMES[source], "records": count}
                for source, count in self.source_counts.items()
            ],
        }

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | str | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        stage: str | None = None,
        round: str | int | None = None,
        source: str | None = None,
        limit: int = 50,
        order: str = "desc",
        include_duplicates: bool = False,
    ) -> dict[str, Any]:
        """Search matches by team, opponent, competition, season, date, and source."""
        if limit < 1 or limit > 1_000:
            raise ValueError("limit must be between 1 and 1000")
        if order not in {"asc", "desc"}:
            raise ValueError("order must be either 'asc' or 'desc'")

        team_key = normalize_team(team) if team else None
        opponent_key = normalize_team(opponent) if opponent else None
        wanted_competition = normalize_competition(competition) if competition else None
        wanted_season = _integer(season)
        if season is not None and wanted_season is None:
            raise ValueError("season must be a four-digit year")
        start = _query_date(date_from, "date_from")
        end = _query_date(date_to, "date_to")
        if start and end and start > end:
            raise ValueError("date_from must not be later than date_to")
        source_id = self._source_id(source)

        matches = [
            match for match in self.matches
            if self._matches_filters(
                match, team_key, opponent_key, wanted_competition, wanted_season,
                start, end, stage, round, source_id,
            )
        ]
        matches = self._deduplicated(matches) if not include_duplicates else matches
        matches.sort(key=self._match_sort_key, reverse=order == "desc")
        total = len(matches)
        shown = matches[:limit]
        return {
            "count": total,
            "returned": len(shown),
            "filters": {
                "team": team,
                "opponent": opponent,
                "competition": wanted_competition,
                "season": wanted_season,
                "date_from": start.isoformat() if start else None,
                "date_to": end.isoformat() if end else None,
                "stage": stage,
                "round": str(round) if round is not None else None,
                "source": source_id,
                "include_duplicates": include_duplicates,
            },
            "matches": [match.as_dict() for match in shown],
        }

    def team_statistics(
        self,
        team: str,
        season: int | str | None = None,
        competition: str | None = None,
        venue: str = "all",
        source: str | None = None,
        include_duplicates: bool = False,
    ) -> dict[str, Any]:
        """Calculate wins, draws, losses, and goals for a club."""
        if not team or not normalize_team(team):
            raise ValueError("team is required")
        if venue not in {"all", "home", "away"}:
            raise ValueError("venue must be 'all', 'home', or 'away'")
        team_key = normalize_team(team)
        matches = self._filtered_matches(
            team=team_key,
            competition=competition,
            season=season,
            source=source,
            include_duplicates=include_duplicates,
        )
        if venue == "home":
            matches = [match for match in matches if match.home_key == team_key]
        elif venue == "away":
            matches = [match for match in matches if match.away_key == team_key]
        record = self._record_for_team(team_key, matches)
        return {
            "team": self._team_label(team_key, team),
            "venue": venue,
            "competition": normalize_competition(competition) if competition else None,
            "season": _integer(season) if season is not None else None,
            "matches_found": len(matches),
            "record": record,
        }

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | str | None = None,
        source: str | None = None,
        limit: int = 50,
        include_duplicates: bool = False,
    ) -> dict[str, Any]:
        """Compare two teams, including their match list and record in the loaded data."""
        if not team_a or not team_b:
            raise ValueError("team_a and team_b are required")
        first_key, second_key = normalize_team(team_a), normalize_team(team_b)
        if first_key == second_key:
            raise ValueError("team_a and team_b must identify different teams")
        matches = self._filtered_matches(
            team=first_key,
            opponent=second_key,
            competition=competition,
            season=season,
            source=source,
            include_duplicates=include_duplicates,
        )
        matches.sort(key=self._match_sort_key, reverse=True)
        first = self._record_for_team(first_key, matches)
        second = self._record_for_team(second_key, matches)
        return {
            "team_a": self._team_label(first_key, team_a),
            "team_b": self._team_label(second_key, team_b),
            "matches_found": len(matches),
            "record": {
                "team_a_wins": first["wins"],
                "team_b_wins": second["wins"],
                "draws": first["draws"],
                "team_a_goals": first["goals_for"],
                "team_b_goals": second["goals_for"],
            },
            "matches": [match.as_dict() for match in matches[:limit]],
        }

    def team_overview(
        self,
        team: str,
        season: int | str | None = None,
        competition: str | None = None,
        source: str | None = None,
        match_limit: int = 10,
        player_limit: int = 20,
    ) -> dict[str, Any]:
        """Combine a club's match record, competitions, players, and recent matches.

        This is the cross-file query: its player list comes from the FIFA CSV,
        while the other sections come from the match CSVs.
        """
        if not team or not normalize_team(team):
            raise ValueError("team is required")
        if match_limit < 1 or player_limit < 1:
            raise ValueError("match_limit and player_limit must both be positive")
        team_key = normalize_team(team)
        matches = self._filtered_matches(
            team=team_key,
            competition=competition,
            season=season,
            source=source,
        )
        competitions: dict[str, int] = Counter(match.competition for match in matches)
        return {
            "team": self._team_label(team_key, team),
            "statistics": self.team_statistics(team, season, competition, source=source),
            "competitions": [
                {"competition": name, "matches": count}
                for name, count in sorted(competitions.items(), key=lambda item: (-item[1], item[0]))
            ],
            "players": self.search_players(club=team, limit=player_limit),
            "recent_matches": self.search_matches(
                team=team,
                competition=competition,
                season=season,
                source=source,
                limit=match_limit,
            ),
        }

    def competition_standings(
        self,
        competition: str = "Brasileirão",
        season: int | str | None = None,
        source: str | None = None,
        limit: int = 50,
        include_duplicates: bool = False,
    ) -> dict[str, Any]:
        """Calculate a points table from completed match results."""
        if season is None:
            raise ValueError("season is required to calculate a standings table")
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        wanted_season = _integer(season)
        if wanted_season is None:
            raise ValueError("season must be a four-digit year")
        matches = self._filtered_matches(
            competition=competition,
            season=wanted_season,
            source=source,
            include_duplicates=include_duplicates,
        )
        table: dict[str, dict[str, Any]] = {}
        for match in matches:
            if not match.is_completed:
                continue
            for key in (match.home_key, match.away_key):
                table.setdefault(key, self._empty_table_row(self._team_label(key, key)))
            home, away = table[match.home_key], table[match.away_key]
            self._add_table_result(home, match.home_goal, match.away_goal)
            self._add_table_result(away, match.away_goal, match.home_goal)

        standings = sorted(
            table.values(),
            key=lambda row: (-row["points"], -row["goal_difference"], -row["goals_for"], -row["wins"], row["team"]),
        )
        for rank, row in enumerate(standings, start=1):
            row["rank"] = rank
        return {
            "competition": normalize_competition(competition),
            "season": wanted_season,
            "matches_used": sum(1 for match in matches if match.is_completed),
            "champion": standings[0]["team"] if standings else None,
            "standings": standings[:limit],
        }

    def competition_statistics(
        self,
        competition: str | None = None,
        season: int | str | None = None,
        source: str | None = None,
        include_duplicates: bool = False,
        biggest_wins_limit: int = 10,
    ) -> dict[str, Any]:
        """Aggregate goal rates, result rates, biggest wins, and home/away records."""
        if biggest_wins_limit < 1 or biggest_wins_limit > 100:
            raise ValueError("biggest_wins_limit must be between 1 and 100")
        matches = self._filtered_matches(
            competition=competition,
            season=season,
            source=source,
            include_duplicates=include_duplicates,
        )
        completed = [match for match in matches if match.is_completed]
        total_goals = sum(match.home_goal + match.away_goal for match in completed)  # type: ignore[operator]
        home_wins = sum(match.home_goal > match.away_goal for match in completed)  # type: ignore[operator]
        away_wins = sum(match.home_goal < match.away_goal for match in completed)  # type: ignore[operator]
        draws = len(completed) - home_wins - away_wins
        home_records: dict[str, dict[str, Any]] = {}
        away_records: dict[str, dict[str, Any]] = {}
        goal_totals: Counter[str] = Counter()
        for match in completed:
            home_records.setdefault(match.home_key, self._empty_record())
            away_records.setdefault(match.away_key, self._empty_record())
            self._add_record(home_records[match.home_key], match.home_goal, match.away_goal)  # type: ignore[arg-type]
            self._add_record(away_records[match.away_key], match.away_goal, match.home_goal)  # type: ignore[arg-type]
            goal_totals[match.home_key] += match.home_goal  # type: ignore[operator]
            goal_totals[match.away_key] += match.away_goal  # type: ignore[operator]
        biggest = sorted(
            completed,
            key=lambda match: (
                abs(match.home_goal - match.away_goal),  # type: ignore[operator]
                match.home_goal + match.away_goal,  # type: ignore[operator]
                self._match_sort_key(match),
            ),
            reverse=True,
        )[:biggest_wins_limit]
        return {
            "competition": normalize_competition(competition) if competition else None,
            "season": _integer(season) if season is not None else None,
            "matches_found": len(matches),
            "completed_matches": len(completed),
            "total_goals": total_goals,
            "average_goals_per_match": round(total_goals / len(completed), 3) if completed else 0.0,
            "home_win_rate": self._percent(home_wins, len(completed)),
            "away_win_rate": self._percent(away_wins, len(completed)),
            "draw_rate": self._percent(draws, len(completed)),
            "best_home_record": self._best_record(home_records),
            "best_away_record": self._best_record(away_records),
            "top_scoring_teams": [
                {"team": self._team_label(key, key), "goals": goals}
                for key, goals in goal_totals.most_common(10)
            ],
            "biggest_wins": [match.as_dict() for match in biggest],
        }

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search FIFA player records by identity, nationality, club, position, and rating."""
        if limit < 1 or limit > 1_000:
            raise ValueError("limit must be between 1 and 1000")
        if min_overall is not None and not 0 <= min_overall <= 100:
            raise ValueError("min_overall must be between 0 and 100")
        name_key = normalize_text(name)
        nationality_key = normalize_text(nationality)
        if nationality_key in {"brazilian", "brasileiro", "brasileira"}:
            nationality_key = "brazil"
        club_key = normalize_text(club)
        position_key = normalize_text(position)
        players = [
            player for player in self.players
            if (not name_key or name_key in normalize_text(player["name"]))
            and (not nationality_key or nationality_key in normalize_text(player["nationality"]))
            and (not club_key or self._club_matches(player["club"], club_key))
            and self._position_matches(player["position"], position_key)
            and (min_overall is None or (player["overall"] is not None and player["overall"] >= min_overall))
        ]
        players.sort(key=lambda player: (player["overall"] is not None, player["overall"] or -1, player["potential"] or -1, player["name"]), reverse=True)
        return {
            "count": len(players),
            "returned": min(len(players), limit),
            "filters": {
                "name": name,
                "nationality": nationality,
                "club": club,
                "position": position,
                "min_overall": min_overall,
            },
            "players": [self._public_player(player) for player in players[:limit]],
        }

    def answer_question(self, question: str, limit: int = 20) -> dict[str, Any]:
        """Route common English or Portuguese soccer questions to a structured query."""
        if not question or not question.strip():
            raise ValueError("question is required")
        text = normalize_text(question)
        competition = self._competition_in_text(text)
        season = self._season_in_text(text)
        teams = self._teams_in_text(text)

        if any(phrase in text for phrase in ("who won", "winner", "champion", "quem ganhou", "campeao")) and season:
            result = self.competition_standings(competition or "Brasileirão", season, limit=limit)
            return {"intent": "competition_standings", "answer": result}
        if any(phrase in text for phrase in ("standings", "table", "classificacao", "tabela")) and season:
            result = self.competition_standings(competition or "Brasileirão", season, limit=limit)
            return {"intent": "competition_standings", "answer": result}
        if any(phrase in text for phrase in ("average goals", "biggest win", "best away", "most goals", "media de gols", "maior vitoria", "melhor visitante")):
            result = self.competition_statistics(competition, season, biggest_wins_limit=limit)
            return {"intent": "competition_statistics", "answer": result}
        if len(teams) >= 2 and any(phrase in text for phrase in ("head to head", "compare", "versus", " vs ", " contra ")):
            result = self.head_to_head(teams[0], teams[1], competition, season, limit=limit)
            return {"intent": "head_to_head", "answer": result}
        if teams and any(phrase in text for phrase in ("home record", "record at home", "mandante")):
            result = self.team_statistics(teams[0], season, competition, venue="home")
            return {"intent": "team_statistics", "answer": result}
        if teams and any(phrase in text for phrase in ("last play", "last match", "ultimo jogo", "ultima partida")):
            result = self.search_matches(teams[0], teams[1] if len(teams) > 1 else None, competition, season, limit=1)
            return {"intent": "latest_match", "answer": result}
        if any(word in text for word in (
            "player", "players", "jogador", "jogadores", "who is", "forward", "forwards",
            "striker", "strikers", "atacante", "atacantes",
        )):
            club = teams[0] if teams and any(word in text for word in ("play for", " at ", "do ", "da ", "from ", "de ")) else None
            name = None if club else self._person_candidate(question)
            nationality = "Brazilian" if any(word in text for word in ("brazilian", "brasileiro", "brasileira")) else None
            position = "forward" if any(word in text for word in ("forward", "forwards", "striker", "strikers", "atacante", "atacantes")) else None
            result = self.search_players(name=name, club=club, nationality=nationality, position=position, limit=limit)
            return {"intent": "player_search", "answer": result}
        if teams:
            result = self.search_matches(teams[0], teams[1] if len(teams) > 1 else None, competition, season, limit=limit)
            return {"intent": "match_search", "answer": result}
        return {
            "intent": "unresolved",
            "answer": None,
            "message": "I could not determine a supported query. Use search_matches, team_statistics, search_players, or competition_standings.",
        }

    def _filtered_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | str | None = None,
        source: str | None = None,
        include_duplicates: bool = False,
    ) -> list[Match]:
        team_key = normalize_team(team) if team else None
        opponent_key = normalize_team(opponent) if opponent else None
        wanted_season = _integer(season)
        if season is not None and wanted_season is None:
            raise ValueError("season must be a four-digit year")
        matches = [
            match for match in self.matches
            if self._matches_filters(
                match, team_key, opponent_key,
                normalize_competition(competition) if competition else None,
                wanted_season, None, None, None, None, self._source_id(source),
            )
        ]
        if include_duplicates:
            return matches
        # Several files intentionally cover the same top-flight fixtures. For
        # statistics, counting every source would turn a 38-match season into
        # a 100+ match season. Use the dedicated competition file where it is
        # available, while still allowing callers to select any source.
        if source is None:
            matches = self._canonical_statistical_matches(matches)
        return self._deduplicated(matches)

    @staticmethod
    def _canonical_statistical_matches(matches: Iterable[Match]) -> list[Match]:
        """Choose one authoritative source per competition/season group.

        The separate extended-statistics CSV duplicates many Serie A and Copa
        do Brasil results. Dedicated competition files take precedence, then
        the historical Brasileirão file, and finally the extended file for
        competitions that exist only there (for example Serie B).
        """
        grouped: dict[tuple[str, int | None], list[Match]] = defaultdict(list)
        for match in matches:
            grouped[(match.competition, match.season)].append(match)

        preferred_sources = {
            "Brasileirão Série A": ("brasileirao", "historical_brasileirao", "extended_statistics"),
            "Copa do Brasil": ("brazilian_cup", "extended_statistics"),
            "Copa Libertadores": ("libertadores", "extended_statistics"),
        }
        selected: list[Match] = []
        for (competition, _), group in grouped.items():
            preference = preferred_sources.get(competition, ("extended_statistics",))
            chosen_source = next((candidate for candidate in preference if any(match.source == candidate for match in group)), None)
            if chosen_source:
                selected.extend(match for match in group if match.source == chosen_source)
            else:
                selected.extend(group)
        return selected

    @staticmethod
    def _matches_filters(
        match: Match,
        team_key: str | None,
        opponent_key: str | None,
        competition: str | None,
        season: int | None,
        start: date | None,
        end: date | None,
        stage: str | None,
        round_value: str | int | None,
        source: str | None,
    ) -> bool:
        if team_key and team_key not in {match.home_key, match.away_key}:
            return False
        if opponent_key:
            if not team_key or {match.home_key, match.away_key} != {team_key, opponent_key}:
                return False
        if competition and normalize_competition(match.competition) != competition:
            return False
        if season is not None and match.season != season:
            return False
        if start and (match.match_date is None or match.match_date < start):
            return False
        if end and (match.match_date is None or match.match_date > end):
            return False
        if stage and normalize_text(stage) not in normalize_text(match.stage):
            return False
        if round_value is not None and normalize_text(round_value) != normalize_text(match.round):
            return False
        return not source or match.source == source

    def _source_id(self, source: str | None) -> str | None:
        if source is None or not str(source).strip() or normalize_text(source) == "all":
            return None
        normalized = normalize_text(source)
        source_id = _SOURCE_ALIASES.get(normalized, normalized.replace(" ", "_"))
        if source_id not in _SOURCE_NAMES or source_id == "fifa_players":
            raise ValueError(f"unknown match source '{source}'. See data_summary for source IDs.")
        return source_id

    @staticmethod
    def _match_sort_key(match: Match) -> tuple[date, str, str]:
        return (match.match_date or date.min, match.home_team, match.away_team)

    @staticmethod
    def _deduplicated(matches: Iterable[Match]) -> list[Match]:
        seen: set[tuple[Any, ...]] = set()
        unique: list[Match] = []
        for match in matches:
            key = (
                match.competition, match.match_date, match.home_key, match.away_key,
                match.home_goal, match.away_goal,
            )
            if key not in seen:
                seen.add(key)
                unique.append(match)
        return unique

    @staticmethod
    def _empty_record() -> dict[str, Any]:
        return {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}

    @classmethod
    def _record_for_team(cls, team_key: str, matches: Iterable[Match]) -> dict[str, Any]:
        record = cls._empty_record()
        for match in matches:
            if not match.is_completed:
                continue
            if match.home_key == team_key:
                cls._add_record(record, match.home_goal, match.away_goal)  # type: ignore[arg-type]
            elif match.away_key == team_key:
                cls._add_record(record, match.away_goal, match.home_goal)  # type: ignore[arg-type]
        record["goal_difference"] = record["goals_for"] - record["goals_against"]
        record["win_rate"] = cls._percent(record["wins"], record["matches"])
        return record

    @staticmethod
    def _add_record(record: dict[str, Any], goals_for: int, goals_against: int) -> None:
        record["matches"] += 1
        record["goals_for"] += goals_for
        record["goals_against"] += goals_against
        if goals_for > goals_against:
            record["wins"] += 1
        elif goals_for < goals_against:
            record["losses"] += 1
        else:
            record["draws"] += 1

    @staticmethod
    def _percent(numerator: int, denominator: int) -> float:
        return round(100 * numerator / denominator, 1) if denominator else 0.0

    @staticmethod
    def _empty_table_row(team: str) -> dict[str, Any]:
        return {
            "team": team, "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "goal_difference": 0, "points": 0,
        }

    @staticmethod
    def _add_table_result(row: dict[str, Any], goals_for: int, goals_against: int) -> None:
        row["played"] += 1
        row["goals_for"] += goals_for
        row["goals_against"] += goals_against
        if goals_for > goals_against:
            row["wins"] += 1
            row["points"] += 3
        elif goals_for == goals_against:
            row["draws"] += 1
            row["points"] += 1
        else:
            row["losses"] += 1
        row["goal_difference"] = row["goals_for"] - row["goals_against"]

    def _best_record(self, records: Mapping[str, Mapping[str, Any]]) -> dict[str, Any] | None:
        if not records:
            return None
        key, record = max(
            records.items(),
            key=lambda item: (
                item[1]["wins"] / item[1]["matches"] if item[1]["matches"] else -1,
                item[1]["points"] if "points" in item[1] else item[1]["wins"] * 3 + item[1]["draws"],
                item[1]["goals_for"] - item[1]["goals_against"],
                item[1]["goals_for"],
            ),
        )
        response = dict(record)
        response["team"] = self._team_label(key, key)
        response["win_rate"] = self._percent(response["wins"], response["matches"])
        return response

    def _team_label(self, team_key: str, fallback: str) -> str:
        for match in self.matches:
            if match.home_key == team_key:
                return display_team(match.home_team)
            if match.away_key == team_key:
                return display_team(match.away_team)
        return display_team(fallback)

    @staticmethod
    def _position_matches(player_position: str, requested: str) -> bool:
        if not requested:
            return True
        actual = normalize_text(player_position)
        groups = {
            "forward": {"st", "cf", "lw", "rw", "lf", "rf"},
            "attacker": {"st", "cf", "lw", "rw", "lf", "rf"},
            "midfielder": {"cam", "cm", "cdm", "lm", "rm", "lam", "ram", "lcm", "rcm", "ldm", "rdm"},
            "defender": {"cb", "lb", "rb", "lcb", "rcb", "lwb", "rwb"},
            "goalkeeper": {"gk"},
            "keeper": {"gk"},
        }
        return actual in groups.get(requested, {requested})

    @staticmethod
    def _club_matches(player_club: str, requested_key: str) -> bool:
        """Use club aliases where possible, with substring matching as a fallback."""
        return requested_key in normalize_text(player_club) or normalize_team(player_club) == requested_key

    @staticmethod
    def _public_player(player: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": player["id"],
            "name": player["name"],
            "age": player["age"],
            "nationality": player["nationality"],
            "overall": player["overall"],
            "potential": player["potential"],
            "club": player["club"],
            "position": player["position"],
            "jersey_number": player["jersey_number"],
            "height": player["height"],
            "weight": player["weight"],
            "attributes": dict(player["attributes"]),
        }

    def _competition_in_text(self, text: str) -> str | None:
        for phrase, competition in (
            ("libertadores", "Copa Libertadores"),
            ("copa do brasil", "Copa do Brasil"),
            ("brasileirao", "Brasileirão Série A"),
            ("serie a", "Brasileirão Série A"),
        ):
            if phrase in text:
                return competition
        return None

    @staticmethod
    def _season_in_text(text: str) -> int | None:
        for word in text.split():
            if len(word) == 4 and word.isdigit() and 1900 <= int(word) <= 2100:
                return int(word)
        return None

    def _teams_in_text(self, text: str) -> list[str]:
        candidates: dict[str, str] = {}
        for match in self.matches:
            candidates.setdefault(match.home_key, display_team(match.home_team))
            candidates.setdefault(match.away_key, display_team(match.away_team))
        padded = f" {text} "
        found: list[tuple[int, str, str]] = []
        for key, label in candidates.items():
            if len(key) >= 4 and f" {key} " in padded:
                found.append((len(key), key, label))
        found.sort(reverse=True)
        selected: list[str] = []
        occupied: list[str] = []
        for _, key, label in found:
            if key not in occupied and not any(key in previous for previous in occupied):
                selected.append(label)
                occupied.append(key)
        return selected

    @staticmethod
    def _person_candidate(question: str) -> str | None:
        # Handles compact forms such as "Who is Gabriel Barbosa?" without
        # pretending to provide open-ended natural-language understanding.
        lowered = question.strip().rstrip("?!. ")
        for prefix in ("who is ", "quem e ", "quem é ", "find player "):
            if lowered.casefold().startswith(prefix):
                return lowered[len(prefix):].strip() or None
        return None


@lru_cache(maxsize=8)
def _load_cached(directory_text: str) -> SoccerData:
    directory = Path(directory_text)
    missing = [filename for filename in _DATA_FILES.values() if not (directory / filename).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required CSV file(s) in {directory}: {', '.join(missing)}")

    matches: list[Match] = []
    source_counts: dict[str, int] = {}
    for source in ("brasileirao", "brazilian_cup", "libertadores", "extended_statistics", "historical_brasileirao"):
        rows = _read_rows(directory / _DATA_FILES[source])
        source_counts[source] = len(rows)
        matches.extend(_matches_from_rows(source, rows))
    player_rows = _read_rows(directory / _DATA_FILES["fifa_players"])
    source_counts["fifa_players"] = len(player_rows)
    return SoccerData(matches, (_player_from_row(row) for row in player_rows), source_counts)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _matches_from_rows(source: str, rows: Iterable[Mapping[str, str]]) -> list[Match]:
    matches: list[Match] = []
    for row in rows:
        if source == "brasileirao":
            competition, date_value = "Brasileirão Série A", row.get("datetime")
            home, away = row.get("home_team"), row.get("away_team")
            home_goal, away_goal = row.get("home_goal"), row.get("away_goal")
            season, round_value, stage = row.get("season"), row.get("round"), None
            details = {key: _clean(row.get(key)) for key in ("home_team_state", "away_team_state") if _clean(row.get(key))}
        elif source == "brazilian_cup":
            competition, date_value = "Copa do Brasil", row.get("datetime")
            home, away = row.get("home_team"), row.get("away_team")
            home_goal, away_goal = row.get("home_goal"), row.get("away_goal")
            season, round_value, stage, details = row.get("season"), row.get("round"), None, {}
        elif source == "libertadores":
            competition, date_value = "Copa Libertadores", row.get("datetime")
            home, away = row.get("home_team"), row.get("away_team")
            home_goal, away_goal = row.get("home_goal"), row.get("away_goal")
            season, round_value, stage, details = row.get("season"), None, row.get("stage"), {}
        elif source == "extended_statistics":
            competition, date_value = normalize_competition(row.get("tournament")), row.get("date")
            home, away = row.get("home"), row.get("away")
            home_goal, away_goal = row.get("home_goal"), row.get("away_goal")
            parsed_date = _parse_date(date_value)
            season, round_value, stage = str(parsed_date.year) if parsed_date else None, None, None
            detail_fields = {
                "home_corners": "home_corner",
                "away_corners": "away_corner",
                "home_attacks": "home_attack",
                "away_attacks": "away_attack",
                "home_shots": "home_shots",
                "away_shots": "away_shots",
                "total_corners": "total_corners",
                "home_half_time_result": "ht_result",
                "away_half_time_result": "at_result",
                "kickoff_time": "time",
            }
            details = {
                label: _number_or_text(row.get(column))
                for label, column in detail_fields.items()
                if _clean(row.get(column)) is not None
            }
        else:  # historical_brasileirao
            competition, date_value = "Brasileirão Série A", row.get("Data")
            home, away = row.get("Equipe_mandante"), row.get("Equipe_visitante")
            home_goal, away_goal = row.get("Gols_mandante"), row.get("Gols_visitante")
            season, round_value, stage = row.get("Ano"), row.get("Rodada"), None
            details = {
                label: _clean(row.get(column))
                for label, column in (("home_state", "Mandante_UF"), ("away_state", "Visitante_UF"), ("stadium", "Arena"), ("winner", "Vencedor"))
                if _clean(row.get(column))
            }
        home_text, away_text = _clean(home), _clean(away)
        if not home_text or not away_text:
            continue
        parsed_date = _parse_date(date_value)
        parsed_season = _integer(season) or (parsed_date.year if parsed_date else None)
        matches.append(Match(
            source=source,
            competition=competition,
            match_date=parsed_date,
            season=parsed_season,
            round=_clean(round_value),
            stage=_clean(stage),
            home_team=home_text,
            away_team=away_text,
            home_key=normalize_team(home_text),
            away_key=normalize_team(away_text),
            home_goal=_integer(home_goal),
            away_goal=_integer(away_goal),
            details=details,
        ))
    return matches


def _player_from_row(row: Mapping[str, str]) -> dict[str, Any]:
    attributes = {attribute: _integer(row.get(attribute)) for attribute in _PLAYER_ATTRIBUTES if _integer(row.get(attribute)) is not None}
    return {
        "id": _integer(row.get("ID")),
        "name": _clean(row.get("Name")) or "Unknown",
        "age": _integer(row.get("Age")),
        "nationality": _clean(row.get("Nationality")) or "",
        "overall": _integer(row.get("Overall")),
        "potential": _integer(row.get("Potential")),
        "club": _clean(row.get("Club")) or "",
        "position": _clean(row.get("Position")) or "",
        "jersey_number": _integer(row.get("Jersey Number")),
        "height": _clean(row.get("Height")),
        "weight": _clean(row.get("Weight")),
        "attributes": attributes,
    }
