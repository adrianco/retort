"""
Domain model.

Context
-------
Six CSV files with six different schemas are normalised into just three record
types -- :class:`Team`, :class:`Match` and :class:`Player` -- plus a handful of
derived statistic containers.  Every loader in :mod:`brazilian_soccer.loaders`
emits these, so the graph and query layers never have to know which file a row
came from (``Match.sources`` keeps that provenance for reporting).

Design notes
------------
* Scores are ``int | None`` because the Copa do Brasil file stores ``NA`` for a
  handful of unplayed/abandoned ties, and one Libertadores final has ``-``.
  Everything downstream filters on :attr:`Match.has_score` before aggregating.
* ``Match.sources`` is a list because the datasets overlap heavily (Serie A
  2014-2019 appears in three files); de-duplication merges the rows and keeps
  every contributing dataset key.
* All records are plain dataclasses -- JSON serialisation for MCP responses is
  handled by the explicit ``to_dict`` methods so tool output stays stable.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Team",
    "Competition",
    "Match",
    "Player",
    "TeamRecord",
    "StandingRow",
    "HeadToHead",
    "COMPETITIONS",
    "competition_name",
]


@dataclass(frozen=True, slots=True)
class Competition:
    """A tournament the datasets cover."""

    id: str
    name: str
    short_name: str
    kind: str  # "league" or "cup"
    country: str = "BRA"
    aliases: tuple[str, ...] = ()


COMPETITIONS: tuple[Competition, ...] = (
    Competition(
        id="serie-a",
        name="Campeonato Brasileiro Série A",
        short_name="Brasileirão",
        kind="league",
        aliases=(
            "brasileirao",
            "brasileirão",
            "serie a",
            "série a",
            "seriea",
            "campeonato brasileiro",
            "brazilian league",
            "brazilian championship",
            "first division",
        ),
    ),
    Competition(
        id="serie-b",
        name="Campeonato Brasileiro Série B",
        short_name="Série B",
        kind="league",
        aliases=("serie b", "série b", "brasileirao serie b", "second division"),
    ),
    Competition(
        id="serie-c",
        name="Campeonato Brasileiro Série C",
        short_name="Série C",
        kind="league",
        aliases=("serie c", "série c", "brasileirao serie c", "third division"),
    ),
    Competition(
        id="copa-do-brasil",
        name="Copa do Brasil",
        short_name="Copa do Brasil",
        kind="cup",
        aliases=("copa do brasil", "brazilian cup", "cup", "copa"),
    ),
    Competition(
        id="libertadores",
        name="Copa Libertadores",
        short_name="Libertadores",
        kind="cup",
        country="CONMEBOL",
        aliases=("libertadores", "copa libertadores", "conmebol libertadores"),
    ),
)

_COMPETITIONS_BY_ID = {comp.id: comp for comp in COMPETITIONS}


def competition_name(competition_id: str) -> str:
    """Human readable name for a competition id (falls back to the id)."""

    comp = _COMPETITIONS_BY_ID.get(competition_id)
    return comp.name if comp else competition_id


@dataclass(frozen=True, slots=True)
class Team:
    """A canonical club identity shared across every dataset."""

    id: str
    name: str
    state: str | None = None
    country: str = "BRA"
    nicknames: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    @property
    def display_name(self) -> str:
        """Name with the disambiguating state, e.g. ``"Botafogo (RJ)"``."""

        if self.state and self.country == "BRA":
            return f"{self.name} ({self.state})"
        if self.country not in ("BRA", ""):
            return f"{self.name} ({self.country})"
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "state": self.state,
            "country": self.country,
            "nicknames": list(self.nicknames),
        }


@dataclass(slots=True)
class Match:
    """One fixture, normalised from any of the five match datasets."""

    id: str
    competition_id: str
    season: int | None
    date: dt.date | None
    home_team_id: str
    away_team_id: str
    home_goals: int | None = None
    away_goals: int | None = None
    kickoff: str | None = None
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    home_team_raw: str = ""
    away_team_raw: str = ""
    sources: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    # -- derived -----------------------------------------------------------
    @property
    def has_score(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def total_goals(self) -> int | None:
        if not self.has_score:
            return None
        return self.home_goals + self.away_goals  # type: ignore[operator]

    @property
    def goal_difference(self) -> int | None:
        if not self.has_score:
            return None
        return self.home_goals - self.away_goals  # type: ignore[operator]

    @property
    def result(self) -> str | None:
        """``"H"`` home win, ``"A"`` away win, ``"D"`` draw, ``None`` unknown."""

        diff = self.goal_difference
        if diff is None:
            return None
        if diff > 0:
            return "H"
        if diff < 0:
            return "A"
        return "D"

    @property
    def winner_id(self) -> str | None:
        result = self.result
        if result == "H":
            return self.home_team_id
        if result == "A":
            return self.away_team_id
        return None

    @property
    def loser_id(self) -> str | None:
        result = self.result
        if result == "H":
            return self.away_team_id
        if result == "A":
            return self.home_team_id
        return None

    @property
    def competition(self) -> str:
        return competition_name(self.competition_id)

    def involves(self, team_id: str) -> bool:
        return team_id in (self.home_team_id, self.away_team_id)

    def opponent_of(self, team_id: str) -> str | None:
        if team_id == self.home_team_id:
            return self.away_team_id
        if team_id == self.away_team_id:
            return self.home_team_id
        return None

    def goals_for(self, team_id: str) -> int | None:
        if not self.has_score:
            return None
        if team_id == self.home_team_id:
            return self.home_goals
        if team_id == self.away_team_id:
            return self.away_goals
        return None

    def goals_against(self, team_id: str) -> int | None:
        if not self.has_score:
            return None
        if team_id == self.home_team_id:
            return self.away_goals
        if team_id == self.away_team_id:
            return self.home_goals
        return None

    def to_dict(self, names: dict[str, str] | None = None) -> dict[str, Any]:
        """JSON-ready view; ``names`` maps team id -> display name."""

        def label(team_id: str, raw: str) -> str:
            if names and team_id in names:
                return names[team_id]
            return raw or team_id

        return {
            "id": self.id,
            "competition": self.competition,
            "competition_id": self.competition_id,
            "season": self.season,
            "date": self.date.isoformat() if self.date else None,
            "kickoff": self.kickoff,
            "round": self.round,
            "stage": self.stage,
            "venue": self.venue,
            "home_team": label(self.home_team_id, self.home_team_raw),
            "away_team": label(self.away_team_id, self.away_team_raw),
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "result": self.result,
            "sources": list(self.sources),
            "stats": dict(self.stats),
        }


@dataclass(slots=True)
class Player:
    """A FIFA 19 player row, with the club linked to the match graph."""

    id: int
    name: str
    age: int | None = None
    nationality: str | None = None
    overall: int | None = None
    potential: int | None = None
    club_raw: str | None = None
    club_team_id: str | None = None
    position: str | None = None
    jersey_number: int | None = None
    height: str | None = None
    weight: str | None = None
    value: str | None = None
    wage: str | None = None
    preferred_foot: str | None = None
    work_rate: str | None = None
    contract_valid_until: str | None = None
    joined: str | None = None
    skills: dict[str, int] = field(default_factory=dict)

    @property
    def is_brazilian(self) -> bool:
        return (self.nationality or "").strip().lower() == "brazil"

    def top_skills(self, count: int = 5) -> list[tuple[str, int]]:
        return sorted(self.skills.items(), key=lambda kv: (-kv[1], kv[0]))[:count]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club_raw,
            "club_team_id": self.club_team_id,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "value": self.value,
            "wage": self.wage,
            "preferred_foot": self.preferred_foot,
            "work_rate": self.work_rate,
            "joined": self.joined,
            "contract_valid_until": self.contract_valid_until,
            "top_skills": [{"skill": k, "rating": v} for k, v in self.top_skills()],
        }


@dataclass(slots=True)
class TeamRecord:
    """Win/draw/loss + goals aggregate for a team over a set of matches."""

    team_id: str
    team_name: str
    scope: str = "all"  # "all" | "home" | "away"
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def add(self, scored: int, conceded: int) -> None:
        self.played += 1
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
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return (self.wins / self.played * 100.0) if self.played else 0.0

    @property
    def points_per_game(self) -> float:
        return (self.points / self.played) if self.played else 0.0

    @property
    def goals_for_per_game(self) -> float:
        return (self.goals_for / self.played) if self.played else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "team": self.team_name,
            "scope": self.scope,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": round(self.win_rate, 1),
            "points_per_game": round(self.points_per_game, 2),
        }


@dataclass(slots=True)
class StandingRow:
    """One line of a calculated league table."""

    position: int
    record: TeamRecord
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = self.record.to_dict()
        data["position"] = self.position
        data["note"] = self.note
        return data


@dataclass(slots=True)
class HeadToHead:
    """Aggregated meetings between two clubs."""

    team_a_id: str
    team_a: str
    team_b_id: str
    team_b: str
    matches: list[Match] = field(default_factory=list)
    team_a_wins: int = 0
    team_b_wins: int = 0
    draws: int = 0
    team_a_goals: int = 0
    team_b_goals: int = 0

    @property
    def played(self) -> int:
        return self.team_a_wins + self.team_b_wins + self.draws

    def to_dict(self, names: dict[str, str] | None = None) -> dict[str, Any]:
        return {
            "team_a": self.team_a,
            "team_b": self.team_b,
            "team_a_id": self.team_a_id,
            "team_b_id": self.team_b_id,
            "played": self.played,
            "team_a_wins": self.team_a_wins,
            "team_b_wins": self.team_b_wins,
            "draws": self.draws,
            "team_a_goals": self.team_a_goals,
            "team_b_goals": self.team_b_goals,
            "matches": [match.to_dict(names) for match in self.matches],
        }
