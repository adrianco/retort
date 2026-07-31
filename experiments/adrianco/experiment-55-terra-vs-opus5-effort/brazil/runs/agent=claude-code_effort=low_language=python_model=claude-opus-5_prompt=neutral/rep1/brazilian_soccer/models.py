"""
Context
=======
Module: brazilian_soccer.models

The two node types of the knowledge graph.

`Match` is the union of the columns available across the five match datasets;
fields absent from a given source stay None (e.g. only BR-Football-Dataset.csv
carries shots/corners, only novo_campeonato_brasileiro.csv carries the arena).
Every Match keeps both the raw spellings (for display) and the normalised
canonical keys (for joining across files) -- see names.py.

`Player` wraps the FIFA row, keeping only the columns the query layer needs plus
a `skills` dict for the long tail of attribute ratings.

Both types are frozen dataclasses: the graph is built once and read many times,
so immutability makes the indexes safe to share.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

# Canonical competition labels used everywhere in the API.
BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

COMPETITIONS = [
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    LIBERTADORES,
]

# Accepted user spellings -> canonical competition label.
COMPETITION_ALIASES = {
    "brasileirao": BRASILEIRAO_A,
    "brasileirão": BRASILEIRAO_A,
    "serie a": BRASILEIRAO_A,
    "série a": BRASILEIRAO_A,
    "brasileirao serie a": BRASILEIRAO_A,
    "campeonato brasileiro": BRASILEIRAO_A,
    "serie b": BRASILEIRAO_B,
    "série b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "série c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "cup": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
}


def resolve_competition(raw: str | None) -> str | None:
    """Map a loose user string onto a canonical competition label."""
    if not raw:
        return None
    key = " ".join(raw.strip().lower().split())
    if key in COMPETITION_ALIASES:
        return COMPETITION_ALIASES[key]
    for canon in COMPETITIONS:
        if canon.lower() == key:
            return canon
    return None


@dataclass(frozen=True)
class Match:
    """One match, normalised across all five match datasets."""

    competition: str
    season: int
    match_date: date | None
    home_team: str          # canonical key, e.g. "sao paulo"
    away_team: str
    home_display: str       # prettiest raw spelling, e.g. "São Paulo"
    away_display: str
    home_goals: int
    away_goals: int
    source: str
    round: str | None = None
    stage: str | None = None
    arena: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    kickoff: str | None = None
    stats: dict[str, float] = field(default_factory=dict, compare=False)

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def goal_difference(self) -> int:
        return abs(self.home_goals - self.away_goals)

    @property
    def winner(self) -> str | None:
        """Canonical key of the winner, or None for a draw."""
        if self.home_goals > self.away_goals:
            return self.home_team
        if self.away_goals > self.home_goals:
            return self.away_team
        return None

    @property
    def is_draw(self) -> bool:
        return self.home_goals == self.away_goals

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home_team, self.away_team)

    def opponent_of(self, team_key: str) -> str | None:
        if team_key == self.home_team:
            return self.away_team
        if team_key == self.away_team:
            return self.home_team
        return None

    @property
    def dedup_key(self) -> tuple:
        """Identity used to merge the same fixture appearing in two datasets.

        Deliberately *excludes* the date: the same fixture is dated one day
        apart in different files (kick-off recorded in different time zones),
        so the date is compared with a tolerance in loader.deduplicate()
        instead.  Within one competition and season a given (home, away)
        ordered pair normally occurs once -- league seasons are double
        round-robin, and cup ties play one leg at each venue.
        """
        return (self.competition, self.season, self.home_team, self.away_team)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "competition": self.competition,
            "season": self.season,
            "date": self.match_date.isoformat() if self.match_date else None,
            "home_team": self.home_display,
            "away_team": self.away_display,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "score": f"{self.home_goals}-{self.away_goals}",
            "source": self.source,
        }
        for key in ("round", "stage", "arena", "kickoff", "home_state", "away_state"):
            value = getattr(self, key)
            if value:
                data[key] = value
        if self.stats:
            data["stats"] = self.stats
        return data


@dataclass(frozen=True)
class Player:
    """One row of fifa_data.csv."""

    player_id: int
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str                # raw club spelling from the dataset
    club_key: str            # normalised club key, "" when the player is a free agent
    position: str | None
    jersey_number: str | None
    height: str | None
    weight: str | None
    value: str | None
    wage: str | None
    preferred_foot: str | None
    skills: dict[str, int] = field(default_factory=dict, compare=False)

    @property
    def is_brazilian(self) -> bool:
        return self.nationality.strip().lower() == "brazil"

    def to_dict(self, include_skills: bool = False) -> dict[str, Any]:
        data = {
            "id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club or None,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "value": self.value,
            "wage": self.wage,
            "preferred_foot": self.preferred_foot,
        }
        if include_skills and self.skills:
            data["skills"] = self.skills
        return data
