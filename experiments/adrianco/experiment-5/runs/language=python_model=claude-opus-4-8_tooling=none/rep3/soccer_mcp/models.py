# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : soccer_mcp.models
# Purpose : Typed, immutable records shared across the package. A `Match` is the
#           normalised representation of one game from any of the five match
#           datasets; a `Player` is one row of the FIFA player database.
# Notes   : Team names are stored both raw (as they appear in the source CSV)
#           and normalised (suffix-stripped) so queries can match loosely while
#           output can still show the original name. Optional extended stats
#           (shots, corners ...) are only populated for the BR-Football dataset.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Match:
    """One football match, normalised across all source datasets."""

    competition: str          # e.g. "Brasileirão", "Copa do Brasil", "Libertadores"
    season: Optional[int]     # year the season belongs to (may be None)
    date: Optional[str]       # ISO date "YYYY-MM-DD" when known, else None
    home_team: str            # raw home team name (with any suffix)
    away_team: str            # raw away team name
    home_team_norm: str       # normalised (suffix/accent-stripped) home name
    away_team_norm: str       # normalised away name
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    venue: Optional[str] = None
    source: str = ""          # source CSV filename
    stats: dict = field(default_factory=dict)  # optional extended stats

    @property
    def winner(self) -> Optional[str]:
        """Return raw name of the winning team, or None for a draw / unknown."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return self.home_team
        if self.away_goal > self.home_goal:
            return self.away_team
        return None

    @property
    def is_draw(self) -> bool:
        return (
            self.home_goal is not None
            and self.away_goal is not None
            and self.home_goal == self.away_goal
        )

    @property
    def total_goals(self) -> Optional[int]:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal + self.away_goal

    def score_line(self) -> str:
        """Human readable score line, e.g. 'Flamengo 2-1 Fluminense'."""
        hg = "?" if self.home_goal is None else self.home_goal
        ag = "?" if self.away_goal is None else self.away_goal
        return f"{self.home_team} {hg}-{ag} {self.away_team}"


@dataclass(frozen=True)
class Player:
    """One FIFA player row."""

    player_id: Optional[int]
    name: str
    name_norm: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    club_norm: str
    position: str
    jersey_number: Optional[str] = None
    height: str = ""
    weight: str = ""
    value: str = ""
    wage: str = ""
    preferred_foot: str = ""
