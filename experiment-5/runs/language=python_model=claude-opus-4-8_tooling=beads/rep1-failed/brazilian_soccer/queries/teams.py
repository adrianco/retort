"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.queries.teams
Purpose   : Team-centric statistics derived from match results.

Functions
  team_record(kg, team, ...)     -> wins/draws/losses, goals for/against, win
                                    rate, optionally filtered to home or away
                                    games, a competition and/or a season.
  team_competitions(kg, team)    -> which competitions a team appears in + counts.

A "record" counts only matches that have a known score.
================================================================================
"""

from __future__ import annotations

from typing import Optional

from ..knowledge_graph import KnowledgeGraph
from ..models import Match
from ..normalize import normalize_team_name


def _empty_record() -> dict:
    return {
        "matches": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
    }


def team_record(
    kg: KnowledgeGraph,
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",  # "all" | "home" | "away"
) -> dict:
    """Compute a team's W/D/L and goal record under the given filters.

    `venue` restricts to home games, away games, or both.
    """
    key = normalize_team_name(team)
    rec = _empty_record()

    for m in kg.matches_by_team.get(key, []):
        if season is not None and m.season != season:
            continue
        if competition and m.competition != competition:
            continue
        if not m.has_score:
            continue

        is_home = m.home_key == key
        if venue == "home" and not is_home:
            continue
        if venue == "away" and is_home:
            continue

        gf = m.home_goal if is_home else m.away_goal
        ga = m.away_goal if is_home else m.home_goal

        rec["matches"] += 1
        rec["goals_for"] += gf
        rec["goals_against"] += ga
        if gf > ga:
            rec["wins"] += 1
        elif gf < ga:
            rec["losses"] += 1
        else:
            rec["draws"] += 1

    rec["goal_difference"] = rec["goals_for"] - rec["goals_against"]
    rec["points"] = rec["wins"] * 3 + rec["draws"]
    rec["win_rate"] = round(rec["wins"] / rec["matches"], 4) if rec["matches"] else 0.0
    rec["team"] = kg.display_name(key)
    rec["season"] = season
    rec["competition"] = competition
    rec["venue"] = venue
    return rec


def team_competitions(kg: KnowledgeGraph, team: str) -> dict:
    """Return the competitions a team has played in, with match counts."""
    key = normalize_team_name(team)
    counts: dict[str, int] = {}
    seasons: set[int] = set()
    for m in kg.matches_by_team.get(key, []):
        counts[m.competition] = counts.get(m.competition, 0) + 1
        if m.season is not None:
            seasons.add(m.season)
    return {
        "team": kg.display_name(key),
        "competitions": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "seasons": sorted(seasons),
        "total_matches": sum(counts.values()),
    }
