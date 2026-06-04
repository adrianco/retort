"""
================================================================================
Module: brazilian_soccer_mcp.models
--------------------------------------------------------------------------------
Context:
    Defines the immutable domain objects that flow through the system: a unified
    ``Match`` record (every competition / source CSV is normalized into this
    shape) and a ``Player`` record sourced from the FIFA database.

Responsibility:
    Provide typed, hashable, serializable value objects plus small helpers
    (result, winner, dedup key) so the knowledge-graph and MCP layers never have
    to reason about raw CSV columns. Kept dependency-free (stdlib dataclasses).
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .normalize import team_key

# Canonical competition labels used across the project.
BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"


@dataclass(frozen=True)
class Match:
    """A single normalized match from any source dataset."""

    competition: str
    season: Optional[int]
    match_date: Optional[date]
    home_team: str
    away_team: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    home_state: Optional[str] = None
    away_state: Optional[str] = None
    source: str = ""

    # ----- derived helpers -------------------------------------------------
    @property
    def played(self) -> bool:
        """True when both scores are known (the match has a usable result)."""
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.played:
            return None
        return self.home_goal + self.away_goal

    @property
    def winner(self) -> Optional[str]:
        """Return the winning team name, or ``None`` for a draw / unplayed match."""
        if not self.played:
            return None
        if self.home_goal > self.away_goal:
            return self.home_team
        if self.away_goal > self.home_goal:
            return self.away_team
        return None

    @property
    def is_draw(self) -> bool:
        return self.played and self.home_goal == self.away_goal

    def involves(self, key: str) -> bool:
        return team_key(self.home_team) == key or team_key(self.away_team) == key

    def dedup_key(self) -> tuple:
        """Identity used to collapse the same match appearing in several files.

        Keyed on (date, both team keys, both scores) so the historical and the
        modern Brasileirão files do not double-count overlapping seasons.
        """
        return (
            self.match_date,
            team_key(self.home_team),
            team_key(self.away_team),
            self.home_goal,
            self.away_goal,
        )

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.match_date.isoformat() if self.match_date else None,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "round": self.round,
            "stage": self.stage,
            "score": self.score_str,
            "source": self.source,
        }

    @property
    def score_str(self) -> str:
        if not self.played:
            return "vs"
        return f"{self.home_goal}-{self.away_goal}"

    def summary(self) -> str:
        """One-line human readable summary used in formatted answers."""
        when = self.match_date.isoformat() if self.match_date else "????-??-??"
        ctx = self.competition
        if self.season:
            ctx += f" {self.season}"
        if self.round:
            ctx += f" Round {self.round}"
        elif self.stage:
            ctx += f" {self.stage}"
        return f"{when}: {self.home_team} {self.score_str} {self.away_team} ({ctx})"


@dataclass(frozen=True)
class Player:
    """A FIFA-database player record (subset of useful columns)."""

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
    extra: dict = field(default_factory=dict, compare=False)

    def to_dict(self) -> dict:
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

    def summary(self) -> str:
        rating = self.overall if self.overall is not None else "?"
        return (
            f"{self.name} - Overall: {rating}, Position: {self.position or '?'}, "
            f"Club: {self.club or 'Free agent'}"
        )
