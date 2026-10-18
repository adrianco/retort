"""In-memory query layer over the loaded matches and players.

``SoccerData`` is the only object the MCP tools talk to. It owns the
cross-file de-duplication (a fixture can appear in both the 2012+ and the
2003-2019 Brasileirão files) and resolves fuzzy user input such as
"flamengo" or "Copa do Brasil" to canonical keys.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .loaders import BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES, load_all
from .models import Match, Player
from .normalize import normalize_text, team_key

FORWARD_POSITIONS = {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
MIDFIELD_POSITIONS = {
    "CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM", "LCM", "RCM", "LDM", "RDM",
}
DEFENDER_POSITIONS = {"CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"}
GOALKEEPER_POSITIONS = {"GK"}
POSITION_GROUPS = {
    "forward": FORWARD_POSITIONS,
    "midfielder": MIDFIELD_POSITIONS,
    "defender": DEFENDER_POSITIONS,
    "goalkeeper": GOALKEEPER_POSITIONS,
}

_COMPETITION_ALIASES = {
    "brasileirao": BRASILEIRAO,
    "brasileirao serie a": BRASILEIRAO,
    "serie a": BRASILEIRAO,
    "copa do brasil": COPA_DO_BRASIL,
    "copa brasil": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
}
# Keys are compared after normalize_text(), so they are accent-free.


class QueryError(ValueError):
    """Raised for unknown or ambiguous user input; the message is user-facing."""


@dataclass(frozen=True)
class Record:
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.played * 100 if self.played else 0.0


@dataclass(frozen=True)
class HeadToHead:
    a_key: str
    b_key: str
    matches: list[Match]
    a_wins: int
    b_wins: int
    draws: int
    a_goals: int
    b_goals: int


@dataclass(frozen=True)
class StandingRow:
    team_key: str
    team: str
    record: Record
    points: int

    @property
    def goal_difference(self) -> int:
        return self.record.goals_for - self.record.goals_against


def _tally(matches: list[Match], team: str) -> Record:
    wins = draws = losses = gf = ga = 0
    for match in matches:
        outcome = match.result_for(team)
        wins += outcome == "W"
        draws += outcome == "D"
        losses += outcome == "L"
        gf += match.goals_for(team)
        ga += match.goals_against(team)
    return Record(len(matches), wins, draws, losses, gf, ga)


# Some sources record the same kick-off a day apart (time-zone shifts), so
# fixtures are matched on competition, ordered pair and score, within one day.
_DUPLICATE_WINDOW_DAYS = 1


def _is_duplicate(match: Match, kept: list[Match]) -> bool:
    return any(
        abs((match.date - other.date).days) <= _DUPLICATE_WINDOW_DAYS
        and other.home_goals == match.home_goals
        and other.away_goals == match.away_goals
        for other in kept
    )


def _dedupe(matches: list[Match]) -> list[Match]:
    """Keep the first copy of each fixture; earlier sources win ties."""
    by_pair: dict[tuple, list[Match]] = defaultdict(list)
    unique: list[Match] = []
    for match in matches:
        pair = (match.competition, match.home_key, match.away_key)
        if _is_duplicate(match, by_pair[pair]):
            continue
        by_pair[pair].append(match)
        unique.append(match)
    return unique


class SoccerData:
    """Indexed, de-duplicated view over the Brazilian soccer datasets."""

    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = sorted(_dedupe(matches), key=lambda m: (m.date, m.home_key))
        self.players = players
        self._team_names: dict[str, Counter] = defaultdict(Counter)
        self._by_team: dict[str, list[Match]] = defaultdict(list)
        self._competitions = {m.competition for m in self.matches}
        for match in self.matches:
            self._team_names[match.home_key][match.home] += 1
            self._team_names[match.away_key][match.away] += 1
            self._by_team[match.home_key].append(match)
            self._by_team[match.away_key].append(match)

    @classmethod
    def load(cls, data_dir: Path) -> "SoccerData":
        matches, players, _report = load_all(data_dir)
        return cls(matches, players)

    # ----- competitions ------------------------------------------------

    def resolve_competition(self, text: str | None) -> str | None:
        """Map 'brasileirao', 'copa do brasil', 'Brasileirão Série B', ... to a
        competition name present in the data, or raise ``QueryError``."""
        if text is None or not text.strip():
            return None
        needle = normalize_text(text)
        if needle in _COMPETITION_ALIASES:
            return _COMPETITION_ALIASES[needle]
        for name in self._competitions:
            if needle == normalize_text(name):
                return name
        raise QueryError(f"unknown competition: {text!r}")

    # ----- teams -------------------------------------------------------

    def team_name(self, key: str) -> str:
        """Most common display spelling for a team key."""
        names = self._team_names.get(key)
        return names.most_common(1)[0][0] if names else key

    def resolve_team(self, text: str) -> str:
        """Resolve free text to one team key or raise ``QueryError``."""
        key = team_key(text)
        if key in self._by_team:
            return key
        candidates = [k for k in self._by_team if len(key) >= 4 and key in k]
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            names = ", ".join(sorted(self.team_name(k) for k in candidates))
            raise QueryError(f"ambiguous team {text!r}; did you mean: {names}?")
        raise QueryError(f"no team matches {text!r} in the match data")

    def brazilian_team_keys(self) -> set[str]:
        """Clubs that appear in any Brazilian domestic competition."""
        domestic = {BRASILEIRAO, COPA_DO_BRASIL}
        keys: set[str] = set()
        for match in self.matches:
            if match.competition in domestic or match.competition.startswith("Brasileirão"):
                keys.add(match.home_key)
                keys.add(match.away_key)
        return keys

    # ----- match queries ----------------------------------------------

    def _filter_matches(
        self,
        *,
        competition: str | None = None,
        season: int | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[Match]:
        return [
            m for m in self.matches
            if (competition is None or m.competition == competition)
            and (season is None or m.season == season)
            and (start is None or m.date >= start)
            and (end is None or m.date <= end)
        ]

    def find_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        venue: str = "any",
        competition: str | None = None,
        season: int | None = None,
        start: date | None = None,
        end: date | None = None,
        limit: int | None = 20,
    ) -> list[Match]:
        """Matches newest-first. ``venue`` applies to ``team``: home, away or any."""
        if venue not in {"any", "home", "away"}:
            raise QueryError("venue must be one of: any, home, away")
        team_k = self.resolve_team(team) if team else None
        opp_k = self.resolve_team(opponent) if opponent else None
        comp = self.resolve_competition(competition)

        pool = self._by_team.get(team_k, []) if team_k else self.matches
        if team_k and opp_k:
            pool = [m for m in pool if opp_k in (m.home_key, m.away_key)]
        result = []
        for m in pool:
            if team_k and venue == "home" and m.home_key != team_k:
                continue
            if team_k and venue == "away" and m.away_key != team_k:
                continue
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != season:
                continue
            if start and m.date < start or end and m.date > end:
                continue
            result.append(m)
        result.sort(key=lambda m: (m.date, m.home_key), reverse=True)
        return result[:limit] if limit else result

    def head_to_head(self, a: str, b: str, competition: str | None = None) -> HeadToHead:
        a_key, b_key = self.resolve_team(a), self.resolve_team(b)
        matches = self.find_matches(
            team=a_key, opponent=b_key, competition=competition, limit=None,
        )
        a_wins = sum(m.result_for(a_key) == "W" for m in matches)
        b_wins = sum(m.result_for(b_key) == "W" for m in matches)
        draws = sum(m.result_for(a_key) == "D" for m in matches)
        return HeadToHead(
            a_key=a_key,
            b_key=b_key,
            matches=matches,
            a_wins=a_wins,
            b_wins=b_wins,
            draws=draws,
            a_goals=sum(m.goals_for(a_key) for m in matches),
            b_goals=sum(m.goals_for(b_key) for m in matches),
        )

    def team_record(
        self,
        team: str,
        *,
        venue: str = "any",
        competition: str | None = None,
        season: int | None = None,
    ) -> Record:
        key = self.resolve_team(team)
        matches = self.find_matches(
            team=key, venue=venue, competition=competition, season=season, limit=None,
        )
        return _tally(matches, key)

    # ----- aggregates -------------------------------------------------

    def standings(self, season: int, competition: str = BRASILEIRAO) -> list[StandingRow]:
        comp = self.resolve_competition(competition)
        matches = self._filter_matches(competition=comp, season=season)
        keys = {m.home_key for m in matches} | {m.away_key for m in matches}
        rows = []
        for key in keys:
            team_matches = [m for m in matches if key in (m.home_key, m.away_key)]
            record = _tally(team_matches, key)
            points = 3 * record.wins + record.draws
            rows.append(StandingRow(key, self.team_name(key), record, points))
        rows.sort(key=lambda r: (-r.points, -r.goal_difference, -r.record.goals_for, r.team))
        return rows

    def goals_per_match(self, competition: str | None = None, season: int | None = None) -> float:
        matches = self._filter_matches(
            competition=self.resolve_competition(competition), season=season,
        )
        if not matches:
            raise QueryError("no matches for that filter")
        return sum(m.home_goals + m.away_goals for m in matches) / len(matches)

    def home_win_rate(self, competition: str | None = None, season: int | None = None) -> float:
        matches = self._filter_matches(
            competition=self.resolve_competition(competition), season=season,
        )
        if not matches:
            raise QueryError("no matches for that filter")
        return sum(m.home_goals > m.away_goals for m in matches) / len(matches) * 100

    def biggest_wins(self, limit: int = 5, competition: str | None = None) -> list[Match]:
        comp = self.resolve_competition(competition)
        matches = [m for m in self.matches if comp is None or m.competition == comp]
        return sorted(
            (m for m in matches if m.margin > 0),
            key=lambda m: (m.margin, m.home_goals + m.away_goals, m.date),
            reverse=True,
        )[:limit]

    def best_away_records(
        self,
        *,
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 10,
        limit: int = 5,
    ) -> list[tuple[str, Record]]:
        comp = self.resolve_competition(competition)
        matches = self._filter_matches(competition=comp, season=season)
        away_by_team: dict[str, list[Match]] = defaultdict(list)
        for m in matches:
            away_by_team[m.away_key].append(m)
        rows = []
        for key, team_matches in away_by_team.items():
            record = _tally(team_matches, key)
            if record.played >= min_matches:
                rows.append((self.team_name(key), record))
        rows.sort(key=lambda row: (row[1].win_rate, row[1].played), reverse=True)
        return rows[:limit]

    # ----- players ----------------------------------------------------

    def find_players(
        self,
        *,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int | None = 20,
    ) -> list[Player]:
        """Players sorted by overall rating. ``position`` may be a code (ST) or a group."""
        positions = self._position_filter(position)
        needle_name = normalize_text(name) if name else None
        needle_nat = normalize_text(nationality) if nationality else None
        needle_club = normalize_text(club) if club else None
        result = []
        for p in self.players:
            if needle_name and needle_name not in normalize_text(p.name):
                continue
            if needle_nat and needle_nat != normalize_text(p.nationality):
                continue
            if needle_club and needle_club not in normalize_text(p.club):
                continue
            if positions and p.position not in positions:
                continue
            if min_overall is not None and p.overall < min_overall:
                continue
            result.append(p)
        result.sort(key=lambda p: (-p.overall, p.name))
        return result[:limit] if limit else result

    def _position_filter(self, position: str | None) -> set[str] | None:
        if not position:
            return None
        group = POSITION_GROUPS.get(normalize_text(position).rstrip("s"))
        if group:
            return group
        return {position.strip().upper()}

    def brazilian_players_by_club(self, limit: int = 10) -> list[tuple[str, int, float]]:
        """(club, Brazilian player count, average overall) for domestic clubs."""
        domestic = self.brazilian_team_keys()
        groups: dict[str, list[int]] = defaultdict(list)
        for p in self.players:
            if normalize_text(p.nationality) != "brazil":
                continue
            if team_key(p.club) not in domestic:
                continue
            groups[p.club].append(p.overall)
        rows = [(club, len(ovr), sum(ovr) / len(ovr)) for club, ovr in groups.items()]
        rows.sort(key=lambda row: (-row[1], -row[2], row[0]))
        return rows[:limit]
