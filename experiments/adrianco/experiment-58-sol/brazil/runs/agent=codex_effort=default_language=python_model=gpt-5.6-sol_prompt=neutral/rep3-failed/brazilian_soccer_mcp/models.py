"""Small immutable domain objects shared by loaders and analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Match:
    date: datetime
    season: int
    competition: str
    home_team: str
    away_team: str
    home_key: str
    away_key: str
    home_goals: int
    away_goals: int
    source: str
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    statistics: dict[str, float] = field(default_factory=dict)

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def goal_difference(self) -> int:
        return abs(self.home_goals - self.away_goals)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(sep=" "),
            "season": self.season,
            "competition": self.competition,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "score": f"{self.home_goals}-{self.away_goals}",
            "round": self.round,
            "stage": self.stage,
            "venue": self.venue,
            "statistics": self.statistics,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class Player:
    player_id: int
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    height: str
    weight: str
    attributes: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.player_id,
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
            "attributes": self.attributes,
        }

