"""Canonical domain models shared by every dataset adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class Match:
    date: date
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    season: int
    competition: str
    source: str
    round_or_stage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["date"] = self.date.isoformat()
        return value


@dataclass(frozen=True, slots=True)
class Player:
    id: int
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    attributes: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

