"""
================================================================================
Brazilian Soccer MCP Server - Data Models
================================================================================

CONTEXT
-------
Light-weight, dependency-free dataclasses representing the two core entities of
the knowledge graph: a football ``Match`` and a FIFA ``Player``. All six source
CSV files are normalised into ``Match`` records (except the FIFA file which maps
to ``Player`` records) by ``data_loader``.

Each model stores both human-readable display fields and pre-computed match
keys (see ``normalize.team_key``) so that the query engine can compare entities
cheaply and consistently regardless of the source file's naming convention.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from .normalize import team_key


@dataclass
class Match:
    """A single football match, normalised across all source datasets."""

    competition: str
    season: Optional[int]
    date: Optional[str]            # ISO YYYY-MM-DD
    home_team: str                 # display name (state suffix stripped)
    away_team: str                 # display name
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    home_state: Optional[str] = None
    away_state: Optional[str] = None
    stadium: Optional[str] = None
    source: str = ""               # originating dataset key
    extra: Dict[str, Any] = field(default_factory=dict)  # corners/shots/etc.

    # Derived match keys (populated in __post_init__).
    home_key: str = ""
    away_key: str = ""

    def __post_init__(self) -> None:
        self.home_key = team_key(self.home_team)
        self.away_key = team_key(self.away_team)

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.has_score:
            return None
        return self.home_goal + self.away_goal

    @property
    def winner_key(self) -> Optional[str]:
        """Match key of the winner, or ``None`` for a draw / unknown score."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None  # draw

    def involves(self, key: str) -> bool:
        return key in (self.home_key, self.away_key)

    def score_str(self) -> str:
        if not self.has_score:
            return "? - ?"
        return f"{self.home_goal}-{self.away_goal}"

    def describe(self) -> str:
        """One-line human readable description of the match."""
        date = self.date or "????-??-??"
        comp = self.competition
        rnd = ""
        if self.round:
            rnd = f", Round {self.round}"
        elif self.stage:
            rnd = f", {self.stage}"
        return (
            f"{date}: {self.home_team} {self.score_str()} {self.away_team} "
            f"({comp}{rnd})"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "round": self.round,
            "stage": self.stage,
            "stadium": self.stadium,
            "source": self.source,
        }


@dataclass
class Player:
    """A FIFA player record."""

    name: str
    age: Optional[int]
    nationality: Optional[str]
    overall: Optional[int]
    potential: Optional[int]
    club: Optional[str]
    position: Optional[str]
    jersey_number: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    player_id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    # Derived keys.
    name_key: str = ""
    club_key: str = ""
    nationality_key: str = ""

    def __post_init__(self) -> None:
        from .normalize import strip_accents

        self.name_key = strip_accents(self.name or "").lower()
        self.club_key = team_key(self.club or "")
        self.nationality_key = strip_accents(self.nationality or "").lower()

    def describe(self) -> str:
        ovr = self.overall if self.overall is not None else "?"
        pos = self.position or "?"
        club = self.club or "Unknown club"
        return f"{self.name} - Overall: {ovr}, Position: {pos}, Club: {club}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
        }
