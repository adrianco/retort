"""
Context
=======
Module: brazilian_soccer_mcp.models
Purpose: Plain dataclasses describing the two node types in the knowledge
graph - :class:`Match` and :class:`Player`.

These objects are produced by :mod:`brazilian_soccer_mcp.data_loader`, indexed
by :mod:`brazilian_soccer_mcp.knowledge_graph` and serialised to dictionaries
for the MCP tools.  Keeping them as light dataclasses (instead of pandas rows)
keeps the project dependency-free and easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .normalize import extract_state, team_key


@dataclass
class Match:
    """A single football match from one of the match datasets."""

    competition: str
    season: Optional[int]
    home_team: str
    away_team: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    source: str
    match_date: Optional[date] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    arena: Optional[str] = None
    # Optional extended statistics (only present in BR-Football-Dataset).
    stats: dict = field(default_factory=dict)

    # Derived matching keys, filled in __post_init__.
    # ``*_base`` is the state-stripped key; ``*_state`` the state code; ``*_id``
    # is the canonical team id assigned by the KnowledgeGraph (it equals the
    # base unless the base is ambiguous, in which case the state is appended).
    home_base: str = field(default="", init=False)
    away_base: str = field(default="", init=False)
    home_state: str = field(default="", init=False)
    away_state: str = field(default="", init=False)
    home_id: str = field(default="", init=False)
    away_id: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.home_base = team_key(self.home_team)
        self.away_base = team_key(self.away_team)
        self.home_state = extract_state(self.home_team)
        self.away_state = extract_state(self.away_team)
        # Default the id to the base; the graph refines ambiguous ones.
        self.home_id = self.home_base
        self.away_id = self.away_base

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.has_score:
            return None
        return self.home_goal + self.away_goal

    @property
    def winner_id(self) -> Optional[str]:
        """Return the team id of the winner, or ``None`` for a draw/no score."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_id
        if self.away_goal > self.home_goal:
            return self.away_id
        return None  # draw

    def involves(self, team_id: str) -> bool:
        return team_id in (self.home_id, self.away_id)

    def date_str(self) -> str:
        return self.match_date.isoformat() if self.match_date else "unknown date"

    def score_line(self) -> str:
        """Human readable one-liner, e.g. ``2012-05-19: Palmeiras 1-1 Portuguesa``."""
        if self.has_score:
            score = f"{self.home_goal}-{self.away_goal}"
        else:
            score = "vs"
        parts = [f"{self.date_str()}: {self.home_team} {score} {self.away_team}"]
        ctx = self.competition
        if self.season:
            ctx += f" {self.season}"
        if self.round:
            ctx += f" Round {self.round}"
        elif self.stage:
            ctx += f" {self.stage}"
        parts.append(f"({ctx})")
        return " ".join(parts)

    def to_dict(self) -> dict:
        d = {
            "competition": self.competition,
            "season": self.season,
            "date": self.match_date.isoformat() if self.match_date else None,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "round": self.round,
            "stage": self.stage,
            "arena": self.arena,
            "source": self.source,
        }
        if self.stats:
            d["stats"] = self.stats
        return d


@dataclass
class Player:
    """A player row from the FIFA dataset."""

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
    value: str = ""
    wage: str = ""
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
            "preferred_foot": self.preferred_foot,
            "value": self.value,
            "wage": self.wage,
            "skills": self.skills,
        }

    def summary_line(self) -> str:
        bits = [self.name]
        if self.overall is not None:
            bits.append(f"Overall: {self.overall}")
        if self.position:
            bits.append(f"Position: {self.position}")
        if self.club:
            bits.append(f"Club: {self.club}")
        return " - ".join(bits)
