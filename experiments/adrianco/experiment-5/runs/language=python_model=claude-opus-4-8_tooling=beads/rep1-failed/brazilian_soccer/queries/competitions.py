"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.queries.competitions
Purpose   : Competition-level views, primarily league standings calculated from
            match results (3 points for a win, 1 for a draw).

Functions
  standings(kg, competition, season)  -> sorted league table with points, W/D/L,
                                          goals for/against, goal difference.
  champion(kg, competition, season)   -> the top team of the computed standings.
  relegated(kg, season, count)        -> bottom `count` teams of a Brasileirao
                                          season standings.

Standings are most meaningful for round-robin leagues (Brasileirao); they can be
computed for any competition but a knockout cup table is just a points summary.
================================================================================
"""

from __future__ import annotations

from typing import List, Optional

from ..knowledge_graph import KnowledgeGraph


def standings(
    kg: KnowledgeGraph,
    competition: str = "Brasileirao",
    season: Optional[int] = None,
) -> List[dict]:
    """Compute a league table for a competition/season from match results."""
    table: dict[str, dict] = {}

    for m in kg.matches_by_competition.get(competition, []):
        if season is not None and m.season != season:
            continue
        if not m.has_score:
            continue

        for key, gf, ga in (
            (m.home_key, m.home_goal, m.away_goal),
            (m.away_key, m.away_goal, m.home_goal),
        ):
            row = table.setdefault(
                key,
                {
                    "team": kg.display_name(key),
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0,
                },
            )
            row["played"] += 1
            row["goals_for"] += gf
            row["goals_against"] += ga
            if gf > ga:
                row["wins"] += 1
                row["points"] += 3
            elif gf < ga:
                row["losses"] += 1
            else:
                row["draws"] += 1
                row["points"] += 1

    rows = list(table.values())
    for r in rows:
        r["goal_difference"] = r["goals_for"] - r["goals_against"]

    rows.sort(
        key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]),
        reverse=True,
    )
    for i, r in enumerate(rows, start=1):
        r["position"] = i
    return rows


def champion(
    kg: KnowledgeGraph,
    competition: str = "Brasileirao",
    season: Optional[int] = None,
) -> Optional[dict]:
    """Return the top team of the computed standings, or None if no data."""
    table = standings(kg, competition, season)
    return table[0] if table else None


def relegated(
    kg: KnowledgeGraph,
    season: int,
    competition: str = "Brasileirao",
    count: int = 4,
) -> List[dict]:
    """Return the bottom `count` teams of a season's standings."""
    table = standings(kg, competition, season)
    return table[-count:] if table else []
