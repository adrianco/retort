"""Plain data records shared by the loaders, the query layer and the tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Match:
    """One played fixture, normalised across all match datasets."""

    date: date
    competition: str
    home: str
    away: str
    home_key: str
    away_key: str
    home_goals: int
    away_goals: int
    season: int
    source: str
    round: str | None = None
    stage: str | None = None

    @property
    def margin(self) -> int:
        return abs(self.home_goals - self.away_goals)

    def goals_for(self, team_key: str) -> int:
        return self.home_goals if team_key == self.home_key else self.away_goals

    def goals_against(self, team_key: str) -> int:
        return self.away_goals if team_key == self.home_key else self.home_goals

    def result_for(self, team_key: str) -> str:
        """'W', 'D' or 'L' from the point of view of ``team_key``."""
        if self.home_goals == self.away_goals:
            return "D"
        home_won = self.home_goals > self.away_goals
        return "W" if home_won == (team_key == self.home_key) else "L"


@dataclass(frozen=True)
class Player:
    """One FIFA player record."""

    id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    height: str
    weight: str
    value: str
    wage: str
    preferred_foot: str
    attributes: dict[str, int | None] = field(default_factory=dict)
