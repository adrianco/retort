"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.models
Purpose   : Lightweight dataclasses representing the entities in the knowledge
            graph: Match and Player.

These are deliberately simple, immutable-ish records. Each Match carries both the
raw team names (as they appeared in the source file) and normalized keys used for
matching, plus a derived `winner` ("home" / "away" / "draw"). Players mirror the
useful subset of the FIFA dataset columns.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .normalize import display_team_name, normalize_team_name


@dataclass
class Match:
    """A single soccer match from any of the five match datasets."""

    competition: str            # "Brasileirao", "Copa do Brasil", "Libertadores", ...
    home_team: str              # display name
    away_team: str              # display name
    home_goal: Optional[int]
    away_goal: Optional[int]
    season: Optional[int] = None
    match_date: Optional[date] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    stadium: Optional[str] = None
    source: str = ""            # source CSV filename

    # Normalized keys (filled in __post_init__).
    home_key: str = field(default="", init=False)
    away_key: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.home_key = normalize_team_name(self.home_team)
        self.away_key = normalize_team_name(self.away_team)
        # Clean display names.
        self.home_team = display_team_name(self.home_team)
        self.away_team = display_team_name(self.away_team)

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.has_score:
            return None
        return self.home_goal + self.away_goal

    @property
    def winner(self) -> Optional[str]:
        """Return 'home', 'away' or 'draw'; None if score unknown."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return "home"
        if self.away_goal > self.home_goal:
            return "away"
        return "draw"

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home_key, self.away_key)

    def score_str(self) -> str:
        if not self.has_score:
            return "?-?"
        return f"{self.home_goal}-{self.away_goal}"

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "season": self.season,
            "date": self.match_date.isoformat() if self.match_date else None,
            "round": self.round,
            "stage": self.stage,
            "stadium": self.stadium,
            "winner": self.winner,
            "source": self.source,
        }


@dataclass
class Player:
    """A player record from the FIFA dataset."""

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
    preferred_foot: str = ""

    name_key: str = field(default="", init=False)
    nationality_key: str = field(default="", init=False)
    club_key: str = field(default="", init=False)

    def __post_init__(self) -> None:
        from .normalize import strip_accents

        self.name_key = strip_accents(self.name).lower().strip()
        self.nationality_key = strip_accents(self.nationality).lower().strip()
        self.club_key = normalize_team_name(self.club)

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
            "preferred_foot": self.preferred_foot,
        }
