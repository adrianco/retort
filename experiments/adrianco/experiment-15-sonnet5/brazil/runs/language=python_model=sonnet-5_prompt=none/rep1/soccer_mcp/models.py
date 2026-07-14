"""Unified data models shared across all match/player sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class Match:
    source: str  # dataset key, e.g. "brasileirao"
    competition: str  # display name, e.g. "Brasileirao Serie A"
    season: int | None
    match_date: date | None
    home_team_key: str
    home_team: str
    away_team_key: str
    away_team: str
    home_goal: int
    away_goal: int
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    home_team_raw: str = ""
    away_team_raw: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def result(self) -> str:
        if self.home_goal > self.away_goal:
            return "home_win"
        if self.away_goal > self.home_goal:
            return "away_win"
        return "draw"

    @property
    def goal_difference(self) -> int:
        return abs(self.home_goal - self.away_goal)

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home_team_key, self.away_team_key)

    def opponent_key(self, team_key: str) -> str | None:
        if team_key == self.home_team_key:
            return self.away_team_key
        if team_key == self.away_team_key:
            return self.home_team_key
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.match_date.isoformat() if self.match_date else None,
            "round": self.round,
            "stage": self.stage,
            "venue": self.venue,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "result": self.result,
            "source": self.source,
        }


@dataclass
class Player:
    player_id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str | None
    jersey_number: int | None
    height: str | None
    weight: str | None
    attributes: dict[str, Any] = field(default_factory=dict)

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
        }
