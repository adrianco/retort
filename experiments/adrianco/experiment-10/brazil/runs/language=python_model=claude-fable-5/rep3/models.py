"""Data model for the Brazilian soccer knowledge graph.

The graph has three entity types — matches, teams and players — linked by
normalized team identities (:class:`team_names.TeamKey`).  Matches reference
two teams; players reference a club; teams are derived from both.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date
from typing import Optional

from team_names import TeamKey

# Canonical competition names.
SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"


@dataclass
class Match:
    """One match, unified across all source CSV files."""

    competition: str
    source: str                      # which CSV the row came from
    date: Optional[Date]
    season: Optional[int]
    home_name: str                   # display name as it appears in the source
    away_name: str
    home_key: TeamKey
    away_key: TeamKey
    home_goals: Optional[int]
    away_goals: Optional[int]
    round: Optional[str] = None      # league round or cup round
    stage: Optional[str] = None      # Libertadores stage (group stage, final…)
    time: Optional[str] = None
    extras: dict = field(default_factory=dict)   # stadium, corners, shots…

    @property
    def has_score(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    def winner_key(self) -> Optional[TeamKey]:
        """TeamKey of the winner, or None for a draw / unknown score."""
        if not self.has_score:
            return None
        if self.home_goals > self.away_goals:
            return self.home_key
        if self.away_goals > self.home_goals:
            return self.away_key
        return None

    def score_line(self) -> str:
        if not self.has_score:
            return f"{self.home_name} vs {self.away_name} (score unknown)"
        return (
            f"{self.home_name} {self.home_goals}-{self.away_goals} "
            f"{self.away_name}"
        )

    def context(self) -> str:
        """Short competition/round context, e.g. 'Brasileirão Série A Round 22'."""
        parts = [self.competition]
        if self.stage:
            parts.append(self.stage)
        elif self.round:
            parts.append(f"Round {self.round}")
        return " ".join(parts)


@dataclass
class Player:
    """One player from the FIFA dataset."""

    player_id: str
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey_number: Optional[int]
    value: str
    wage: str
    height: str
    weight: str
    preferred_foot: str
    skills: dict[str, int] = field(default_factory=dict)
