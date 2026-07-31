"""
Context
=======
Module: brazilian_soccer.graph

The knowledge graph itself: nodes are teams, players and competitions; edges are
matches (team --played--> team) and squad membership (player --plays_for--> team).

It is held in memory as a set of dict indexes built once at start-up:

    _by_team[team_key]                -> matches involving that team
    _by_competition_season[(c, y)]    -> matches in a competition+season
    _players_by_club[club_key]        -> FIFA players at that club
    _players_by_nationality[country]  -> FIFA players from that country

With ~24k matches and ~18k players the whole graph is a few tens of MB, so index
lookups make simple queries O(matches for one team) -- comfortably inside the
<2s budget -- and full-table aggregates (standings, biggest wins) a single pass
under 5s.

Every public method returns plain dicts/lists so that server.py can serialise
them to JSON without knowing anything about the internals.  Team arguments are
always accepted as free text and resolved via `resolve_team()`, which tries the
canonical key first and then a substring match, so "flamengo", "Flamengo-RJ" and
"Clube de Regatas do Flamengo" all work.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from datetime import date
from typing import Iterable, Sequence

from . import loader
from .models import LIBERTADORES, Match, Player, resolve_competition
from .names import DisplayNames, derby_name, normalize_team, strip_accents

# Points awarded in the league table.
WIN_POINTS, DRAW_POINTS = 3, 1


class TeamNotFound(LookupError):
    """Raised when a team string cannot be resolved to any club in the data."""

    def __init__(self, query: str, suggestions: Sequence[str] = ()):
        self.query = query
        self.suggestions = list(suggestions)
        extra = f" Did you mean: {', '.join(self.suggestions)}?" if self.suggestions else ""
        super().__init__(f"No team matching {query!r} in the datasets.{extra}")


def _empty_record() -> dict:
    return {
        "matches": 0, "wins": 0, "draws": 0, "losses": 0,
        "goals_for": 0, "goals_against": 0,
    }


def _finish_record(rec: dict) -> dict:
    played = rec["matches"]
    rec["goal_difference"] = rec["goals_for"] - rec["goals_against"]
    rec["points"] = rec["wins"] * WIN_POINTS + rec["draws"] * DRAW_POINTS
    rec["win_rate"] = round(100.0 * rec["wins"] / played, 1) if played else 0.0
    rec["goals_for_per_match"] = round(rec["goals_for"] / played, 2) if played else 0.0
    rec["goals_against_per_match"] = round(rec["goals_against"] / played, 2) if played else 0.0
    return rec


def _accumulate(rec: dict, scored: int, conceded: int) -> None:
    rec["matches"] += 1
    rec["goals_for"] += scored
    rec["goals_against"] += conceded
    if scored > conceded:
        rec["wins"] += 1
    elif scored < conceded:
        rec["losses"] += 1
    else:
        rec["draws"] += 1


class KnowledgeGraph:
    """In-memory graph over the Brazilian soccer datasets."""

    def __init__(
        self,
        matches: list[Match],
        players: list[Player],
        names: DisplayNames,
        source_counts: dict[str, int] | None = None,
    ) -> None:
        self.matches = matches
        self.players = players
        self.names = names
        self.source_counts = source_counts or {}
        self._build_indexes()

    # ------------------------------------------------------------------ build

    def _build_indexes(self) -> None:
        self._by_team: dict[str, list[Match]] = defaultdict(list)
        self._by_competition_season: dict[tuple[str, int], list[Match]] = defaultdict(list)
        self._by_competition: dict[str, list[Match]] = defaultdict(list)
        for match in self.matches:
            self._by_team[match.home_team].append(match)
            self._by_team[match.away_team].append(match)
            self._by_competition_season[(match.competition, match.season)].append(match)
            self._by_competition[match.competition].append(match)

        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        self._players_by_nationality: dict[str, list[Player]] = defaultdict(list)
        for player in self.players:
            if player.club_key:
                self._players_by_club[player.club_key].append(player)
            self._players_by_nationality[player.nationality.lower()].append(player)

        # Teams that appear in match data; used for resolution and suggestions.
        self._team_keys = set(self._by_team)
        # Clubs that played a *Brazilian domestic* competition.  Needed because
        # normalisation legitimately collapses "FC Barcelona" and the Ecuadorian
        # "Barcelona-EQU" of the Libertadores file onto the same key; only the
        # domestic set may be treated as "a Brazilian club" when joining the
        # FIFA squad data.
        self._domestic_team_keys = {
            key for key, rows in self._by_team.items()
            if any(m.competition != LIBERTADORES for m in rows)
        }

    # --------------------------------------------------------------- resolving

    def resolve_team(self, query: str, *, required: bool = True) -> str | None:
        """Resolve free text to a canonical team key present in the match data."""
        if not query or not query.strip():
            if required:
                raise TeamNotFound(query)
            return None
        key = normalize_team(query)
        if key in self._team_keys:
            return key
        needle = strip_accents(query).strip().lower()
        # Exact display-name match, then unique substring match.
        candidates = [k for k in self._team_keys if strip_accents(self.names.display(k)).lower() == needle]
        if not candidates and key:
            candidates = [k for k in self._team_keys if key in k or k in key]
        if not candidates:
            candidates = [
                k for k in self._team_keys
                if needle in strip_accents(self.names.display(k)).lower()
            ]
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            # Prefer the club with the most matches -- the "main" club of that name.
            candidates.sort(key=lambda k: (-len(self._by_team[k]), k))
            return candidates[0]
        if required:
            raise TeamNotFound(query, self._suggest(needle))
        return None

    def _suggest(self, needle: str, limit: int = 5) -> list[str]:
        if not needle:
            return []
        head = needle[:3]
        hits = [
            self.names.display(k) for k in sorted(self._team_keys)
            if strip_accents(self.names.display(k)).lower().startswith(head)
        ]
        return hits[:limit]

    def display(self, team_key: str) -> str:
        return self.names.display(team_key)

    # ----------------------------------------------------------------- queries

    def find_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        venue: str = "any",          # "home" | "away" | "any" (relative to `team`)
        competition: str | None = None,
        season: int | None = None,
        season_from: int | None = None,
        season_to: int | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        stage: str | None = None,
        limit: int | None = 50,
    ) -> list[Match]:
        """Filter matches by any combination of criteria, newest first."""
        team_key = self.resolve_team(team) if team else None
        opponent_key = self.resolve_team(opponent) if opponent else None
        comp = resolve_competition(competition) if competition else None
        if competition and comp is None:
            raise ValueError(
                f"Unknown competition {competition!r}. Known: "
                + ", ".join(sorted(self._by_competition))
            )
        start = _as_date(date_from)
        end = _as_date(date_to)
        stage_needle = stage.strip().lower() if stage else None

        if team_key is not None:
            pool: Iterable[Match] = self._by_team[team_key]
        elif comp and season is not None:
            pool = self._by_competition_season[(comp, season)]
        elif comp:
            pool = self._by_competition[comp]
        else:
            pool = self.matches

        results = []
        for match in pool:
            if comp and match.competition != comp:
                continue
            if season is not None and match.season != season:
                continue
            if season_from is not None and match.season < season_from:
                continue
            if season_to is not None and match.season > season_to:
                continue
            if team_key is not None:
                if venue == "home" and match.home_team != team_key:
                    continue
                if venue == "away" and match.away_team != team_key:
                    continue
            if opponent_key is not None:
                if team_key is None:
                    if not match.involves(opponent_key):
                        continue
                elif match.opponent_of(team_key) != opponent_key:
                    continue
            if start and (match.match_date is None or match.match_date < start):
                continue
            if end and (match.match_date is None or match.match_date > end):
                continue
            if stage_needle:
                haystack = " ".join(filter(None, [match.stage, match.round])).lower()
                # Word-boundary match so that stage="final" does not also return
                # every semifinal.
                if not re.search(rf"\b{re.escape(stage_needle)}\b", haystack):
                    continue
            results.append(match)

        results.sort(key=_match_sort_key, reverse=True)
        return results[:limit] if limit else results

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        *,
        competition: str | None = None,
        season: int | None = None,
        limit: int | None = 20,
    ) -> dict:
        """Full head-to-head record between two clubs."""
        key_a = self.resolve_team(team_a)
        key_b = self.resolve_team(team_b)
        if key_a == key_b:
            raise ValueError("head_to_head needs two different teams")
        matches = self.find_matches(
            team=key_a, opponent=key_b, competition=competition, season=season, limit=None
        )
        rec_a, rec_b = _empty_record(), _empty_record()
        by_competition: dict[str, dict] = defaultdict(_empty_record)
        for match in matches:
            a_goals = match.home_goals if match.home_team == key_a else match.away_goals
            b_goals = match.total_goals - a_goals
            _accumulate(rec_a, a_goals, b_goals)
            _accumulate(rec_b, b_goals, a_goals)
            _accumulate(by_competition[match.competition], a_goals, b_goals)
        return {
            "team_a": self.display(key_a),
            "team_b": self.display(key_b),
            "derby": derby_name(key_a, key_b),
            "total_matches": len(matches),
            "team_a_record": _finish_record(rec_a),
            "team_b_record": _finish_record(rec_b),
            "by_competition": {
                comp: _finish_record(rec) for comp, rec in sorted(by_competition.items())
            },
            "first_meeting": _iso(min((m.match_date for m in matches if m.match_date), default=None)),
            "last_meeting": _iso(max((m.match_date for m in matches if m.match_date), default=None)),
            "matches": [m.to_dict() for m in (matches[:limit] if limit else matches)],
        }

    def team_stats(
        self,
        team: str,
        *,
        competition: str | None = None,
        season: int | None = None,
        venue: str = "any",
    ) -> dict:
        """Win/draw/loss and goal record for a club, split home vs away."""
        key = self.resolve_team(team)
        matches = self.find_matches(
            team=key, competition=competition, season=season, venue=venue, limit=None
        )
        overall, home, away = _empty_record(), _empty_record(), _empty_record()
        by_competition: dict[str, dict] = defaultdict(_empty_record)
        by_season: dict[int, dict] = defaultdict(_empty_record)
        for match in matches:
            at_home = match.home_team == key
            scored = match.home_goals if at_home else match.away_goals
            conceded = match.total_goals - scored
            _accumulate(overall, scored, conceded)
            _accumulate(home if at_home else away, scored, conceded)
            _accumulate(by_competition[match.competition], scored, conceded)
            _accumulate(by_season[match.season], scored, conceded)
        return {
            "team": self.display(key),
            "competition": resolve_competition(competition) if competition else "all",
            "season": season if season is not None else "all",
            "venue": venue,
            "overall": _finish_record(overall),
            "home": _finish_record(home),
            "away": _finish_record(away),
            "by_competition": {c: _finish_record(r) for c, r in sorted(by_competition.items())},
            "by_season": {s: _finish_record(r) for s, r in sorted(by_season.items())},
            "biggest_win": _describe(_best_result(matches, key, win=True)),
            "biggest_loss": _describe(_best_result(matches, key, win=False)),
        }

    def standings(self, competition: str, season: int, *, limit: int | None = None) -> dict:
        """League table computed from match results (3 pts win, 1 pt draw).

        Ranking follows CBF criteria as far as the data allows:
        points, then wins, then goal difference, then goals for.
        """
        comp = resolve_competition(competition)
        if comp is None:
            raise ValueError(f"Unknown competition {competition!r}")
        matches = self._by_competition_season.get((comp, season), [])
        if not matches:
            return {
                "competition": comp, "season": season, "matches_counted": 0,
                "table": [], "note": "no matches for this competition/season in the datasets",
            }
        table: dict[str, dict] = defaultdict(_empty_record)
        for match in matches:
            _accumulate(table[match.home_team], match.home_goals, match.away_goals)
            _accumulate(table[match.away_team], match.away_goals, match.home_goals)
        rows = []
        for key, rec in table.items():
            rec = _finish_record(rec)
            rec["team"] = self.display(key)
            rows.append(rec)
        rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"], -r["goals_for"], r["team"]))
        for position, row in enumerate(rows, start=1):
            row["position"] = position
        is_league = comp.startswith("Brasileirão")
        return {
            "competition": comp,
            "season": season,
            "matches_counted": len(matches),
            "champion": rows[0]["team"] if is_league and rows else None,
            "relegated": [r["team"] for r in rows[-4:]] if is_league and len(rows) >= 16 else [],
            "table": rows[:limit] if limit else rows,
            "note": None if is_league else
                   "knockout competition: table is an aggregate of results, not a league table",
        }

    def competition_summary(self, competition: str, season: int | None = None) -> dict:
        """Season-level overview: goals, home advantage, stages, top scorers by team."""
        comp = resolve_competition(competition)
        if comp is None:
            raise ValueError(f"Unknown competition {competition!r}")
        matches = (
            self._by_competition_season.get((comp, season), [])
            if season is not None else self._by_competition.get(comp, [])
        )
        summary = self._aggregate(matches)
        summary.update({"competition": comp, "season": season if season is not None else "all"})
        if matches:
            summary["seasons_covered"] = sorted({m.season for m in matches})
            stages = sorted({m.stage for m in matches if m.stage})
            if stages:
                summary["stages"] = stages
            scored: dict[str, int] = defaultdict(int)
            for match in matches:
                scored[match.home_team] += match.home_goals
                scored[match.away_team] += match.away_goals
            top = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
            summary["top_scoring_teams"] = [
                {"team": self.display(k), "goals": v} for k, v in top
            ]
        return summary

    def bracket(self, competition: str, season: int) -> dict:
        """Knockout bracket (Libertadores / Copa do Brasil), grouped by stage."""
        comp = resolve_competition(competition)
        if comp is None:
            raise ValueError(f"Unknown competition {competition!r}")
        matches = self._by_competition_season.get((comp, season), [])
        order = ["group stage", "round of 16", "quarterfinals", "semifinals", "final"]

        def rank(stage: str) -> tuple[int, str]:
            low = stage.lower()
            for index, known in enumerate(order):
                if known in low:
                    return (index, low)
            return (len(order), low)

        grouped: dict[str, list[Match]] = defaultdict(list)
        for match in matches:
            grouped[(match.stage or match.round or "unknown")].append(match)
        stages = []
        for stage in sorted(grouped, key=rank):
            legs = sorted(grouped[stage], key=_match_sort_key)
            stages.append({
                "stage": stage,
                "matches": [m.to_dict() for m in legs],
            })
        return {"competition": comp, "season": season, "stages": stages}

    def statistics(
        self,
        *,
        competition: str | None = None,
        season: int | None = None,
        season_from: int | None = None,
        season_to: int | None = None,
    ) -> dict:
        """Aggregate statistics over an arbitrary slice of the match data."""
        matches = self.find_matches(
            competition=competition, season=season,
            season_from=season_from, season_to=season_to, limit=None,
        )
        result = self._aggregate(matches)
        result.update({
            "competition": resolve_competition(competition) if competition else "all",
            "season": season if season is not None else "all",
        })
        return result

    def _aggregate(self, matches: Sequence[Match]) -> dict:
        if not matches:
            return {"matches": 0, "note": "no matches match these filters"}
        total_goals = sum(m.total_goals for m in matches)
        home_wins = sum(1 for m in matches if m.home_goals > m.away_goals)
        away_wins = sum(1 for m in matches if m.away_goals > m.home_goals)
        draws = len(matches) - home_wins - away_wins
        count = len(matches)
        dates = [m.match_date for m in matches if m.match_date]
        return {
            "matches": count,
            "total_goals": total_goals,
            "goals_per_match": round(total_goals / count, 2),
            "median_goals": statistics.median(m.total_goals for m in matches),
            "home_goals": sum(m.home_goals for m in matches),
            "away_goals": sum(m.away_goals for m in matches),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(100.0 * home_wins / count, 1),
            "away_win_rate": round(100.0 * away_wins / count, 1),
            "draw_rate": round(100.0 * draws / count, 1),
            "goalless_draws": sum(1 for m in matches if m.total_goals == 0),
            "date_range": [_iso(min(dates)), _iso(max(dates))] if dates else None,
            "teams_involved": len({t for m in matches for t in (m.home_team, m.away_team)}),
        }

    def biggest_wins(
        self,
        *,
        competition: str | None = None,
        season: int | None = None,
        team: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Matches with the largest goal difference, tie-broken by total goals."""
        matches = self.find_matches(
            competition=competition, season=season, team=team, limit=None
        )
        matches = [m for m in matches if m.goal_difference > 0]
        matches.sort(key=lambda m: (-m.goal_difference, -m.total_goals, _match_sort_key(m)))
        return [
            {**m.to_dict(), "margin": m.goal_difference, "winner": self.display(m.winner)}
            for m in matches[:limit]
        ]

    def team_leaderboard(
        self,
        *,
        metric: str = "wins",
        competition: str | None = None,
        season: int | None = None,
        venue: str = "any",
        min_matches: int = 1,
        limit: int = 10,
    ) -> list[dict]:
        """Rank every club by a metric over a slice of the data.

        metric: wins | win_rate | points | goals_for | goals_against |
                goal_difference | matches
        """
        allowed = {
            "wins", "win_rate", "points", "goals_for", "goals_against",
            "goal_difference", "matches", "draws", "losses",
        }
        if metric not in allowed:
            raise ValueError(f"Unknown metric {metric!r}. Choose from: {', '.join(sorted(allowed))}")
        matches = self.find_matches(competition=competition, season=season, limit=None)
        table: dict[str, dict] = defaultdict(_empty_record)
        for match in matches:
            if venue in ("any", "home"):
                _accumulate(table[match.home_team], match.home_goals, match.away_goals)
            if venue in ("any", "away"):
                _accumulate(table[match.away_team], match.away_goals, match.home_goals)
        rows = []
        for key, rec in table.items():
            if rec["matches"] < min_matches:
                continue
            rec = _finish_record(rec)
            rec["team"] = self.display(key)
            rows.append(rec)
        ascending = metric == "goals_against"
        rows.sort(key=lambda r: (r[metric] if ascending else -r[metric], r["team"]))
        return rows[:limit]

    def team_profile(self, team: str) -> dict:
        """Everything the graph knows about one club, matches and squad."""
        key = self.resolve_team(team)
        matches = self._by_team[key]
        competitions = sorted({m.competition for m in matches})
        seasons = sorted({m.season for m in matches})
        squad = sorted(
            self._players_by_club.get(key, []),
            key=lambda p: (-(p.overall or 0), p.name),
        )
        rivals: dict[str, int] = defaultdict(int)
        for match in matches:
            rivals[match.opponent_of(key)] += 1
        top_rivals = sorted(rivals.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        return {
            "team": self.display(key),
            "key": key,
            "competitions": competitions,
            "seasons": seasons,
            "total_matches": len(matches),
            "record": _finish_record(_record_for(matches, key)),
            "most_played_opponents": [
                {"team": self.display(k), "matches": v, "derby": derby_name(key, k)}
                for k, v in top_rivals
            ],
            "squad_size_in_fifa_data": len(squad),
            "squad": [p.to_dict() for p in squad[:30]],
            "arenas": sorted({m.arena for m in matches if m.arena})[:10],
        }

    # ----------------------------------------------------------------- players

    def search_players(
        self,
        *,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        sort_by: str = "overall",
        limit: int = 20,
        include_skills: bool = False,
    ) -> list[dict]:
        """Search the FIFA player table on any combination of fields."""
        pool: Iterable[Player] = self.players
        if nationality:
            pool = self._players_by_nationality.get(nationality.strip().lower(), [])
        elif club:
            club_key = self.resolve_team(club, required=False) or normalize_team(club)
            indexed = self._players_by_club.get(club_key)
            pool = indexed if indexed else self.players

        needle = strip_accents(name).strip().lower() if name else None
        club_needle = strip_accents(club).strip().lower() if club else None
        position_needle = position.strip().upper() if position else None

        results = []
        for player in pool:
            if needle and needle not in strip_accents(player.name).lower():
                continue
            if club_needle:
                club_key = normalize_team(club)
                if player.club_key != club_key and club_needle not in strip_accents(player.club).lower():
                    continue
            if position_needle and (player.position or "").upper() != position_needle:
                continue
            if min_overall is not None and (player.overall or 0) < min_overall:
                continue
            if max_overall is not None and (player.overall or 0) > max_overall:
                continue
            if min_age is not None and (player.age or 0) < min_age:
                continue
            if max_age is not None and (player.age or 0) > max_age:
                continue
            results.append(player)

        keys = {
            "overall": lambda p: (-(p.overall or 0), p.name),
            "potential": lambda p: (-(p.potential or 0), p.name),
            "age": lambda p: ((p.age or 999), p.name),
            "name": lambda p: p.name.lower(),
        }
        results.sort(key=keys.get(sort_by, keys["overall"]))
        return [p.to_dict(include_skills=include_skills) for p in results[:limit]]

    def player_profile(self, name: str) -> dict:
        """Best-match player lookup by name, with full attributes."""
        needle = strip_accents(name).strip().lower()
        if not needle:
            raise ValueError("player name is required")
        exact = [p for p in self.players if strip_accents(p.name).lower() == needle]
        partial = [p for p in self.players if needle in strip_accents(p.name).lower()]
        pool = exact or partial
        if not pool:
            # The FIFA snapshot abbreviates or nicknames many players
            # ("Gabriel Barbosa" is absent, "Gabriel Jesus" is present), so fall
            # back to any player sharing a name token and offer them as
            # suggestions rather than pretending the query matched.
            tokens = [t for t in needle.split() if len(t) > 2]
            near = [
                p for p in self.players
                if any(t in strip_accents(p.name).lower().split() for t in tokens)
            ]
            near.sort(key=lambda p: (-(p.overall or 0), p.name))
            return {
                "query": name,
                "found": False,
                "matches": [],
                "suggestions": [p.to_dict() for p in near[:5]],
            }
        pool.sort(key=lambda p: (-(p.overall or 0), p.name))
        best = pool[0]
        profile = best.to_dict(include_skills=True)
        profile["plays_in_brazilian_league_data"] = best.club_key in self._domestic_team_keys
        if best.club_key in self._domestic_team_keys:
            profile["club_matches_in_dataset"] = len(self._by_team[best.club_key])
        return {
            "query": name,
            "found": True,
            "player": profile,
            "other_matches": [p.to_dict() for p in pool[1:6]],
        }

    # A handful of club names are true homonyms across countries: the Argentine
    # River Plate vs River-PI, Portuguese Boavista vs Boavista-RJ.  fifa_data.csv
    # records no country for clubs, so we require a squad to be majority-Brazilian
    # before treating it as the Brazilian club of that name.
    BRAZILIAN_SQUAD_THRESHOLD = 0.5

    def players_by_brazilian_club(self, *, min_players: int = 1, limit: int = 30) -> list[dict]:
        """Squads grouped by club, restricted to clubs present in the match data."""
        rows = []
        for club_key, squad in self._players_by_club.items():
            if club_key not in self._domestic_team_keys or len(squad) < min_players:
                continue
            share = sum(1 for p in squad if p.is_brazilian) / len(squad)
            if share < self.BRAZILIAN_SQUAD_THRESHOLD:
                continue
            rated = [p.overall for p in squad if p.overall is not None]
            best = max(squad, key=lambda p: (p.overall or 0))
            rows.append({
                "club": self.display(club_key),
                "players": len(squad),
                "brazilian_share": round(share, 2),
                "average_overall": round(sum(rated) / len(rated), 1) if rated else None,
                "best_player": best.name,
                "best_overall": best.overall,
            })
        rows.sort(key=lambda r: (-r["players"], r["club"]))
        return rows[:limit]

    # -------------------------------------------------------------- meta / misc

    def list_teams(self, *, query: str | None = None, limit: int = 50) -> list[dict]:
        needle = strip_accents(query).strip().lower() if query else None
        rows = []
        for key in self._team_keys:
            display = self.display(key)
            if needle and needle not in strip_accents(display).lower() and needle not in key:
                continue
            rows.append({
                "team": display,
                "key": key,
                "matches": len(self._by_team[key]),
                "competitions": sorted({m.competition for m in self._by_team[key]}),
            })
        rows.sort(key=lambda r: (-r["matches"], r["team"]))
        return rows[:limit]

    def find_derbies(self, *, season: int | None = None, competition: str | None = None,
                     limit: int = 50) -> list[dict]:
        """Matches between traditional rivals, annotated with the derby's name."""
        matches = self.find_matches(season=season, competition=competition, limit=None)
        rows = []
        for match in matches:
            name = derby_name(match.home_team, match.away_team)
            if name:
                rows.append({**match.to_dict(), "derby": name})
        return rows[:limit]

    def dataset_overview(self) -> dict:
        seasons = sorted({m.season for m in self.matches})
        per_competition = {
            comp: {
                "matches": len(rows),
                "seasons": [min(m.season for m in rows), max(m.season for m in rows)],
            }
            for comp, rows in sorted(self._by_competition.items())
        }
        brazilian = self._players_by_nationality.get("brazil", [])
        return {
            "matches_after_deduplication": len(self.matches),
            "rows_read_per_file": self.source_counts,
            "competitions": per_competition,
            "seasons": [min(seasons), max(seasons)] if seasons else None,
            "distinct_teams": len(self._team_keys),
            "players": len(self.players),
            "brazilian_players": len(brazilian),
            "clubs_with_squad_and_match_data": sum(
                1 for k in self._players_by_club if k in self._domestic_team_keys
            ),
        }


# ------------------------------------------------------------------- helpers

def _match_sort_key(match: Match) -> tuple:
    return (match.match_date or date.min, match.season, match.home_team)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _as_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    parsed = loader.parse_date(value)
    if parsed is None:
        raise ValueError(f"Unrecognised date {value!r}; use YYYY-MM-DD or DD/MM/YYYY")
    return parsed


def _record_for(matches: Sequence[Match], key: str) -> dict:
    rec = _empty_record()
    for match in matches:
        scored = match.home_goals if match.home_team == key else match.away_goals
        _accumulate(rec, scored, match.total_goals - scored)
    return rec


def _best_result(matches: Sequence[Match], key: str, *, win: bool) -> Match | None:
    best, best_margin = None, 0
    for match in matches:
        scored = match.home_goals if match.home_team == key else match.away_goals
        conceded = match.total_goals - scored
        margin = scored - conceded if win else conceded - scored
        if margin > best_margin:
            best, best_margin = match, margin
    return best


def _describe(match: Match | None) -> dict | None:
    return match.to_dict() if match else None


def load_default_graph(data_dir=None) -> KnowledgeGraph:
    """Load every dataset and build the graph (call once; it takes a few seconds)."""
    matches, players, names, counts = loader.load_all(data_dir)
    return KnowledgeGraph(matches, players, names, counts)
