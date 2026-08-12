"""Deterministic query and analytics service used by every MCP tool."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from .models import Match
from .normalize import fold_text, normalize_competition, normalize_team_name, parse_date
from .repository import SoccerRepository


DERBIES = (
    ("Flamengo", "Fluminense", "Fla-Flu"),
    ("Flamengo", "Vasco", "Clássico dos Milhões"),
    ("Flamengo", "Botafogo", "Clássico da Rivalidade"),
    ("Corinthians", "Palmeiras", "Derby Paulista"),
    ("Corinthians", "São Paulo", "Majestoso"),
    ("Palmeiras", "São Paulo", "Choque-Rei"),
    ("Santos", "São Paulo", "San-São"),
    ("Grêmio", "Internacional", "Grenal"),
    ("Atlético Mineiro", "Cruzeiro", "Clássico Mineiro"),
    ("Bahia", "Vitória", "Ba-Vi"),
    ("Athletico Paranaense", "Coritiba", "Athletiba"),
)


class SoccerService:
    """Knowledge-graph style traversal over normalized entities and relationships."""

    def __init__(self, repository: SoccerRepository | None = None) -> None:
        self.repository = repository or SoccerRepository()

    @staticmethod
    def _team_matches(match: Match, team_key: str, side: str = "either") -> bool:
        return {
            "home": match.home_key == team_key,
            "away": match.away_key == team_key,
            "either": match.home_key == team_key or match.away_key == team_key,
        }[side]

    @staticmethod
    def _competition_matches(match: Match, requested: str) -> bool:
        wanted = normalize_competition(requested)
        actual = normalize_competition(match.competition)
        return wanted == actual or wanted in actual or actual in wanted

    @staticmethod
    def _deduplicate(matches: Iterable[Match]) -> list[Match]:
        seen: set[tuple[object, ...]] = set()
        result = []
        for match in matches:
            key = (
                match.date.date(), match.home_key, match.away_key, match.home_goals,
                match.away_goals, normalize_competition(match.competition),
            )
            if key not in seen:
                seen.add(key)
                result.append(match)
        return result

    def _filtered_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        season: int | None = None,
        competition: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        side: str = "either",
        stage: str | None = None,
        source: str | None = None,
        deduplicate: bool = True,
    ) -> list[Match]:
        if side not in {"home", "away", "either"}:
            raise ValueError("side must be 'home', 'away', or 'either'")
        team_key = normalize_team_name(team) if team else None
        opponent_key = normalize_team_name(opponent) if opponent else None
        candidates = self.repository.matches_by_team.get(team_key, []) if team_key else self.repository.matches
        first = parse_date(start_date) if start_date else None
        last = parse_date(end_date) if end_date else None
        stage_key = fold_text(stage)
        found = []
        for match in candidates:
            if team_key and not self._team_matches(match, team_key, side):
                continue
            if opponent_key and not self._team_matches(match, opponent_key):
                continue
            if season is not None and match.season != int(season):
                continue
            if competition and not self._competition_matches(match, competition):
                continue
            if first and match.date.date() < first.date():
                continue
            if last and match.date.date() > last.date():
                continue
            if stage_key and stage_key not in fold_text(" ".join(filter(None, (match.stage, match.round)))):
                continue
            if source and match.source != source:
                continue
            found.append(match)
        return self._deduplicate(found) if deduplicate else list(found)

    @staticmethod
    def _page(items: list[Match], limit: int, offset: int) -> dict[str, object]:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        return {
            "total": len(items),
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < len(items),
            "matches": [match.to_dict() for match in items[offset:offset + limit]],
        }

    def search_matches(self, **criteria: object) -> dict[str, object]:
        limit = int(criteria.pop("limit", 25))
        offset = int(criteria.pop("offset", 0))
        matches = self._filtered_matches(**criteria)
        result = self._page(matches, limit, offset)
        result["criteria"] = criteria
        return result

    def team_statistics(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        side: str = "either",
    ) -> dict[str, object]:
        key = normalize_team_name(team)
        if season is not None and competition:
            canonical, _ = self._canonical_competition_matches(int(season), competition)
            matches = [match for match in canonical if self._team_matches(match, key, side)]
        else:
            matches = self._filtered_matches(team=team, season=season, competition=competition, side=side)
        wins = draws = losses = goals_for = goals_against = 0
        for match in matches:
            home = match.home_key == key
            scored = match.home_goals if home else match.away_goals
            conceded = match.away_goals if home else match.home_goals
            goals_for += scored
            goals_against += conceded
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1
        played = len(matches)
        return {
            "team": team,
            "season": season,
            "competition": competition,
            "venue_filter": side,
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "points": wins * 3 + draws,
            "win_rate": round(wins * 100 / played, 1) if played else 0.0,
        }

    def head_to_head(
        self,
        team1: str,
        team2: str,
        season: int | None = None,
        competition: str | None = None,
        limit: int = 25,
    ) -> dict[str, object]:
        first_key, second_key = normalize_team_name(team1), normalize_team_name(team2)
        matches = self._filtered_matches(team=team1, opponent=team2, season=season, competition=competition)
        first_wins = second_wins = draws = 0
        for match in matches:
            first_goals = match.home_goals if match.home_key == first_key else match.away_goals
            second_goals = match.home_goals if match.home_key == second_key else match.away_goals
            if first_goals > second_goals:
                first_wins += 1
            elif second_goals > first_goals:
                second_wins += 1
            else:
                draws += 1
        page = self._page(matches, limit, 0)
        return {
            "team1": team1,
            "team2": team2,
            "meetings": len(matches),
            "team1_wins": first_wins,
            "team2_wins": second_wins,
            "draws": draws,
            "recent_matches": page["matches"],
            "truncated": page["has_more"],
        }

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        sort_by: str = "overall",
        limit: int = 25,
        offset: int = 0,
    ) -> dict[str, object]:
        name_key, nation_key, club_key = fold_text(name), fold_text(nationality), fold_text(club)
        position_key = fold_text(position)
        position_groups = {
            "forward": {"st", "cf", "lf", "rf", "lw", "rw"},
            "forwards": {"st", "cf", "lf", "rf", "lw", "rw"},
            "midfielder": {"cam", "cm", "cdm", "lm", "rm", "lam", "ram", "lcm", "rcm"},
            "defender": {"cb", "lb", "rb", "lwb", "rwb", "lcb", "rcb"},
            "goalkeeper": {"gk"},
        }
        found = []
        for player in self.repository.players:
            if name_key and name_key not in fold_text(player.name):
                continue
            if nation_key and nation_key not in fold_text(player.nationality):
                continue
            if club_key and club_key not in fold_text(player.club):
                continue
            if position_key:
                allowed = position_groups.get(position_key)
                if (allowed and fold_text(player.position) not in allowed) or (not allowed and position_key != fold_text(player.position)):
                    continue
            if min_overall is not None and (player.overall is None or player.overall < int(min_overall)):
                continue
            found.append(player)
        if sort_by not in {"overall", "potential", "age", "name"}:
            raise ValueError("sort_by must be overall, potential, age, or name")
        found.sort(key=lambda player: (getattr(player, sort_by) is not None, getattr(player, sort_by) or -1), reverse=sort_by != "name")
        limit, offset = max(1, min(int(limit), 200)), max(0, int(offset))
        return {
            "total": len(found),
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < len(found),
            "players": [player.to_dict() for player in found[offset:offset + limit]],
        }

    def _canonical_competition_matches(self, season: int, competition: str) -> tuple[list[Match], str | None]:
        matches = self._filtered_matches(season=season, competition=competition, deduplicate=False)
        if not matches:
            return [], None
        normalized = normalize_competition(competition)
        preferences = {
            "brasileirao serie a": ("Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"),
            "copa do brasil": ("Brazilian_Cup_Matches.csv", "BR-Football-Dataset.csv"),
            "copa libertadores": ("Libertadores_Matches.csv",),
        }
        preferred = preferences.get(normalized, ("BR-Football-Dataset.csv",))
        candidates = []
        for priority, source in enumerate(preferred):
            selected = [match for match in matches if match.source == source]
            if selected:
                candidates.append((len(selected), -priority, selected, source))
        if candidates:
            _, _, selected, source = max(candidates, key=lambda item: (item[0], item[1]))
            return selected, source
        source = matches[0].source
        return [match for match in matches if match.source == source], source

    def standings(self, season: int, competition: str = "Brasileirão Série A", limit: int = 30) -> dict[str, object]:
        matches, source = self._canonical_competition_matches(int(season), competition)
        table: dict[str, dict[str, object]] = defaultdict(lambda: {"played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0, "display": ""})
        for match in matches:
            for key, display, scored, conceded in (
                (match.home_key, match.home_team, match.home_goals, match.away_goals),
                (match.away_key, match.away_team, match.away_goals, match.home_goals),
            ):
                row = table[key]
                row["display"] = display
                row["played"] += 1
                row["goals_for"] += scored
                row["goals_against"] += conceded
                if scored > conceded:
                    row["wins"] += 1
                    row["points"] += 3
                elif scored == conceded:
                    row["draws"] += 1
                    row["points"] += 1
                else:
                    row["losses"] += 1
        rows = []
        for key, row in table.items():
            row = dict(row)
            row["team"] = row.pop("display")
            row["team_key"] = key
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
            rows.append(row)
        rows.sort(key=lambda row: (row["points"], row["wins"], row["goal_difference"], row["goals_for"]), reverse=True)
        for position, row in enumerate(rows, 1):
            row["position"] = position
        return {
            "season": int(season),
            "competition": competition,
            "calculation_source": source,
            "matches_used": len(matches),
            "standings": rows[:max(1, min(int(limit), 100))],
            "note": "League-style table calculated from final scores; knockout competitions do not determine champions by table position.",
        }

    def competition_statistics(self, competition: str | None = None, season: int | None = None) -> dict[str, object]:
        matches = self._filtered_matches(competition=competition, season=season)
        count = len(matches)
        home_wins = sum(match.home_goals > match.away_goals for match in matches)
        away_wins = sum(match.away_goals > match.home_goals for match in matches)
        draws = count - home_wins - away_wins
        total_goals = sum(match.total_goals for match in matches)
        return {
            "competition": competition,
            "season": season,
            "matches": count,
            "total_goals": total_goals,
            "goals_per_match": round(total_goals / count, 3) if count else 0.0,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(home_wins * 100 / count, 1) if count else 0.0,
            "away_win_rate": round(away_wins * 100 / count, 1) if count else 0.0,
        }

    def biggest_victories(self, competition: str | None = None, season: int | None = None, limit: int = 10) -> dict[str, object]:
        matches = self._filtered_matches(competition=competition, season=season)
        matches.sort(key=lambda match: (match.goal_difference, match.total_goals, match.date), reverse=True)
        return {"total_considered": len(matches), "matches": [match.to_dict() for match in matches[:max(1, min(int(limit), 100))]]}

    def best_record(self, side: str, season: int | None = None, competition: str | None = None, min_matches: int = 5, limit: int = 10) -> dict[str, object]:
        if side not in {"home", "away"}:
            raise ValueError("side must be home or away")
        matches = self._filtered_matches(season=season, competition=competition)
        teams = sorted({match.home_key if side == "home" else match.away_key for match in matches})
        display = {}
        for match in matches:
            display[match.home_key] = match.home_team
            display[match.away_key] = match.away_team
        records = []
        for key in teams:
            stats = self.team_statistics(key, season=season, competition=competition, side=side)
            if stats["matches"] >= min_matches:
                stats["team"] = display.get(key, key)
                records.append(stats)
        records.sort(key=lambda row: (row["win_rate"], row["points"], row["goal_difference"]), reverse=True)
        return {"side": side, "season": season, "competition": competition, "minimum_matches": min_matches, "records": records[:max(1, min(int(limit), 100))]}

    def team_competitions(self, team: str, season: int | None = None) -> dict[str, object]:
        matches = self._filtered_matches(team=team, season=season)
        competitions: dict[str, int] = defaultdict(int)
        for match in matches:
            competitions[match.competition] += 1
        return {"team": team, "season": season, "competitions": dict(sorted(competitions.items())), "matches": len(matches)}

    def derby_matches(self, season: int | None = None, limit: int = 100) -> dict[str, object]:
        found = []
        for first, second, name in DERBIES:
            for match in self._filtered_matches(team=first, opponent=second, season=season):
                found.append((match, name))
        found.sort(key=lambda item: item[0].date, reverse=True)
        data = []
        for match, derby_name in found[:max(1, min(int(limit), 200))]:
            row = match.to_dict()
            row["derby"] = derby_name
            data.append(row)
        return {"season": season, "total": len(found), "matches": data, "truncated": len(found) > len(data)}

    def competition_finals(self, competition: str, season: int | None = None, limit: int = 100) -> dict[str, object]:
        """Find explicitly labeled finals, or the highest numeric cup round per season."""
        matches = self._filtered_matches(competition=competition, season=season)
        explicit = [match for match in matches if "final" in fold_text(" ".join(filter(None, (match.stage, match.round))))]
        selected = explicit
        inferred = False
        if not selected and normalize_competition(competition) == "copa do brasil":
            by_season: dict[int, list[Match]] = defaultdict(list)
            for match in matches:
                if match.source == "Brazilian_Cup_Matches.csv" and match.round and match.round.isdigit():
                    by_season[match.season].append(match)
            selected = []
            for season_matches in by_season.values():
                final_round = max(int(match.round or 0) for match in season_matches)
                selected.extend(match for match in season_matches if int(match.round or 0) == final_round)
            inferred = bool(selected)
        selected.sort(key=lambda match: match.date, reverse=True)
        limited = selected[:max(1, min(int(limit), 200))]
        return {
            "competition": competition,
            "season": season,
            "total": len(selected),
            "inferred_from_highest_round": inferred,
            "matches": [match.to_dict() for match in limited],
            "truncated": len(selected) > len(limited),
        }

    def club_profile(self, team: str, season: int | None = None, competition: str | None = None, player_limit: int = 25) -> dict[str, object]:
        """Join player and match domains into one team-centered response."""
        return {
            "team": team,
            "match_statistics": self.team_statistics(team, season=season, competition=competition),
            "competitions": self.team_competitions(team, season=season)["competitions"],
            "players": self.search_players(club=team, limit=player_limit),
        }

    def compare_seasons(self, season1: int, season2: int, competition: str = "Brasileirão Série A") -> dict[str, object]:
        return {
            "competition": competition,
            "seasons": [
                self.competition_statistics(competition, int(season1)),
                self.competition_statistics(competition, int(season2)),
            ],
        }

    def dataset_status(self) -> dict[str, object]:
        return self.repository.status()
