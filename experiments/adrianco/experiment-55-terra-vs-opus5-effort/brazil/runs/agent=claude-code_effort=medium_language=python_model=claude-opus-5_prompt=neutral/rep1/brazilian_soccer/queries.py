"""Analytical API over the knowledge graph.

Context
-------
Everything the MCP server can answer is implemented here as a plain Python
method returning plain data (dataclasses / dicts / lists), so the query logic is
unit-testable without an MCP client.  Covers the five capability groups in
``TASK.md``:

* match queries      -- :meth:`SoccerQueries.search_matches`, :meth:`last_meeting`
* team queries       -- :meth:`team_record`, :meth:`team_profile`, :meth:`compare_teams`
* player queries     -- :meth:`search_players`, :meth:`get_player`, :meth:`club_squad`
* competition queries-- :meth:`standings`, :meth:`champion`, :meth:`relegated`
* statistics         -- :meth:`competition_stats`, :meth:`biggest_wins`,
                        :meth:`best_records`, :meth:`compare_seasons`

Ambiguous team names raise :class:`TeamNotFound` carrying suggestions, which the
server turns into a helpful "did you mean" message rather than an empty result.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from .graph import KnowledgeGraph, load_default_graph
from .models import (
    BRASILEIRAO,
    LEAGUE_COMPETITIONS,
    AWAY_WIN,
    DRAW,
    HOME_WIN,
    HeadToHead,
    Match,
    Player,
    Team,
    TeamRecord,
)
from .normalization import DERBIES, normalize_text, parse_date

#: Free-text competition names an LLM is likely to produce -> canonical label.
_COMPETITION_ALIASES = {
    "brasileirao": BRASILEIRAO,
    "campeonato brasileiro": BRASILEIRAO,
    "serie a": BRASILEIRAO,
    "serie b": "Brasileirão Série B",
    "serie c": "Brasileirão Série C",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "copa": "Copa do Brasil",
    "cup": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "conmebol libertadores": "Copa Libertadores",
}

VENUE_ANY = "any"
VENUE_HOME = "home"
VENUE_AWAY = "away"


class TeamNotFound(LookupError):
    """Raised when a team name cannot be resolved; carries near-misses."""

    def __init__(self, query: str, suggestions: list[str] | None = None) -> None:
        self.query = query
        self.suggestions = suggestions or []
        message = f"No team matching {query!r} in the dataset."
        if self.suggestions:
            message += " Did you mean: " + ", ".join(self.suggestions) + "?"
        super().__init__(message)


class SoccerQueries:
    """Query facade bound to one :class:`KnowledgeGraph`."""

    def __init__(self, graph: KnowledgeGraph | None = None) -> None:
        self.graph = graph if graph is not None else load_default_graph()

    @classmethod
    def from_data_dir(cls, data_dir: Path | str) -> "SoccerQueries":
        return cls(load_default_graph(data_dir))

    # ------------------------------------------------------------------
    # resolution helpers
    # ------------------------------------------------------------------
    def resolve_team(self, name: str) -> Team:
        """Resolve *name* to a single team or raise :class:`TeamNotFound`."""
        candidates = self.graph.resolve_teams(name, limit=6)
        if not candidates:
            raise TeamNotFound(name)
        return candidates[0]

    def suggest_teams(self, name: str, limit: int = 8) -> list[Team]:
        return self.graph.resolve_teams(name, limit=limit)

    def _competition(self, competition: str | None) -> str | None:
        """Fuzzy-match a competition label (``"libertadores"`` -> full name)."""
        if not competition:
            return None
        needle = normalize_text(competition)
        known = self.graph.competitions
        for name in known:
            if normalize_text(name) == needle:
                return name
        # Aliases are checked before substring matching so that the ambiguous
        # "copa" resolves to the Copa do Brasil rather than whichever full name
        # happens to sort first.  Longest alias wins.
        for alias in sorted(_COMPETITION_ALIASES, key=len, reverse=True):
            name = _COMPETITION_ALIASES[alias]
            if alias in needle and name in known:
                return name
        for name in known:
            if needle in normalize_text(name):
                return name
        raise ValueError(
            f"Unknown competition {competition!r}. Known competitions: "
            + ", ".join(known)
        )

    # ------------------------------------------------------------------
    # 1. match queries
    # ------------------------------------------------------------------
    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        season_from: int | None = None,
        season_to: int | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        venue: str = VENUE_ANY,
        stage: str | None = None,
        min_total_goals: int | None = None,
        limit: int | None = 50,
        newest_first: bool = True,
    ) -> list[Match]:
        """Filter matches by any combination of the supported criteria."""
        competition = self._competition(competition)
        team_key = self.resolve_team(team).key if team else None
        opponent_key = self.resolve_team(opponent).key if opponent else None
        start = _as_date(date_from)
        end = _as_date(date_to)
        stage_needle = normalize_text(stage) if stage else None

        if team_key is not None:
            candidates = (
                self.graph.matches[i] for i in self.graph.matches_by_team[team_key]
            )
        elif competition is not None:
            candidates = (
                self.graph.matches[i]
                for i in self.graph.matches_by_competition[competition]
            )
        elif season is not None:
            candidates = (
                self.graph.matches[i] for i in self.graph.matches_by_season[season]
            )
        else:
            candidates = iter(self.graph.matches)

        results: list[Match] = []
        for match in candidates:
            if competition and match.competition != competition:
                continue
            if season is not None and match.season != season:
                continue
            if season_from is not None and (match.season or 0) < season_from:
                continue
            if season_to is not None and (match.season or 9999) > season_to:
                continue
            if start and (match.match_date is None or match.match_date < start):
                continue
            if end and (match.match_date is None or match.match_date > end):
                continue
            if opponent_key and match.opponent_of(team_key or "") != opponent_key:
                if not (
                    team_key is None
                    and (match.home_key == opponent_key or match.away_key == opponent_key)
                ):
                    continue
            if team_key and venue == VENUE_HOME and match.home_key != team_key:
                continue
            if team_key and venue == VENUE_AWAY and match.away_key != team_key:
                continue
            if stage_needle and not _stage_matches(match, stage_needle):
                continue
            if min_total_goals is not None and (match.total_goals or 0) < min_total_goals:
                continue
            results.append(match)

        results.sort(
            key=lambda m: (m.match_date or date.min, m.competition),
            reverse=newest_first,
        )
        return results[:limit] if limit else results

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
    ) -> HeadToHead:
        """Full meeting history and record between two clubs."""
        a = self.resolve_team(team_a)
        b = self.resolve_team(team_b)
        matches = self.search_matches(
            team=a.key,
            opponent=b.key,
            competition=competition,
            season=season,
            limit=None,
        )
        h2h = HeadToHead(team_a=a.display, team_b=b.display, matches=matches)
        for match in matches:
            if not match.has_score:
                continue
            h2h.a_goals += match.goals_for(a.key)
            h2h.b_goals += match.goals_for(b.key)
            winner = match.winner_key
            if winner == a.key:
                h2h.a_wins += 1
            elif winner == b.key:
                h2h.b_wins += 1
            else:
                h2h.draws += 1
        return h2h

    def last_meeting(self, team_a: str, team_b: str) -> Match | None:
        """Most recent match between two clubs, or ``None``."""
        matches = self.search_matches(team=team_a, opponent=team_b, limit=1)
        return matches[0] if matches else None

    def derbies(self, season: int | None = None, limit: int = 200) -> list[dict]:
        """Matches between traditional rivals, tagged with the derby name."""
        results: list[dict] = []
        for key_a, key_b, name in DERBIES:
            if key_a not in self.graph.teams or key_b not in self.graph.teams:
                continue
            matches = self.search_matches(
                team=key_a, opponent=key_b, season=season, limit=None
            )
            for match in matches:
                results.append({"derby": name, "match": match})
        results.sort(key=lambda item: item["match"].match_date or date.min, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # 2. team queries
    # ------------------------------------------------------------------
    def team_record(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str = VENUE_ANY,
        season_from: int | None = None,
        season_to: int | None = None,
    ) -> TeamRecord:
        """W/D/L + goals for a club, optionally scoped by season/comp/venue."""
        resolved = self.resolve_team(team)
        record = TeamRecord(team_key=resolved.key, team_name=resolved.display)
        for match in self.search_matches(
            team=resolved.key,
            season=season,
            competition=competition,
            venue=venue,
            season_from=season_from,
            season_to=season_to,
            limit=None,
        ):
            record.add(match)
        return record

    def team_profile(self, team: str) -> dict:
        """Everything the graph knows about one club."""
        resolved = self.resolve_team(team)
        matches = self.graph.team_matches(resolved.key)
        by_competition: dict[str, TeamRecord] = {}
        seasons: set[int] = set()
        for match in matches:
            record = by_competition.setdefault(
                match.competition,
                TeamRecord(team_key=resolved.key, team_name=resolved.display),
            )
            record.add(match)
            if match.season is not None:
                seasons.add(match.season)
        overall = TeamRecord(team_key=resolved.key, team_name=resolved.display)
        for match in matches:
            overall.add(match)
        dates = [m.match_date for m in matches if m.match_date]
        squad = [self.graph.players[i] for i in resolved.player_indexes]
        return {
            "team": resolved.display,
            "team_key": resolved.key,
            "region": resolved.region,
            "known_as": sorted(resolved.aliases),
            "overall": overall.to_dict(),
            "competitions": {
                name: record.to_dict() for name, record in sorted(by_competition.items())
            },
            "seasons": sorted(seasons),
            "first_match": min(dates).isoformat() if dates else None,
            "last_match": max(dates).isoformat() if dates else None,
            "fifa_players": len(squad),
            "home": self.team_record(resolved.key, venue=VENUE_HOME).to_dict(),
            "away": self.team_record(resolved.key, venue=VENUE_AWAY).to_dict(),
        }

    def compare_teams(
        self, team_a: str, team_b: str, competition: str | None = None
    ) -> dict:
        """Side-by-side records plus the head-to-head between two clubs."""
        record_a = self.team_record(team_a, competition=competition)
        record_b = self.team_record(team_b, competition=competition)
        h2h = self.head_to_head(team_a, team_b, competition=competition)
        return {
            "team_a": record_a.to_dict(),
            "team_b": record_b.to_dict(),
            "head_to_head": h2h.to_dict(match_limit=10),
            "competition": competition or "all competitions",
        }

    def team_season_trend(self, team: str, competition: str | None = None) -> list[dict]:
        """Season-by-season record, for "performance trend" style questions."""
        resolved = self.resolve_team(team)
        by_season: dict[int, TeamRecord] = {}
        for match in self.search_matches(
            team=resolved.key, competition=competition, limit=None
        ):
            if match.season is None:
                continue
            record = by_season.setdefault(
                match.season,
                TeamRecord(team_key=resolved.key, team_name=resolved.display),
            )
            record.add(match)
        return [
            {"season": season, **by_season[season].to_dict()}
            for season in sorted(by_season)
        ]

    def search_teams(self, query: str, limit: int = 10) -> list[Team]:
        return self.graph.resolve_teams(query, limit=limit)

    # ------------------------------------------------------------------
    # 3. player queries
    # ------------------------------------------------------------------
    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_age: int | None = None,
        min_age: int | None = None,
        sort_by: str = "overall",
        limit: int = 25,
    ) -> list[Player]:
        """Filter/sort the FIFA player table."""
        if name:
            candidates = self.graph.find_players_by_name(name, limit=500)
        elif nationality:
            key = normalize_text(nationality)
            candidates = [
                self.graph.players[i] for i in self.graph.players_by_nationality.get(key, ())
            ]
        elif club:
            candidates = self._club_players(club)
        else:
            candidates = self.graph.players

        nationality_needle = normalize_text(nationality) if nationality else None
        club_needle = normalize_text(club) if club else None
        club_key = None
        if club:
            resolved = self.graph.resolve_teams(club, limit=1)
            club_key = resolved[0].key if resolved else None
        position_needle = (position or "").strip().upper()

        results: list[Player] = []
        for player in candidates:
            if nationality_needle and normalize_text(player.nationality) != nationality_needle:
                continue
            if club_needle:
                if not (
                    club_needle in normalize_text(player.club_raw)
                    or (club_key and player.club_key == club_key)
                ):
                    continue
            if position_needle and (player.position or "").upper() != position_needle:
                continue
            if min_overall is not None and (player.overall or 0) < min_overall:
                continue
            if min_age is not None and (player.age or 0) < min_age:
                continue
            if max_age is not None and (player.age or 999) > max_age:
                continue
            results.append(player)

        if sort_by != "relevance" or not name:
            keys = {
                "overall": lambda p: (-(p.overall or 0), p.name),
                "potential": lambda p: (-(p.potential or 0), p.name),
                "age": lambda p: (p.age or 999, p.name),
                "name": lambda p: p.name,
            }
            results.sort(key=keys.get(sort_by, keys["overall"]))
        return results[:limit]

    def _club_players(self, club: str) -> list[Player]:
        needle = normalize_text(club)
        resolved = self.graph.resolve_teams(club, limit=1)
        indexes: list[int] = []
        if resolved:
            indexes = list(self.graph.players_by_club.get(resolved[0].key, ()))
        players = [self.graph.players[i] for i in indexes]
        if players:
            return players
        return [p for p in self.graph.players if needle in normalize_text(p.club_raw)]

    def get_player(self, name: str) -> Player | None:
        """Best single player match for a name."""
        matches = self.graph.find_players_by_name(name, limit=1)
        return matches[0] if matches else None

    def lookup_player(self, name: str) -> dict:
        """Best match plus whether it is exact and a few alternatives.

        The FIFA file is the FIFA 19 (2018/19) snapshot, so plenty of famous
        Brazilians are simply absent.  Reporting "closest match" beats silently
        answering about a different player.
        """
        candidates = self.graph.find_players_by_name(name, limit=5)
        if not candidates:
            return {"query": name, "player": None, "exact": False, "alternatives": []}
        best = candidates[0]
        return {
            "query": name,
            "player": best,
            "exact": self.graph.name_is_exact(name, best),
            "alternatives": candidates[1:],
        }

    def club_squad(self, club: str, limit: int = 40) -> dict:
        """FIFA squad for a club plus a small summary."""
        players = sorted(
            self._club_players(club), key=lambda p: -(p.overall or 0)
        )
        ratings = [p.overall for p in players if p.overall is not None]
        resolved = self.graph.resolve_teams(club, limit=1)
        return {
            "club": resolved[0].display if resolved else club,
            "players_found": len(players),
            "average_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "players": players[:limit],
        }

    def players_by_nationality_at_clubs(
        self, nationality: str = "Brazil", limit: int = 20
    ) -> list[dict]:
        """e.g. "Brazilian players at Brazilian clubs", grouped by club."""
        key = normalize_text(nationality)
        players = [
            self.graph.players[i]
            for i in self.graph.players_by_nationality.get(key, ())
        ]
        grouped: dict[str, list[Player]] = defaultdict(list)
        for player in players:
            if player.club_raw:
                grouped[player.club_raw].append(player)
        rows = []
        for club, squad in grouped.items():
            ratings = [p.overall for p in squad if p.overall is not None]
            rows.append(
                {
                    "club": club,
                    "players": len(squad),
                    "average_overall": round(sum(ratings) / len(ratings), 1)
                    if ratings
                    else None,
                    "in_match_data": self.graph.resolve_teams(club, limit=1) != [],
                    "top_player": max(squad, key=lambda p: p.overall or 0).name,
                }
            )
        rows.sort(key=lambda row: (-row["players"], -(row["average_overall"] or 0)))
        return rows[:limit]

    # ------------------------------------------------------------------
    # 4. competition queries
    # ------------------------------------------------------------------
    def standings(self, competition: str | None, season: int) -> list[TeamRecord]:
        """League table computed from match results (3-1-0, GD tiebreak)."""
        competition = self._competition(competition) or BRASILEIRAO
        records: dict[str, TeamRecord] = {}
        for match in self.search_matches(
            competition=competition, season=season, limit=None
        ):
            for key, name in (
                (match.home_key, match.home_name),
                (match.away_key, match.away_name),
            ):
                record = records.setdefault(key, TeamRecord(team_key=key, team_name=name))
                record.add(match)
        table = list(records.values())
        table.sort(
            key=lambda r: (-r.points, -r.goal_difference, -r.goals_for, r.team_name)
        )
        return table

    def champion(self, competition: str | None, season: int) -> dict:
        """Season winner: league leader, or the final's winner for cups."""
        competition = self._competition(competition) or BRASILEIRAO
        if competition in LEAGUE_COMPETITIONS:
            table = self.standings(competition, season)
            if not table:
                return {"competition": competition, "season": season, "champion": None}
            leader = table[0]
            return {
                "competition": competition,
                "season": season,
                "champion": leader.team_name,
                "basis": "top of the calculated league table",
                "record": leader.to_dict(),
                "runner_up": table[1].team_name if len(table) > 1 else None,
            }
        final = self._final_match(competition, season)
        if final is None:
            return {
                "competition": competition,
                "season": season,
                "champion": None,
                "basis": "no final found in the dataset",
            }
        return {
            "competition": competition,
            "season": season,
            "champion": final["winner"],
            "basis": final["basis"],
            "finalists": final["finalists"],
            "matches": [m.to_dict() for m in final["matches"]],
        }

    def _final_match(self, competition: str, season: int) -> dict | None:
        """Locate a cup final and decide it on aggregate over both legs.

        Some seasons in the cup files carry no stage labels at all; there we
        fall back to the last fixture of the season and any earlier leg between
        the same two clubs, flagging the weaker basis in the answer.
        """
        season_matches = self.search_matches(
            competition=competition, season=season, limit=None
        )
        finals = [
            match
            for match in season_matches
            if "final" in normalize_text(match.stage or match.round or "")
            and "semi" not in normalize_text(match.stage or match.round or "")
            and "quarter" not in normalize_text(match.stage or match.round or "")
        ]
        inferred = False
        if not finals:
            dated = [m for m in season_matches if m.match_date and m.has_score]
            if not dated:
                return None
            last = max(dated, key=lambda m: m.match_date)
            pair = {last.home_key, last.away_key}
            finals = [m for m in dated if {m.home_key, m.away_key} == pair]
            inferred = True
        aggregate: dict[str, int] = defaultdict(int)
        names: dict[str, str] = {}
        for match in finals:
            if not match.has_score:
                continue
            aggregate[match.home_key] += match.home_goals
            aggregate[match.away_key] += match.away_goals
            names[match.home_key] = match.home_name
            names[match.away_key] = match.away_name
        if not aggregate:
            return None
        best = max(aggregate.items(), key=lambda item: item[1])
        tied = [k for k, v in aggregate.items() if v == best[1]]
        winner = names[best[0]] if len(tied) == 1 else None
        if winner is None:
            basis = "final level on aggregate in the dataset (decided on penalties)"
        elif inferred:
            basis = (
                "inferred from the last fixture of the season -- this competition"
                " has no stage labels for that year in the source data"
            )
        else:
            basis = "winner on aggregate over the final"
        return {
            "winner": winner,
            "basis": basis,
            "matches": finals,
            "finalists": [names[key] for key in sorted(aggregate)],
        }

    def relegated(self, season: int, competition: str | None = None, count: int = 4) -> dict:
        """Bottom *count* of the calculated league table."""
        competition = self._competition(competition) or BRASILEIRAO
        table = self.standings(competition, season)
        return {
            "competition": competition,
            "season": season,
            "teams_in_table": len(table),
            "relegated": [record.to_dict() for record in table[-count:]] if table else [],
            "note": "calculated from match results in the dataset",
        }

    def season_bracket(self, competition: str, season: int) -> dict:
        """Knockout matches grouped by stage (Libertadores / Copa do Brasil)."""
        competition = self._competition(competition)
        stages: dict[str, list[Match]] = defaultdict(list)
        for match in self.search_matches(
            competition=competition, season=season, limit=None, newest_first=False
        ):
            stages[(match.stage or match.round or "unknown")].append(match)
        return {
            "competition": competition,
            "season": season,
            "stages": {name: stages[name] for name in sorted(stages, key=_stage_order)},
        }

    # ------------------------------------------------------------------
    # 5. statistics
    # ------------------------------------------------------------------
    def competition_stats(
        self, competition: str | None = None, season: int | None = None
    ) -> dict:
        """Goals-per-match, home/draw/away split and volume for a slice."""
        competition = self._competition(competition)
        matches = self.search_matches(
            competition=competition, season=season, limit=None
        )
        played = [m for m in matches if m.has_score]
        goals = sum(m.total_goals for m in played)
        home_wins = sum(1 for m in played if m.result == HOME_WIN)
        away_wins = sum(1 for m in played if m.result == AWAY_WIN)
        draws = sum(1 for m in played if m.result == DRAW)
        total = len(played) or 1
        seasons = sorted({m.season for m in matches if m.season is not None})
        return {
            "competition": competition or "all competitions",
            "season": season,
            "seasons_covered": [seasons[0], seasons[-1]] if seasons else [],
            "matches": len(matches),
            "matches_with_scores": len(played),
            "total_goals": goals,
            "goals_per_match": round(goals / total, 2),
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "home_win_rate": round(home_wins / total * 100, 1),
            "draw_rate": round(draws / total * 100, 1),
            "away_win_rate": round(away_wins / total * 100, 1),
        }

    def biggest_wins(
        self,
        competition: str | None = None,
        season: int | None = None,
        team: str | None = None,
        limit: int = 10,
    ) -> list[Match]:
        """Largest goal margins, biggest first."""
        matches = self.search_matches(
            competition=competition, season=season, team=team, limit=None
        )
        played = [m for m in matches if m.has_score]
        played.sort(
            key=lambda m: (
                -m.goal_difference,
                -m.total_goals,
                -(m.match_date.toordinal() if m.match_date else 0),
            )
        )
        return played[:limit]

    def best_records(
        self,
        competition: str | None = None,
        season: int | None = None,
        venue: str = VENUE_ANY,
        metric: str = "points_per_game",
        min_matches: int = 10,
        limit: int = 10,
    ) -> list[TeamRecord]:
        """Rank clubs by points-per-game / win-rate / goals over a slice."""
        competition = self._competition(competition)
        records: dict[str, TeamRecord] = {}
        for match in self.search_matches(
            competition=competition, season=season, limit=None
        ):
            sides = []
            if venue in (VENUE_ANY, VENUE_HOME):
                sides.append((match.home_key, match.home_name))
            if venue in (VENUE_ANY, VENUE_AWAY):
                sides.append((match.away_key, match.away_name))
            for key, name in sides:
                record = records.setdefault(key, TeamRecord(team_key=key, team_name=name))
                record.add(match)
        metrics = {
            "points_per_game": lambda r: r.points_per_game,
            "points": lambda r: r.points,
            "win_rate": lambda r: r.win_rate,
            "wins": lambda r: r.wins,
            "goals_for": lambda r: r.goals_for,
            "goals_per_game": lambda r: r.goals_per_game,
            "goal_difference": lambda r: r.goal_difference,
        }
        score = metrics.get(metric, metrics["points_per_game"])
        eligible = [r for r in records.values() if r.played >= min_matches]
        eligible.sort(key=lambda r: (-score(r), -r.goal_difference, r.team_name))
        return eligible[:limit]

    def top_scoring_teams(
        self, competition: str | None = None, season: int | None = None, limit: int = 10
    ) -> list[TeamRecord]:
        return self.best_records(
            competition=competition,
            season=season,
            metric="goals_for",
            min_matches=1,
            limit=limit,
        )

    def compare_seasons(
        self, seasons: list[int], competition: str | None = None
    ) -> list[dict]:
        """Aggregate stats for several seasons side by side."""
        return [
            self.competition_stats(competition=competition, season=season)
            for season in seasons
        ]

    def dataset_overview(self) -> dict:
        summary = self.graph.summary()
        summary["seasons_by_competition"] = {
            competition: (
                [self.graph.seasons_for(competition)[0], self.graph.seasons_for(competition)[-1]]
                if self.graph.seasons_for(competition)
                else []
            )
            for competition in self.graph.competitions
        }
        return summary


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

_STAGE_ORDER = (
    "round1", "round2", "round3", "round4", "groupstage", "roundof16",
    "quarterfinal", "semifinal", "final",
)


def _stage_order(stage: str) -> tuple:
    """Order knockout stages sensibly; tolerates ``quarterfinals``/``quarter-final``."""
    normalized = normalize_text(stage).replace("-", "").replace(" ", "")
    for position, known in enumerate(_STAGE_ORDER):
        if known in normalized:
            return (position, normalized)
    return (len(_STAGE_ORDER), normalized)


def _stage_matches(match: Match, needle: str) -> bool:
    """Stage/round filter that does not let ``final`` swallow ``semi-final``.

    Both sides are collapsed to a hyphen/space-free form so ``quarter-final``
    and ``quarterfinals`` are interchangeable.
    """
    haystack = normalize_text(f"{match.stage or ''} {match.round or ''}")
    haystack = haystack.replace("-", "").replace(" ", "")
    compact = needle.replace("-", "").replace(" ", "")
    if compact == "final":
        return "final" in haystack and not (
            "semifinal" in haystack or "quarterfinal" in haystack
        )
    return compact in haystack


def _as_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return parse_date(value)
