"""FIFA player queries.

Search the FIFA player dump by name, nationality, club, and position; return a
short dict per player rather than a pandas row so consumers don't need pandas
in their dependency tree. All comparisons go through the normalised
``name_norm`` / ``club_norm`` / ``nationality_norm`` columns added by
``data._load_fifa`` so a query for "São Paulo" matches a club tagged
"Sao Paulo FC", and a name search for "neymar" finds "Neymar Jr".
"""

from __future__ import annotations

import unicodedata
from typing import Any

import pandas as pd

from soccer_mcp.data import SoccerData, normalize_team_name


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _player_dict(row: pd.Series) -> dict[str, Any]:
    def get(col: str, default=None):
        if col not in row.index:
            return default
        val = row[col]
        if pd.isna(val):
            return default
        return val

    return {
        "id": int(get("ID")) if get("ID") is not None else None,
        "name": get("Name"),
        "age": int(get("Age")) if get("Age") is not None else None,
        "nationality": get("Nationality"),
        "overall": int(get("Overall")) if get("Overall") is not None else None,
        "potential": int(get("Potential")) if get("Potential") is not None else None,
        "club": get("Club"),
        "position": get("Position"),
        "jersey_number": int(get("Jersey Number")) if get("Jersey Number") is not None else None,
        "height": get("Height"),
        "weight": get("Weight"),
        "preferred_foot": get("Preferred Foot"),
    }


def search_players_by_name(data: SoccerData, name: str, limit: int = 25) -> list[dict]:
    """Substring match on player name (accent-insensitive)."""
    needle = _strip_accents(name).lower().strip()
    if not needle:
        return []
    df = data.fifa
    matches = df[df["name_norm"].str.contains(needle, na=False, regex=False)]
    matches = matches.sort_values("Overall", ascending=False).head(limit)
    return [_player_dict(row) for _, row in matches.iterrows()]


def players_by_nationality(data: SoccerData, nationality: str, limit: int = 25) -> list[dict]:
    """All players from a given country, sorted by overall rating."""
    target = nationality.strip().lower()
    df = data.fifa[data.fifa["nationality_norm"] == target]
    df = df.sort_values("Overall", ascending=False).head(limit)
    return [_player_dict(row) for _, row in df.iterrows()]


def players_by_club(
    data: SoccerData,
    club: str,
    position: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Players at a club, optionally filtered to a single position."""
    club_norm = normalize_team_name(club)
    df = data.fifa[data.fifa["club_norm"].str.contains(club_norm, na=False, regex=False)]
    if position:
        df = df[df["Position"].fillna("").str.upper() == position.upper()]
    df = df.sort_values("Overall", ascending=False).head(limit)
    return [_player_dict(row) for _, row in df.iterrows()]


def top_players(
    data: SoccerData,
    nationality: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Highest-rated players in scope; defaults to global top-N."""
    df = data.fifa
    if nationality:
        df = df[df["nationality_norm"] == nationality.strip().lower()]
    if position:
        df = df[df["Position"].fillna("").str.upper() == position.upper()]
    df = df.sort_values("Overall", ascending=False).head(limit)
    return [_player_dict(row) for _, row in df.iterrows()]


def brazilian_players_by_club_summary(data: SoccerData, limit: int = 20) -> list[dict]:
    """Per-club counts and avg rating among Brazilian players."""
    df = data.fifa[data.fifa["nationality_norm"] == "brazil"]
    grouped = df.groupby("Club").agg(
        players=("Name", "count"),
        avg_rating=("Overall", "mean"),
    )
    grouped = grouped.sort_values("players", ascending=False).head(limit)
    return [
        {"club": club, "players": int(row["players"]), "avg_rating": round(float(row["avg_rating"]), 1)}
        for club, row in grouped.iterrows()
    ]
