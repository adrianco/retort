"""
Context
=======
Domain records for the Brazilian Soccer MCP server.

``Match`` is the unified representation every CSV schema is loaded into, so the
query engine never needs to know which file a match came from. ``Player`` is the
FIFA player record. Both expose ``as_dict`` producing the JSON-friendly shape
returned to MCP clients.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Match:
    competition: str
    season: Optional[int]
    date: Optional[str]          # ISO "YYYY-MM-DD"
    home_team: str               # normalized display name
    away_team: str               # normalized display name
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    source: str = ""             # originating CSV file name

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def goal_margin(self) -> int:
        if not self.has_score:
            return 0
        return abs(self.home_goal - self.away_goal)

    @property
    def total_goals(self) -> int:
        if not self.has_score:
            return 0
        return self.home_goal + self.away_goal

    def as_dict(self) -> dict:
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
        }


@dataclass(frozen=True)
class Player:
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str                    # normalized display name
    position: str

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
        }
