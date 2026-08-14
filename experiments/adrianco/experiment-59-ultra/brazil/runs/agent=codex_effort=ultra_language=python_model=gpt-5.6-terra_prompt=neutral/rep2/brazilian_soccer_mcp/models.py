"""Canonical records used by the query service.

The model is graph-shaped: a match connects home and away teams to a
competition and season, while a player connects to a FIFA club snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class MatchRecord:
    """A match normalized from one of the five match datasets."""

    id: str
    source: str
    source_file: str
    competition: str
    competition_key: str
    match_date: date | None
    season: int | None
    round: str | None
    stage: str | None
    home_team: str
    away_team: str
    home_team_key: str
    away_team_key: str
    home_goals: int | None
    away_goals: int | None
    home_state: str | None = None
    away_state: str | None = None
    venue: str | None = None
    statistics: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Whether this record can contribute to result-based aggregates."""

        return self.home_goals is not None and self.away_goals is not None

    @property
    def goal_margin(self) -> int | None:
        if not self.is_complete:
            return None
        return abs(self.home_goals - self.away_goals)  # type: ignore[operator]

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-safe match data with provenance intact."""

        return {
            "id": self.id,
            "source": self.source,
            "source_file": self.source_file,
            "competition": self.competition,
            "date": self.match_date.isoformat() if self.match_date else None,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "home_state": self.home_state,
            "away_state": self.away_state,
            "venue": self.venue,
            "statistics": self.statistics,
        }


@dataclass(frozen=True, slots=True)
class PlayerRecord:
    """A player and their FIFA-database club snapshot, not a match lineup."""

    id: str
    name: str
    name_key: str
    age: int | None
    nationality: str
    nationality_key: str
    overall: int | None
    potential: int | None
    club: str
    club_key: str
    position: str
    jersey_number: int | None
    height: str | None
    weight: str | None
    attributes: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-safe player data and its temporal limitation."""

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
            "attributes": self.attributes,
            "club_data_note": (
                "Club is a FIFA dataset snapshot and does not establish a historical match lineup."
            ),
        }

