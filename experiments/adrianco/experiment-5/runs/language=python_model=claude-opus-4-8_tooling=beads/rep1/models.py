"""
================================================================================
Module: models.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Context
-------
Defines the two normalized record types that every CSV row is mapped onto by
``data_loader.py`` and that the knowledge graph / query engine operate on:

* ``Match``  - one football match (any competition, any source file)
* ``Player`` - one FIFA player row

Keeping these as plain ``dataclasses`` (stdlib only) means they serialise
cleanly to dicts for the MCP/JSON layer and are easy to assert on in tests.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Match:
    """A single match, normalized across all source datasets."""

    competition: str                 # e.g. "Brasileirão Série A", "Copa Libertadores"
    season: Optional[int]            # year
    date: str                        # ISO "YYYY-MM-DD" ("" if unknown)
    home_team: str                   # canonical display name
    away_team: str                   # canonical display name
    home_key: str                    # normalize_key(home_team)
    away_key: str                    # normalize_key(away_team)
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: str = ""
    stage: str = ""
    arena: str = ""
    datetime_raw: str = ""
    sources: list[str] = field(default_factory=list)
    # Optional extended stats (only present in BR-Football-Dataset.csv)
    home_corner: Optional[float] = None
    away_corner: Optional[float] = None
    home_shots: Optional[float] = None
    away_shots: Optional[float] = None
    home_attack: Optional[float] = None
    away_attack: Optional[float] = None

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def winner(self) -> Optional[str]:
        """Return 'home', 'away', 'draw', or None if score unknown."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return "home"
        if self.away_goal > self.home_goal:
            return "away"
        return "draw"

    @property
    def total_goals(self) -> Optional[int]:
        return None if not self.has_score else self.home_goal + self.away_goal

    def score_str(self) -> str:
        if not self.has_score:
            return "?-?"
        return f"{self.home_goal}-{self.away_goal}"

    def summary(self) -> str:
        """One-line human readable summary used in formatted answers."""
        bits = []
        if self.date:
            bits.append(self.date)
        line = f"{self.home_team} {self.score_str()} {self.away_team}"
        ctx = self.competition
        if self.season:
            ctx += f" {self.season}"
        if self.round:
            ctx += f" Round {self.round}"
        elif self.stage:
            ctx += f" {self.stage}"
        prefix = (bits[0] + ": ") if bits else ""
        return f"{prefix}{line} ({ctx})"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["winner"] = self.winner
        d["total_goals"] = self.total_goals
        return d


@dataclass
class Player:
    """A FIFA player record (subset of the many FIFA columns)."""

    player_id: str
    name: str
    nationality: str
    club: str
    club_key: str
    position: str = ""
    age: Optional[int] = None
    overall: Optional[int] = None
    potential: Optional[int] = None
    jersey_number: str = ""
    height: str = ""
    weight: str = ""
    value: str = ""
    wage: str = ""
    preferred_foot: str = ""

    def summary(self) -> str:
        parts = [self.name]
        if self.overall is not None:
            parts.append(f"Overall: {self.overall}")
        if self.position:
            parts.append(f"Position: {self.position}")
        if self.club:
            parts.append(f"Club: {self.club}")
        return " - ".join(parts[:1]) + (" (" + ", ".join(parts[1:]) + ")" if len(parts) > 1 else "")

    def to_dict(self) -> dict:
        return asdict(self)
