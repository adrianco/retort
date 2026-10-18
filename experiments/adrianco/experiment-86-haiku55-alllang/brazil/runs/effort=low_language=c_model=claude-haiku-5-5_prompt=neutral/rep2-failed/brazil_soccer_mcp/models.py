"""Core record types shared by the loaders, queries and server."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .normalize import Team


@dataclass(frozen=True)
class Match:
    played_on: date
    competition: str          # e.g. "Brasileirão Série A", "Copa do Brasil"
    season: int
    home: Team
    away: Team
    home_goals: int
    away_goals: int
    round_or_stage: Optional[str] = None
    source: str = ""

    @property
    def result(self) -> str:
        if self.home_goals > self.away_goals:
            return "home"
        if self.home_goals < self.away_goals:
            return "away"
        return "draw"


@dataclass(frozen=True)
class Player:
    player_id: int
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    value: str
    wage: str
    height: str
    weight: str
    preferred_foot: str
    jersey_number: Optional[int]
