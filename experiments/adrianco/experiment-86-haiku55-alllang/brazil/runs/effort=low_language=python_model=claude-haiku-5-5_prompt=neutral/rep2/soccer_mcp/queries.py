"""Query layer over a loaded :class:`~soccer_mcp.loader.Dataset`.

Every public method returns plain Python data (lists, dicts, dataclasses) so
the MCP layer can format it and tests can assert on it directly. Team, player
and competition arguments are free text and are normalised here.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional, Union

from .loader import Dataset, Match, Player
from .normalize import (
    COMPETITION_NAMES,
    TeamRef,
    parse_date,
    parse_team,
    resolve_competition,
    simplify,
    team_matches,
)

VENUES = ("either", "home", "away")

POSITION_GROUPS = {
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
    "midfielder": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM",
                   "LDM", "RDM"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "goalkeeper": {"GK"},
}
NATIONALITY_ALIASES = {"brazilian": "brazil"}
BRAZILIAN_LEAGUES = ("brasileirao_a", "brasileirao_b", "brasileirao_c")

DateLike = Union[date, str, None]


class QueryError(ValueError):
    """Raised when a query argument is invalid (unknown competition, bad date...)."""


@dataclass(frozen=True)
class TeamRecord:
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int

    @property
    def win_rate(self) -> float:
        return round(100 * self.wins / self.played, 1) if self.played else 0.0


def _as_date(value: DateLike) -> Optional[date]:
    if value is None or isinstance(value, date):
        return value
    return parse_date(value)


def _as_competition(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = resolve_competition(value)
    if key is None:
        raise QueryError(f"Unknown competition: {value!r}")
    return key


def _check_venue(venue: str) -> str:
    if venue not in VENUES:
        raise QueryError(f"venue must be one of {VENUES}, got {venue!r}")
    return venue


def label(team: TeamRef) -> str:
    """Readable team name: 'flamengo' -> 'Flamengo', 'atletico'+MG -> 'Atletico (MG)'."""
    name = team.base.title()
    return f"{name} ({team.state})" if team.state else name


def _side_of(match: Match, team: str, state: Optional[str]) -> Optional[str]:
    """Return 'home', 'away' or None depending on which side ``team`` played."""
    if team_matches(match.home, team, state):
        return "home"
    if team_matches(match.away, team, state):
        return "away"
    return None


def _team_plays(match: Match, team: TeamRef, venue: str) -> bool:
    side = _side_of(match, team.base, team.state)
    return side is not None and venue in ("either", side)


def _opponent_plays(match: Match, team: Optional[TeamRef], opponent: TeamRef) -> bool:
    """True when ``opponent`` is in the match, and is the other side from ``team`` if given."""
    if team is None:
        return _side_of(match, opponent.base, opponent.state) is not None
    side = _side_of(match, team.base, team.state)
    other = match.away if side == "home" else match.home
    return team_matches(other, opponent.base, opponent.state)


def _perspective(match: Match, side: str) -> tuple[int, int]:
    """(goals for, goals against) from the point of view of ``side``."""
    if side == "home":
        return match.home_goals, match.away_goals
    return match.away_goals, match.home_goals


def _result(goals_for: int, goals_against: int) -> str:
    if goals_for > goals_against:
        return "W"
    if goals_for < goals_against:
        return "L"
    return "D"


class SoccerQueries:
    """Answer match, team, player and statistics questions over the dataset."""

    def __init__(self, dataset: Dataset):
        self.dataset = dataset

    # ----- matches -------------------------------------------------------

    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start: DateLike = None,
        end: DateLike = None,
        venue: str = "either",
        limit: Optional[int] = None,
    ) -> list[Match]:
        """Matches filtered by team (and optional opponent), competition, season and dates.

        Results are newest first. ``venue`` restricts ``team`` to home or away games.
        """
        venue = _check_venue(venue)
        comp = _as_competition(competition)
        start_d, end_d = _as_date(start), _as_date(end)
        team_ref = parse_team(team) if team else None
        opp_ref = parse_team(opponent) if opponent else None
        if team_ref and opp_ref and team_ref.base == opp_ref.base:
            raise QueryError("team and opponent must be different clubs")

        found = []
        for match in self.dataset.matches:
            if comp and match.competition != comp:
                continue
            if season is not None and match.season != season:
                continue
            if start_d and match.date < start_d:
                continue
            if end_d and match.date > end_d:
                continue
            if team_ref and not _team_plays(match, team_ref, venue):
                continue
            if opp_ref and not _opponent_plays(match, team_ref, opp_ref):
                continue
            found.append(match)

        found.sort(key=lambda m: m.date, reverse=True)
        return found[:limit] if limit else found

    def head_to_head(self, team_a: str, team_b: str, competition: Optional[str] = None,
                     season: Optional[int] = None) -> dict:
        """Head-to-head summary between two clubs, counting only meetings in the dataset."""
        matches = self.find_matches(team=team_a, opponent=team_b,
                                    competition=competition, season=season)
        ref_a, ref_b = parse_team(team_a), parse_team(team_b)
        wins_a = wins_b = draws = goals_a = goals_b = 0
        for match in matches:
            side = _side_of(match, team_a, ref_a.state)
            gf, ga = _perspective(match, side)
            goals_a += gf
            goals_b += ga
            result = _result(gf, ga)
            wins_a += result == "W"
            wins_b += result == "L"
            draws += result == "D"
        return {
            "team_a": label(ref_a),
            "team_b": label(ref_b),
            "matches": matches,
            "wins_a": wins_a,
            "wins_b": wins_b,
            "draws": draws,
            "goals_a": goals_a,
            "goals_b": goals_b,
            "last_meeting": matches[0] if matches else None,
        }

    # ----- team records -------------------------------------------------

    def team_record(self, team: str, season: Optional[int] = None,
                    competition: Optional[str] = None, venue: str = "either") -> dict:
        """Wins, draws, losses and goals for a team, optionally by venue."""
        matches = self.find_matches(team=team, competition=competition,
                                    season=season, venue=venue)
        ref = parse_team(team)
        record = self._tally(matches, ref)
        return {
            "team": label(ref),
            "season": season,
            "competition": _competition_label(competition),
            "venue": venue,
            "record": record,
            "matches": matches,
        }

    @staticmethod
    def _tally(matches: Iterable[Match], ref: TeamRef) -> TeamRecord:
        played = wins = draws = losses = gf = ga = 0
        for match in matches:
            side = _side_of(match, ref.base, ref.state)
            if side is None:
                continue
            goals_for, goals_against = _perspective(match, side)
            played += 1
            gf += goals_for
            ga += goals_against
            result = _result(goals_for, goals_against)
            wins += result == "W"
            draws += result == "D"
            losses += result == "L"
        return TeamRecord(played, wins, draws, losses, gf, ga)

    def search_teams(self, query: str, limit: int = 20) -> list[dict]:
        """Clubs whose normalised name contains ``query``, with match counts (for disambiguation)."""
        wanted = simplify(query)
        counts: Counter = Counter()
        refs: dict[str, TeamRef] = {}
        for match in self.dataset.matches:
            for ref in (match.home, match.away):
                if wanted in ref.base:
                    refs[ref.key] = ref
                    counts[ref.key] += 1
        ranked = counts.most_common(limit)
        return [{"team": label(refs[key]), "matches": n} for key, n in ranked]

    # ----- competitions and statistics ----------------------------------

    def standings(self, season: int, competition: str = "Brasileirão Série A") -> list[dict]:
        """League table for a season, with 3 points for a win and 1 for a draw."""
        comp = _as_competition(competition)
        matches = self.find_matches(competition=comp, season=season)
        table: dict[str, dict] = {}
        refs: dict[str, TeamRef] = {}
        for match in matches:
            for ref in (match.home, match.away):
                refs.setdefault(ref.key, ref)
                table.setdefault(ref.key, _blank_row())
            for side, ref in (("home", match.home), ("away", match.away)):
                goals_for, goals_against = _perspective(match, side)
                row = table[ref.key]
                row["played"] += 1
                row["goals_for"] += goals_for
                row["goals_against"] += goals_against
                result = _result(goals_for, goals_against)
                row["won"] += result == "W"
                row["drawn"] += result == "D"
                row["lost"] += result == "L"
        table = self._merge_unstated_states(table, refs)

        rows = []
        for key, row in table.items():
            row["team"] = label(refs[key])
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
            row["points"] = 3 * row["won"] + row["drawn"]
            rows.append(row)
        rows.sort(key=lambda r: (-r["points"], -r["won"], -r["goal_difference"],
                                 -r["goals_for"], r["team"]))
        for position, row in enumerate(rows, start=1):
            row["position"] = position
        return rows

    @staticmethod
    def _merge_unstated_states(table: dict, refs: dict) -> dict:
        """Fold a club written without a state into its only stated variant.

        Some files write "Sport" and others "Sport-PE" for the same club in one
        season; merging them keeps the table from listing the club twice.
        """
        by_base: dict[str, list[str]] = defaultdict(list)
        for key in table:
            by_base[refs[key].base].append(key)
        for base, keys in by_base.items():
            stated = [k for k in keys if refs[k].state]
            unstated = [k for k in keys if not refs[k].state]
            if len(stated) != 1 or not unstated:
                continue
            target = stated[0]
            for key in unstated:
                for field_name, value in table.pop(key).items():
                    if isinstance(value, int):
                        table[target][field_name] += value
                refs.pop(key)
        return table

    def league_stats(self, competition: Optional[str] = None,
                     season: Optional[int] = None) -> dict:
        """Goals per match and home/draw/away result percentages."""
        matches = self.find_matches(competition=competition, season=season)
        total = len(matches)
        goals = sum(m.total_goals for m in matches)
        home_wins = sum(m.home_goals > m.away_goals for m in matches)
        draws = sum(m.is_draw for m in matches)
        away_wins = total - home_wins - draws
        return {
            "competition": _competition_label(competition),
            "season": season,
            "matches": total,
            "total_goals": goals,
            "goals_per_match": round(goals / total, 2) if total else 0.0,
            "home_win_pct": _pct(home_wins, total),
            "draw_pct": _pct(draws, total),
            "away_win_pct": _pct(away_wins, total),
        }

    def biggest_wins(self, competition: Optional[str] = None, season: Optional[int] = None,
                     limit: int = 5) -> list[Match]:
        """Matches with the largest goal margin, ties broken by most total goals."""
        matches = self.find_matches(competition=competition, season=season)
        matches = [m for m in matches if not m.is_draw]
        matches.sort(key=lambda m: (-m.goal_margin, -m.total_goals, m.date))
        return matches[:limit]

    def venue_leaderboard(self, venue: str = "home", competition: Optional[str] = None,
                          season: Optional[int] = None, min_matches: int = 10,
                          limit: int = 5) -> list[dict]:
        """Teams ranked by win rate at home or away, from matches in the dataset."""
        venue = _check_venue(venue)
        if venue == "either":
            raise QueryError("venue must be 'home' or 'away' for a leaderboard")
        comp = _as_competition(competition)
        per_team: dict[str, TeamRecord] = {}
        refs: dict[str, TeamRef] = {}
        grouped: dict[str, list[Match]] = defaultdict(list)
        for match in self.find_matches(competition=comp, season=season):
            ref = match.home if venue == "home" else match.away
            refs.setdefault(ref.key, ref)
            grouped[ref.key].append(match)
        for key, matches in grouped.items():
            per_team[key] = self._tally(matches, refs[key])
        rows = [
            {"team": label(refs[key]), "record": rec, "win_rate": rec.win_rate}
            for key, rec in per_team.items() if rec.played >= min_matches
        ]
        rows.sort(key=lambda r: (-r["win_rate"], -r["record"].played, r["team"]))
        return rows[:limit]

    # ----- players ------------------------------------------------------

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "overall",
        limit: int = 20,
    ) -> list[Player]:
        """FIFA players filtered by name, nationality, club, position and rating."""
        if sort_by not in ("overall", "potential", "age"):
            raise QueryError("sort_by must be 'overall', 'potential' or 'age'")
        wanted_name = simplify(name) if name else None
        wanted_nat = _nationality(nationality) if nationality else None
        wanted_club = simplify(club) if club else None
        positions = _position_codes(position) if position else None

        found = []
        for player in self.dataset.players:
            if wanted_name and wanted_name not in simplify(player.name):
                continue
            if wanted_nat and simplify(player.nationality) != wanted_nat:
                continue
            if wanted_club and wanted_club not in simplify(player.club):
                continue
            if positions and player.position.upper() not in positions:
                continue
            if min_overall is not None and player.overall < min_overall:
                continue
            found.append(player)

        if sort_by == "age":
            found.sort(key=lambda p: (p.age, p.name))
        else:
            found.sort(key=lambda p: (-getattr(p, sort_by), p.name))
        return found[:limit]

    def brazilian_players_by_club(self, limit: int = 20) -> list[dict]:
        """Brazilian players grouped by club, for clubs that play in Brazilian league matches."""
        brazilian_clubs = {
            ref.base
            for match in self.dataset.matches if match.competition in BRAZILIAN_LEAGUES
            for ref in (match.home, match.away)
        }
        groups: dict[str, list[Player]] = defaultdict(list)
        for player in self.dataset.players:
            if simplify(player.nationality) != "brazil":
                continue
            club_base = parse_team(player.club).base
            if club_base in brazilian_clubs:
                groups[club_base].append(player)
        rows = []
        for base, players in groups.items():
            rows.append({
                "club": base.title(),
                "players": len(players),
                "avg_overall": round(sum(p.overall for p in players) / len(players), 1),
            })
        rows.sort(key=lambda r: (-r["players"], -r["avg_overall"], r["club"]))
        return rows[:limit]


def _blank_row() -> dict:
    return {"played": 0, "won": 0, "drawn": 0, "lost": 0, "goals_for": 0, "goals_against": 0}


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def _competition_label(competition: Optional[str]) -> str:
    if not competition:
        return "All competitions"
    return COMPETITION_NAMES[_as_competition(competition)]


def _nationality(value: str) -> str:
    key = simplify(value)
    return NATIONALITY_ALIASES.get(key, key)


def _position_codes(value: str) -> set[str]:
    key = simplify(value)
    key = key[:-1] if key.endswith("s") and key[:-1] in POSITION_GROUPS else key
    if key in POSITION_GROUPS:
        return POSITION_GROUPS[key]
    return {value.strip().upper()}
