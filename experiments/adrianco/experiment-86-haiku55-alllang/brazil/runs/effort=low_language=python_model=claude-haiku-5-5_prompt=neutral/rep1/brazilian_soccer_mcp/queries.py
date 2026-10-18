# Context: The knowledge base. Holds the merged match and player records in memory and answers
# structured questions (match search, team records, head-to-head, standings, aggregate stats,
# player search). The MCP layer (server.py) maps natural-language intents onto these methods.
# Team identity is (key, state): "Atletico-MG" and "Atletico-PR" stay distinct when a state is
# known, and a query without a state matches every club with that name.

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .data import BRASILEIRAO_LABEL, Match, Player, Team, load_matches, load_players
from .names import fold, parse_team, resolve_competition

VENUES = ("any", "home", "away")

POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "midfielder": {"CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"},
    "forward": {"ST", "CF", "LS", "RS", "LF", "RF", "LW", "RW"},
}


@dataclass(frozen=True)
class TeamRecord:
    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.played if self.played else 0.0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


@dataclass(frozen=True)
class HeadToHead:
    team_a: str
    team_b: str
    a_wins: int
    b_wins: int
    draws: int
    matches: list[Match]


@dataclass
class StandingRow:
    team: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return 3 * self.wins + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


@dataclass(frozen=True)
class SeasonStats:
    matches: int
    goals: int
    goals_per_match: float
    home_win_rate: float
    draw_rate: float
    away_win_rate: float


@dataclass
class _Tally:
    name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0


def _team_matches(team_identity: tuple[str, str | None], candidate) -> bool:
    key, state = team_identity
    return candidate.key == key and (state is None or candidate.state is None or candidate.state == state)


def _query_identity(text: str) -> tuple[str, str | None]:
    key, state = parse_team(text)
    if not key:
        raise ValueError(f"Empty team name: {text!r}")
    return key, state


def _in_range(played_on: date, start: date | None, end: date | None) -> bool:
    return (start is None or played_on >= start) and (end is None or played_on <= end)


def _perspective(match: Match, identity: tuple[str, str | None], venue: str):
    """Return (side, opponent, goals_for, goals_against) if the team plays in this match at the given venue."""
    if venue in ("any", "home") and _team_matches(identity, match.home):
        return "home", match.away, match.home_goals, match.away_goals
    if venue in ("any", "away") and _team_matches(identity, match.away):
        return "away", match.home, match.away_goals, match.home_goals
    return None


def _group_identities(matches: list[Match]):
    """Return a function giving the grouping identity of a team within a set of matches.

    A club keeps its state in the grouping only when one name appears with several states in
    the same set of matches (e.g. Atlético-MG and Athletico-PR); otherwise the name alone groups it,
    so state-less rows and state-tagged rows of the same club are counted together.
    """
    states: dict[str, set[str]] = defaultdict(set)
    for match in matches:
        for team in (match.home, match.away):
            if team.state:
                states[team.key].add(team.state)
    ambiguous = {key for key, found in states.items() if len(found) > 1}

    def identity(team: Team) -> tuple[str, str | None]:
        return team.identity if team.key in ambiguous else (team.key, None)

    return identity


def _outcome(goals_for: int, goals_against: int) -> str:
    if goals_for > goals_against:
        return "W"
    if goals_for < goals_against:
        return "L"
    return "D"


class SoccerKnowledgeBase:
    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = matches
        self.players = players

    @classmethod
    def load(cls, data_dir: str | Path) -> "SoccerKnowledgeBase":
        data_dir = Path(data_dir)
        return cls(load_matches(data_dir), load_players(data_dir))

    # ---- match queries -------------------------------------------------

    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        start: date | None = None,
        end: date | None = None,
        competition: str | None = None,
        season: int | None = None,
        venue: str = "any",
        limit: int | None = 50,
    ) -> list[Match]:
        """Matches newest first; limit=None returns every match that fits."""
        if venue not in VENUES:
            raise ValueError(f"venue must be one of {VENUES}")
        team_id = _query_identity(team) if team else None
        opponent_id = _query_identity(opponent) if opponent else None
        comp = resolve_competition(competition) if competition else None
        found = []
        for match in self.matches:
            if comp and match.competition != comp:
                continue
            if season is not None and match.season != season:
                continue
            if not _in_range(match.played_on, start, end):
                continue
            if team_id and not self._involves(match, team_id, venue):
                continue
            if opponent_id and not self._involves(match, opponent_id, "any"):
                continue
            found.append(match)
        found.sort(key=lambda m: m.played_on, reverse=True)
        return found if limit is None else found[:limit]

    @staticmethod
    def _involves(match: Match, identity, venue: str) -> bool:
        if venue == "home":
            return _team_matches(identity, match.home)
        if venue == "away":
            return _team_matches(identity, match.away)
        return _team_matches(identity, match.home) or _team_matches(identity, match.away)

    def team_record(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str = "any",
        start: date | None = None,
        end: date | None = None,
    ) -> TeamRecord:
        identity = _query_identity(team)
        comp = resolve_competition(competition) if competition else None
        played, wins, draws, losses, gf, ga = [], 0, 0, 0, 0, 0
        display = team.strip()
        for match in self.matches:
            if comp and match.competition != comp:
                continue
            if season is not None and match.season != season:
                continue
            if not _in_range(match.played_on, start, end):
                continue
            view = _perspective(match, identity, venue)
            if view is None:
                continue
            side, _, goals_for, goals_against = view
            display = (match.home if side == "home" else match.away).label
            played.append(match)
            gf += goals_for
            ga += goals_against
            outcome = _outcome(goals_for, goals_against)
            wins += outcome == "W"
            draws += outcome == "D"
            losses += outcome == "L"
        return TeamRecord(display, len(played), wins, draws, losses, gf, ga)

    def head_to_head(self, team_a: str, team_b: str, competition: str | None = None) -> HeadToHead:
        id_a, id_b = _query_identity(team_a), _query_identity(team_b)
        comp = resolve_competition(competition) if competition else None
        matches, a_wins, b_wins, draws = [], 0, 0, 0
        name_a, name_b = team_a.strip(), team_b.strip()
        for match in self.matches:
            if comp and match.competition != comp:
                continue
            a_is_home = _team_matches(id_a, match.home) and _team_matches(id_b, match.away)
            b_is_home = _team_matches(id_b, match.home) and _team_matches(id_a, match.away)
            if not (a_is_home or b_is_home):
                continue
            matches.append(match)
            if a_is_home:
                name_a, name_b = match.home.label, match.away.label
                a_goals, b_goals = match.home_goals, match.away_goals
            else:
                name_a, name_b = match.away.label, match.home.label
                a_goals, b_goals = match.away_goals, match.home_goals
            outcome = _outcome(a_goals, b_goals)
            a_wins += outcome == "W"
            b_wins += outcome == "L"
            draws += outcome == "D"
        matches.sort(key=lambda m: m.played_on, reverse=True)
        return HeadToHead(name_a, name_b, a_wins, b_wins, draws, matches)

    def biggest_wins(self, competition: str | None = None, season: int | None = None, limit: int = 5) -> list[Match]:
        comp = resolve_competition(competition) if competition else None
        candidates = [
            m for m in self.matches
            if (not comp or m.competition == comp) and (season is None or m.season == season)
            and m.goal_margin > 0
        ]
        candidates.sort(key=lambda m: (m.goal_margin, m.played_on), reverse=True)
        return candidates[:limit]

    # ---- competition and statistics -----------------------------------

    def standings(
        self, season: int, competition: str = BRASILEIRAO_LABEL
    ) -> list[StandingRow]:
        comp = resolve_competition(competition) or competition
        selected = [m for m in self.matches if m.season == season and m.competition == comp]
        identity = _group_identities(selected)
        rows: dict[tuple[str, str | None], StandingRow] = {}
        for match in selected:
            for team, goals_for, goals_against in (
                (match.home, match.home_goals, match.away_goals),
                (match.away, match.away_goals, match.home_goals),
            ):
                group = identity(team)
                row = rows.setdefault(group, StandingRow(team=team.label))
                row.played += 1
                row.goals_for += goals_for
                row.goals_against += goals_against
                outcome = _outcome(goals_for, goals_against)
                row.wins += outcome == "W"
                row.draws += outcome == "D"
                row.losses += outcome == "L"
        return sorted(rows.values(), key=lambda r: (-r.points, -r.goal_difference, -r.goals_for, r.team))

    def season_stats(self, season: int | None = None, competition: str | None = None) -> SeasonStats:
        comp = resolve_competition(competition) if competition else None
        subset = [
            m for m in self.matches
            if (season is None or m.season == season) and (not comp or m.competition == comp)
        ]
        count = len(subset)
        goals = sum(m.total_goals for m in subset)
        home_wins = sum(m.home_goals > m.away_goals for m in subset)
        draws = sum(m.home_goals == m.away_goals for m in subset)
        away_wins = sum(m.home_goals < m.away_goals for m in subset)
        if not count:
            return SeasonStats(0, 0, 0.0, 0.0, 0.0, 0.0)
        return SeasonStats(
            matches=count,
            goals=goals,
            goals_per_match=goals / count,
            home_win_rate=home_wins / count,
            draw_rate=draws / count,
            away_win_rate=away_wins / count,
        )

    def venue_ranking(
        self,
        venue: str,
        season: int | None = None,
        competition: str | None = None,
        min_matches: int = 10,
    ) -> list[TeamRecord]:
        """Teams ranked by win rate when playing only at home or only away."""
        if venue not in ("home", "away"):
            raise ValueError("venue must be 'home' or 'away'")
        comp = resolve_competition(competition) if competition else None
        selected = [
            m for m in self.matches
            if (season is None or m.season == season) and (not comp or m.competition == comp)
        ]
        identity = _group_identities(selected)
        tallies: dict[tuple[str, str | None], _Tally] = {}
        for match in selected:
            if venue == "home":
                side_team, goals_for, goals_against = match.home, match.home_goals, match.away_goals
            else:
                side_team, goals_for, goals_against = match.away, match.away_goals, match.home_goals
            group = identity(side_team)
            tally = tallies.setdefault(group, _Tally(name=side_team.label))
            tally.played += 1
            outcome = _outcome(goals_for, goals_against)
            tally.wins += outcome == "W"
            tally.draws += outcome == "D"
            tally.losses += outcome == "L"
        records = [
            TeamRecord(t.name, t.played, t.wins, t.draws, t.losses, 0, 0)
            for t in tallies.values() if t.played >= min_matches
        ]
        records.sort(key=lambda r: (-r.win_rate, -r.played, r.team))
        return records

    # ---- player queries -----------------------------------------------

    def search_players(self, name: str, limit: int = 20) -> list[Player]:
        needle = fold(name)
        hits = [p for p in self.players if needle and needle in fold(p.name)]
        return sorted(hits, key=lambda p: (-p.overall, p.name))[:limit]

    def list_players(
        self,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        limit: int = 20,
    ) -> list[Player]:
        players = self._filter_players(nationality=nationality, club=club, position=position)
        return sorted(players, key=lambda p: (-p.overall, p.name))[:limit]

    def club_profile(self, team: str) -> tuple[str, list[Player]]:
        """Squad from the player data for a club, matched on the normalized club name."""
        key, _ = _query_identity(team)
        squad = []
        for player in self.players:
            club_key = parse_team(player.club)[0]
            if club_key == key or club_key.startswith(key + " "):
                squad.append(player)
        return team.strip(), sorted(squad, key=lambda p: (-p.overall, p.name))

    def _filter_players(self, nationality, club, position) -> list[Player]:
        nat = fold(nationality) if nationality else None
        club_needle = fold(club) if club else None
        positions = None
        if position:
            positions = POSITION_GROUPS.get(fold(position).rstrip("s"), {position.strip().upper()})
        result = []
        for player in self.players:
            if nat and fold(player.nationality) != nat:
                continue
            if club_needle and club_needle not in fold(player.club):
                continue
            if positions and player.position.upper() not in positions:
                continue
            result.append(player)
        return result
