"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.queries.stats
Purpose   : Aggregate statistical analysis across the match datasets.

Functions
  competition_summary(kg, competition, season) -> goals/match, home win rate,
                                                   draw rate, totals.
  biggest_wins(kg, competition, season, limit)  -> matches with the largest
                                                   goal margin.
  best_records(kg, competition, season, venue)  -> teams ranked by win rate
                                                   (min games threshold).
================================================================================
"""

from __future__ import annotations

from typing import List, Optional

from ..knowledge_graph import KnowledgeGraph
from ..models import Match
from .teams import team_record


def _filter(kg: KnowledgeGraph, competition: Optional[str], season: Optional[int]):
    if competition:
        pool = kg.matches_by_competition.get(competition, [])
    elif season is not None:
        pool = kg.matches_by_season.get(season, [])
    else:
        pool = kg.matches
    for m in pool:
        if competition and m.competition != competition:
            continue
        if season is not None and m.season != season:
            continue
        yield m


def competition_summary(
    kg: KnowledgeGraph,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """Average goals per match, home/away/draw rates and totals."""
    played = 0
    total_goals = 0
    home_wins = away_wins = draws = 0
    for m in _filter(kg, competition, season):
        if not m.has_score:
            continue
        played += 1
        total_goals += m.total_goals
        w = m.winner
        if w == "home":
            home_wins += 1
        elif w == "away":
            away_wins += 1
        else:
            draws += 1

    return {
        "competition": competition or "all",
        "season": season,
        "matches": played,
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / played, 2) if played else 0.0,
        "home_win_rate": round(home_wins / played, 4) if played else 0.0,
        "away_win_rate": round(away_wins / played, 4) if played else 0.0,
        "draw_rate": round(draws / played, 4) if played else 0.0,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
    }


def biggest_wins(
    kg: KnowledgeGraph,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> List[dict]:
    """Matches sorted by largest goal margin (descending)."""
    scored: List[Match] = [
        m for m in _filter(kg, competition, season) if m.has_score
    ]
    scored.sort(
        key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
        reverse=True,
    )
    out = []
    for m in scored[:limit]:
        d = m.to_dict()
        d["margin"] = abs(m.home_goal - m.away_goal)
        out.append(d)
    return out


def best_records(
    kg: KnowledgeGraph,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: str = "all",
    min_matches: int = 5,
    limit: int = 10,
) -> List[dict]:
    """Rank teams by win rate (with a minimum games threshold).

    Considers every team that appears in the filtered match pool.
    """
    team_keys = set()
    for m in _filter(kg, competition, season):
        team_keys.add(m.home_key)
        team_keys.add(m.away_key)

    rows = []
    for key in team_keys:
        rec = team_record(
            kg,
            kg.display_name(key),
            season=season,
            competition=competition,
            venue=venue,
        )
        if rec["matches"] >= min_matches:
            rows.append(rec)

    rows.sort(key=lambda r: (r["win_rate"], r["goal_difference"]), reverse=True)
    return rows[:limit]
