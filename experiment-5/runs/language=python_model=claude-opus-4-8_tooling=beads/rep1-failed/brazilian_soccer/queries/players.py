"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.queries.players
Purpose   : Player search and ranking over the FIFA dataset.

Functions
  search_players(kg, ...)        -> filter by name substring, nationality, club,
                                    position, minimum overall rating; sortable.
  player_by_name(kg, name)       -> best/exact match for a single player.
  top_players(kg, ...)           -> highest-rated players, optionally restricted
                                    to a nationality (e.g. Brazilian) or club.
  brazilians_by_club(kg)         -> Brazilian players grouped by (Brazilian) club
                                    with average ratings.

Name and nationality matching is accent-insensitive.
================================================================================
"""

from __future__ import annotations

from typing import List, Optional

from ..knowledge_graph import KnowledgeGraph
from ..models import Player
from ..normalize import normalize_team_name, strip_accents


def _fold(text: Optional[str]) -> str:
    return strip_accents(text or "").lower().strip()


def search_players(
    kg: KnowledgeGraph,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: str = "overall",  # "overall" | "potential" | "age" | "name"
    limit: Optional[int] = 50,
) -> List[dict]:
    """Return players matching the filters, sorted (descending for ratings)."""
    name_q = _fold(name)
    nat_q = _fold(nationality)
    club_key = normalize_team_name(club) if club else None
    pos_q = _fold(position)

    # Narrow the candidate set using indexes where possible.
    if nat_q and nat_q in kg.players_by_nationality:
        candidates: List[Player] = kg.players_by_nationality[nat_q]
    elif club_key and club_key in kg.players_by_club:
        candidates = kg.players_by_club[club_key]
    else:
        candidates = kg.players

    results: List[Player] = []
    for p in candidates:
        if name_q and name_q not in p.name_key:
            continue
        if nat_q and nat_q != p.nationality_key:
            continue
        if club_key and club_key != p.club_key:
            continue
        if pos_q and pos_q != _fold(p.position):
            continue
        if min_overall is not None and (p.overall is None or p.overall < min_overall):
            continue
        results.append(p)

    reverse = sort_by in ("overall", "potential")
    if sort_by == "name":
        results.sort(key=lambda p: p.name_key)
    else:
        results.sort(key=lambda p: (getattr(p, sort_by) or 0), reverse=reverse)

    if limit is not None:
        results = results[:limit]
    return [p.to_dict() for p in results]


def player_by_name(kg: KnowledgeGraph, name: str) -> Optional[dict]:
    """Return the highest-rated player whose name contains `name`, or None."""
    matches = search_players(kg, name=name, sort_by="overall", limit=1)
    return matches[0] if matches else None


def top_players(
    kg: KnowledgeGraph,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    limit: int = 10,
) -> List[dict]:
    """Highest-rated players overall, or within a nationality/club."""
    return search_players(
        kg,
        nationality=nationality,
        club=club,
        sort_by="overall",
        limit=limit,
    )


def brazilians_by_club(kg: KnowledgeGraph, limit: int = 20) -> List[dict]:
    """Brazilian players grouped by club, with counts and average rating.

    Sorted by number of Brazilian players desc. Useful for "Brazilian players at
    Brazilian clubs" style questions.
    """
    brazilians = kg.players_by_nationality.get("brazil", [])
    groups: dict[str, List[Player]] = {}
    for p in brazilians:
        if not p.club:
            continue
        groups.setdefault(p.club, []).append(p)

    rows = []
    for club, plist in groups.items():
        rated = [p.overall for p in plist if p.overall is not None]
        rows.append(
            {
                "club": club,
                "count": len(plist),
                "avg_overall": round(sum(rated) / len(rated), 1) if rated else None,
                "top_player": max(
                    plist, key=lambda p: p.overall or 0
                ).name,
            }
        )
    rows.sort(key=lambda r: (-r["count"], -(r["avg_overall"] or 0)))
    return rows[:limit]
