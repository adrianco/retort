"""Domain records for the Brazilian soccer knowledge graph.

Context
-------
Plain dataclasses shared by the loader, graph, query and formatting layers.
They are deliberately free of pandas/ORM dependencies: the whole dataset is a
few tens of thousands of rows, so pure-Python objects with pre-built indexes
comfortably meet the spec's "<2s simple / <5s aggregate" performance budget.

``Match`` is the central node type.  Extra per-match statistics (corners,
shots, attacks) only exist in ``BR-Football-Dataset.csv`` and therefore live in
the optional ``stats`` mapping rather than as first-class fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Canonical competition labels used across the whole package.
BRASILEIRAO = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

COMPETITIONS = (BRASILEIRAO, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES)

#: Competitions played as a double round-robin league, where a given ordered
#: (home, away) pair meets exactly once per season.  Used for de-duplication
#: across overlapping source files and for standings.
LEAGUE_COMPETITIONS = frozenset({BRASILEIRAO, SERIE_B, SERIE_C})

HOME_WIN = "home"
AWAY_WIN = "away"
DRAW = "draw"


@dataclass(slots=True)
class Match:
    """A single fixture, after normalisation and cross-file de-duplication."""

    competition: str
    season: int | None
    match_date: date | None
    home_key: str
    away_key: str
    home_name: str
    away_name: str
    home_goals: int | None
    away_goals: int | None
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    sources: set[str] = field(default_factory=set)
    stats: dict[str, float] = field(default_factory=dict)

    # -- derived -----------------------------------------------------------
    @property
    def has_score(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def total_goals(self) -> int | None:
        if not self.has_score:
            return None
        return self.home_goals + self.away_goals

    @property
    def goal_difference(self) -> int | None:
        if not self.has_score:
            return None
        return abs(self.home_goals - self.away_goals)

    @property
    def result(self) -> str | None:
        """``"home"``, ``"away"`` or ``"draw"``."""
        if not self.has_score:
            return None
        if self.home_goals > self.away_goals:
            return HOME_WIN
        if self.home_goals < self.away_goals:
            return AWAY_WIN
        return DRAW

    @property
    def winner_key(self) -> str | None:
        result = self.result
        if result == HOME_WIN:
            return self.home_key
        if result == AWAY_WIN:
            return self.away_key
        return None

    def involves(self, key: str) -> bool:
        return key in (self.home_key, self.away_key)

    def opponent_of(self, key: str) -> str | None:
        if key == self.home_key:
            return self.away_key
        if key == self.away_key:
            return self.home_key
        return None

    def goals_for(self, key: str) -> int | None:
        if not self.has_score:
            return None
        if key == self.home_key:
            return self.home_goals
        if key == self.away_key:
            return self.away_goals
        return None

    def goals_against(self, key: str) -> int | None:
        if not self.has_score:
            return None
        if key == self.home_key:
            return self.away_goals
        if key == self.away_key:
            return self.home_goals
        return None

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.match_date.isoformat() if self.match_date else None,
            "home_team": self.home_name,
            "away_team": self.away_name,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "score": (
                f"{self.home_goals}-{self.away_goals}" if self.has_score else None
            ),
            "round": self.round,
            "stage": self.stage,
            "venue": self.venue,
            "result": self.result,
            "sources": sorted(self.sources),
            "stats": dict(self.stats) or None,
        }


@dataclass(slots=True)
class Team:
    """A club node: canonical key plus every raw spelling seen for it."""

    key: str
    display: str
    region: str | None = None
    aliases: set[str] = field(default_factory=set)
    match_indexes: list[int] = field(default_factory=list)
    player_indexes: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.display,
            "region": self.region,
            "matches": len(self.match_indexes),
            "players_in_fifa_data": len(self.player_indexes),
            "known_as": sorted(self.aliases),
        }


@dataclass(slots=True)
class Player:
    """A FIFA-database player, linked to a club node where possible."""

    player_id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club_raw: str
    club_key: str
    position: str | None
    jersey_number: int | None
    height: str | None
    weight: str | None
    value: str | None
    wage: str | None
    preferred_foot: str | None
    skills: dict[str, int] = field(default_factory=dict)

    def to_dict(self, include_skills: bool = False) -> dict:
        data = {
            "id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club_raw or None,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "value": self.value,
            "wage": self.wage,
            "preferred_foot": self.preferred_foot,
        }
        if include_skills:
            data["skills"] = dict(self.skills)
        return data


@dataclass(slots=True)
class TeamRecord:
    """Aggregated W/D/L + goals for one team over a set of matches."""

    team_key: str
    team_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def add(self, match: Match) -> None:
        """Fold one played match into the record (scoreless rows ignored)."""
        if not match.has_score or not match.involves(self.team_key):
            return
        self.played += 1
        scored = match.goals_for(self.team_key)
        conceded = match.goals_against(self.team_key)
        self.goals_for += scored
        self.goals_against += conceded
        if scored > conceded:
            self.wins += 1
        elif scored < conceded:
            self.losses += 1
        else:
            self.draws += 1

    @property
    def points(self) -> int:
        """Three points for a win, one for a draw (modern Brazilian rules)."""
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return (self.wins / self.played * 100) if self.played else 0.0

    @property
    def points_per_game(self) -> float:
        return (self.points / self.played) if self.played else 0.0

    @property
    def goals_per_game(self) -> float:
        return (self.goals_for / self.played) if self.played else 0.0

    def to_dict(self) -> dict:
        return {
            "team": self.team_name,
            "team_key": self.team_key,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": round(self.win_rate, 1),
        }


@dataclass(slots=True)
class HeadToHead:
    """Two-team summary: overall record plus the underlying match list."""

    team_a: str
    team_b: str
    a_wins: int = 0
    b_wins: int = 0
    draws: int = 0
    a_goals: int = 0
    b_goals: int = 0
    matches: list[Match] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.matches)

    def to_dict(self, match_limit: int = 20) -> dict:
        return {
            "team_a": self.team_a,
            "team_b": self.team_b,
            "matches_found": self.total,
            f"{self.team_a}_wins": self.a_wins,
            f"{self.team_b}_wins": self.b_wins,
            "draws": self.draws,
            "goals": {self.team_a: self.a_goals, self.team_b: self.b_goals},
            "matches": [m.to_dict() for m in self.matches[:match_limit]],
        }
