"""
==============================================================================
Module: brazilian_soccer.models
==============================================================================
CONTEXT
-------
Lightweight, dependency-free value objects shared by the data loader, the
in-memory knowledge graph and the query layer. We deliberately use stdlib
``dataclasses`` (no pandas / ORM) so the core domain stays portable and the
test-suite has zero heavy dependencies.

ENTITIES
--------
* ``Match``   -- a single fixture from any of the five match datasets, with a
                 normalized competition label, parsed date/season and optional
                 extended statistics (corners, shots, attacks).
* ``Player``  -- a single FIFA player row (name, nationality, club, ratings).

Both objects pre-compute normalized keys (via
``brazilian_soccer.normalization``) so the knowledge graph can index and join
them without repeating the normalization logic.
==============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .normalization import display_name, normalize_team


@dataclass
class Match:
    """A single match/fixture from any competition."""

    competition: str                 # canonical: Brasileirão / Copa do Brasil / ...
    season: Optional[int]
    home_raw: str
    away_raw: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    source: str                      # originating CSV file name
    date: Optional[date] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    arena: Optional[str] = None
    primary: bool = True             # counts toward standings (dedup flag)
    stats: dict = field(default_factory=dict)  # extended stats (corners, shots…)

    # Derived (filled in __post_init__)
    home: str = field(init=False)
    away: str = field(init=False)
    home_key: str = field(init=False)
    away_key: str = field(init=False)

    def __post_init__(self) -> None:
        self.home = display_name(self.home_raw)
        self.away = display_name(self.away_raw)
        self.home_key = normalize_team(self.home_raw)
        self.away_key = normalize_team(self.away_raw)

    # -- convenience -------------------------------------------------------
    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> int:
        return (self.home_goal or 0) + (self.away_goal or 0)

    def winner_key(self) -> Optional[str]:
        """Canonical key of the winning team, or None for a draw/unknown."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home_key, self.away_key)

    def date_str(self) -> str:
        return self.date.isoformat() if self.date else "????-??-??"

    def describe(self) -> str:
        """One-line human readable summary, e.g.
        '2019-10-27: Flamengo 5-0 Grêmio (Brasileirão Round 32)'.
        """
        score = (
            f"{self.home_goal}-{self.away_goal}" if self.has_score else "?-?"
        )
        ctx = self.competition
        if self.round:
            ctx += f" Round {self.round}"
        elif self.stage:
            ctx += f" {self.stage}"
        return f"{self.date_str()}: {self.home} {score} {self.away} ({ctx})"


@dataclass
class Player:
    """A single FIFA player record."""

    player_id: Optional[int]
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey_number: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    preferred_foot: Optional[str] = None
    value: Optional[str] = None
    wage: Optional[str] = None

    # Derived
    club_key: str = field(init=False)
    name_key: str = field(init=False)

    def __post_init__(self) -> None:
        self.club_key = normalize_team(self.club) if self.club else ""
        from .normalization import fold_accents

        self.name_key = fold_accents(self.name or "").lower().strip()

    def describe(self) -> str:
        ovr = self.overall if self.overall is not None else "?"
        pos = self.position or "?"
        club = self.club or "Free agent"
        return f"{self.name} - Overall: {ovr}, Position: {pos}, Club: {club}"
