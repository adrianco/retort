"""Domain models for matches and players.

These dataclasses are the in-memory representation the repository queries over.
They are intentionally plain so they serialize cleanly to the JSON the MCP
tools return.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Match:
    competition: str
    competition_type: str  # "league" or "cup"
    home_team: str
    away_team: str
    home_goal: int | None
    away_goal: int | None
    season: int | None = None
    date: date | None = None
    round: str | None = None
    stage: str | None = None
    home_team_raw: str = ""
    away_team_raw: str = ""
    home_key: str = ""
    away_key: str = ""
    source: str = ""
    stats: dict = field(default_factory=dict)

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def winner_key(self) -> str | None:
        """Normalized key of the winning team, or None for a draw/unknown."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None

    def to_dict(self) -> dict:
        score = (
            f"{self.home_goal}-{self.away_goal}" if self.has_score else None
        )
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.date.isoformat() if self.date else None,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "score": score,
        }


@dataclass
class Player:
    id: int | None
    name: str
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    age: int | None = None
    jersey_number: int | None = None
    height: str = ""
    weight: str = ""
    name_key: str = ""
    club_key: str = ""
    nationality_key: str = ""
    position_key: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
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
