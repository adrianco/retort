"""Data models for matches and players."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Match:
    """A single match, normalized across all source datasets."""

    home: str                      # display name, suffix stripped
    away: str
    home_key: str                  # canonical matching key
    away_key: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    competition: str
    season: Optional[int] = None
    match_date: Optional[date] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    venue: Optional[str] = None     # stadium / arena, when available
    source: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def date_str(self) -> str:
        return self.match_date.isoformat() if self.match_date else "unknown"

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.has_score:
            return None
        return self.home_goal + self.away_goal

    def winner_key(self) -> Optional[str]:
        """Return the winning team key, or ``None`` for a draw / no score."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None  # draw

    def signature(self) -> tuple:
        """A key used to deduplicate the same match across datasets."""
        return (self.date_str, self.home_key, self.away_key,
                self.home_goal, self.away_goal)

    def describe(self) -> str:
        score = (f"{self.home_goal}-{self.away_goal}"
                 if self.has_score else "vs")
        parts = [f"{self.date_str}: {self.home} {score} {self.away}"]
        meta = [self.competition]
        if self.season:
            meta.append(str(self.season))
        if self.round:
            meta.append(f"Round {self.round}")
        if self.stage:
            meta.append(self.stage)
        return f"{parts[0]} ({', '.join(meta)})"


@dataclass
class Player:
    """A FIFA player record."""

    player_id: Optional[int]
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey_number: Optional[int] = None
    height: str = ""
    weight: str = ""
    preferred_foot: str = ""
    value: str = ""
    wage: str = ""

    def describe(self) -> str:
        bits = [self.name]
        if self.overall is not None:
            bits.append(f"Overall: {self.overall}")
        if self.position:
            bits.append(f"Position: {self.position}")
        if self.club:
            bits.append(f"Club: {self.club}")
        return " - ".join(bits)
