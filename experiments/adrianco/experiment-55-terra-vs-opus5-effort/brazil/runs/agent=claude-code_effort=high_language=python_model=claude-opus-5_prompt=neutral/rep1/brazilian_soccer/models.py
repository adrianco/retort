"""Domain entities stored in the knowledge graph.

Context
-------
Three node types carry all the information the MCP tools need:

``Team``    a club, keyed by the canonical slug produced by
            :func:`brazilian_soccer.clubs.resolve_club`.
``Match``   one fixture.  A ``Match`` may be assembled from several CSV rows:
            the same Série A game appears in up to three of the provided files,
            so the loader merges them and records every contributing source in
            ``sources``.  Extended statistics (corners, shots, attacks) only
            exist in the BR-Football file and are merged in when available.
``Player``  a FIFA 19 player record, linked to a ``Team`` through
            ``club_slug`` so that player and match data can be joined.

All three are plain dataclasses with ``to_dict`` methods, because the MCP
protocol ultimately needs JSON.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Team", "Match", "Player", "MATCH_STAT_FIELDS"]


#: Extended per-side statistics available only in ``BR-Football-Dataset.csv``.
MATCH_STAT_FIELDS = ("corners", "attacks", "shots")


@dataclass
class Team:
    """A club node in the knowledge graph."""

    slug: str
    name: str
    state: str | None = None
    known: bool = False
    #: Every raw spelling seen for this club across the datasets.
    aliases: set[str] = field(default_factory=set)

    @property
    def display_name(self) -> str:
        if self.state:
            return f"{self.name} ({self.state.upper()})"
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "state": self.state.upper() if self.state else None,
            "curated": self.known,
            "aliases": sorted(self.aliases),
        }


@dataclass
class Match:
    """A single fixture, possibly merged from several source rows."""

    match_id: str
    competition: str            # competition slug
    season: int | None
    date: _dt.date | None
    home_slug: str
    away_slug: str
    home_name: str
    away_name: str
    #: The spelling used in the source CSV, kept for provenance.
    home_raw: str = ""
    away_raw: str = ""
    home_goals: int | None = None
    away_goals: int | None = None
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    kickoff: str | None = None
    sources: tuple[str, ...] = ()
    #: ``{"home": {"corners": 6, ...}, "away": {...}}`` when available.
    stats: dict[str, dict[str, float]] = field(default_factory=dict)

    # -- derived -----------------------------------------------------------
    @property
    def played(self) -> bool:
        """True when both scores are known (a few rows have ``"-"``)."""
        return self.home_goals is not None and self.away_goals is not None

    @property
    def total_goals(self) -> int | None:
        if not self.played:
            return None
        return self.home_goals + self.away_goals

    @property
    def goal_margin(self) -> int | None:
        if not self.played:
            return None
        return abs(self.home_goals - self.away_goals)

    @property
    def winner_slug(self) -> str | None:
        """Slug of the winning club, or ``None`` for a draw/unplayed match."""
        if not self.played or self.home_goals == self.away_goals:
            return None
        return self.home_slug if self.home_goals > self.away_goals else self.away_slug

    @property
    def outcome(self) -> str | None:
        """``"home"``, ``"away"``, ``"draw"`` or ``None``."""
        if not self.played:
            return None
        if self.home_goals > self.away_goals:
            return "home"
        if self.away_goals > self.home_goals:
            return "away"
        return "draw"

    def involves(self, slug: str) -> bool:
        return slug in (self.home_slug, self.away_slug)

    def result_for(self, slug: str) -> str | None:
        """``"W"``, ``"D"`` or ``"L"`` from *slug*'s point of view."""
        if not self.played or not self.involves(slug):
            return None
        if self.home_goals == self.away_goals:
            return "D"
        won = self.winner_slug == slug
        return "W" if won else "L"

    def goals_for(self, slug: str) -> int | None:
        if not self.played or not self.involves(slug):
            return None
        return self.home_goals if slug == self.home_slug else self.away_goals

    def goals_against(self, slug: str) -> int | None:
        if not self.played or not self.involves(slug):
            return None
        return self.away_goals if slug == self.home_slug else self.home_goals

    def opponent_of(self, slug: str) -> str | None:
        if slug == self.home_slug:
            return self.away_slug
        if slug == self.away_slug:
            return self.home_slug
        return None

    @property
    def score(self) -> str:
        if not self.played:
            return "not played"
        return f"{self.home_goals}-{self.away_goals}"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "match_id": self.match_id,
            "competition": self.competition,
            "season": self.season,
            "date": self.date.isoformat() if self.date else None,
            "kickoff": self.kickoff,
            "round": self.round,
            "stage": self.stage,
            "venue": self.venue,
            "home_team": self.home_name,
            "away_team": self.away_name,
            "home_slug": self.home_slug,
            "away_slug": self.away_slug,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "score": self.score,
            "outcome": self.outcome,
            "sources": list(self.sources),
        }
        if self.stats:
            payload["stats"] = self.stats
        return payload


@dataclass
class Player:
    """A FIFA 19 player node."""

    player_id: int
    name: str
    age: int | None = None
    nationality: str | None = None
    overall: int | None = None
    potential: int | None = None
    club: str | None = None
    club_slug: str | None = None
    position: str | None = None
    jersey_number: int | None = None
    height: str | None = None
    weight: str | None = None
    value: str | None = None
    wage: str | None = None
    preferred_foot: str | None = None
    work_rate: str | None = None
    joined: str | None = None
    contract_until: str | None = None
    release_clause: str | None = None
    skills: dict[str, int] = field(default_factory=dict)

    @property
    def is_brazilian(self) -> bool:
        return (self.nationality or "").strip().lower() == "brazil"

    @property
    def position_group(self) -> str:
        """Coarse grouping used by the ``position`` filter (GK/DEF/MID/FWD)."""
        pos = (self.position or "").upper()
        if not pos:
            return "UNKNOWN"
        if pos == "GK":
            return "GK"
        if pos.endswith(("B", "CB")) or pos in {"LB", "RB", "CB", "LCB", "RCB", "LWB", "RWB"}:
            return "DEF"
        if "M" in pos:
            return "MID"
        return "FWD"

    def to_dict(self, *, include_skills: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "player_id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "club_slug": self.club_slug,
            "position": self.position,
            "position_group": self.position_group,
            "jersey_number": self.jersey_number,
            "value": self.value,
            "wage": self.wage,
        }
        if include_skills:
            payload.update(
                {
                    "height": self.height,
                    "weight": self.weight,
                    "preferred_foot": self.preferred_foot,
                    "work_rate": self.work_rate,
                    "joined": self.joined,
                    "contract_until": self.contract_until,
                    "release_clause": self.release_clause,
                    "skills": self.skills,
                }
            )
        return payload
