"""
================================================================================
Context: Brazilian Soccer MCP Server
Module:   brazilian_soccer.models
--------------------------------------------------------------------------------
Purpose:
    The two value objects that flow through the whole system: ``Match`` (one
    game from any of the five match datasets) and ``Player`` (one row of the
    FIFA player database). Both carry a normalised key for matching plus the
    original display fields, and both know how to render themselves as a plain
    dict for JSON/MCP responses.

Dependencies: standard library only (dataclasses, datetime).
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Match:
    """A single match, unified across every source file."""

    competition: str               # "Brasileirao", "Copa do Brasil", ...
    season: int | None             # year
    home_team: str                 # normalised display name
    away_team: str
    home_key: str                  # canonical match key (see normalize.team_key)
    away_key: str
    home_goal: int | None
    away_goal: int | None
    match_date: date | None = None
    round: str | None = None       # round number or cup/knockout stage
    venue: str | None = None
    source: str = ""               # originating CSV filename
    stats: dict = field(default_factory=dict)  # corners/shots/etc. when present

    @property
    def winner_key(self) -> str | None:
        """Canonical key of the winning team, or None for a draw / unknown."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None  # draw

    @property
    def total_goals(self) -> int | None:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal + self.away_goal

    @property
    def goal_difference(self) -> int | None:
        if self.home_goal is None or self.away_goal is None:
            return None
        return abs(self.home_goal - self.away_goal)

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
            "venue": self.venue,
            "source": self.source,
            **({"stats": self.stats} if self.stats else {}),
        }

    def describe(self) -> str:
        """One-line human summary, e.g. '2019-11-23: Flamengo 3-1 ...'."""
        d = self.match_date.isoformat() if self.match_date else f"{self.season or '?'}"
        hg = "?" if self.home_goal is None else self.home_goal
        ag = "?" if self.away_goal is None else self.away_goal
        extra = []
        if self.competition:
            extra.append(self.competition)
        if self.round:
            extra.append(f"Round {self.round}" if str(self.round).isdigit() else str(self.round))
        suffix = f" ({', '.join(extra)})" if extra else ""
        return f"{d}: {self.home_team} {hg}-{ag} {self.away_team}{suffix}"


@dataclass
class Player:
    """A FIFA-database player."""

    player_id: str
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str | None
    position: str | None
    jersey_number: str | None = None
    height: str | None = None
    weight: str | None = None
    value: str | None = None
    skills: dict = field(default_factory=dict)

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
            "value": self.value,
        }

    def describe(self) -> str:
        rating = f"Overall: {self.overall}" if self.overall is not None else "Overall: ?"
        pos = self.position or "?"
        club = self.club or "Free agent"
        return f"{self.name} - {rating}, Position: {pos}, Club: {club}"
