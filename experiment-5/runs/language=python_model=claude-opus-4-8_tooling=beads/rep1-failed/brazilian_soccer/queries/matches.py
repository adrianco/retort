"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.queries.matches
Purpose   : Match-centric queries.

Functions
  find_matches(kg, ...)      -> filter matches by team, opponent, competition,
                                season, date range, and home/away role.
  head_to_head(kg, a, b)     -> aggregate W/D/L and goals between two teams.
  last_match(kg, a, b)       -> most recent match between two teams.

All functions return JSON-serialisable structures (lists of match dicts and/or
summary dicts) and accept fuzzy team names (normalized internally).
================================================================================
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from ..knowledge_graph import KnowledgeGraph
from ..models import Match
from ..normalize import normalize_team_name, parse_date


def _sort_key(m: Match):
    # Sort by date when available; matches without dates sort last (oldest).
    return (m.match_date or date.min, m.season or 0)


def find_matches(
    kg: KnowledgeGraph,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: Optional[int] = None,
) -> List[dict]:
    """Return matches matching the given filters, newest first.

    * team / opponent are fuzzy-matched (state suffixes etc. ignored).
    * home_only / away_only constrain the role of `team`.
    """
    team_key = normalize_team_name(team) if team else None
    opp_key = normalize_team_name(opponent) if opponent else None
    df = parse_date(date_from)
    dt = parse_date(date_to)

    # Start from the smallest candidate set we can.
    if team_key:
        candidates = kg.matches_by_team.get(team_key, [])
    elif competition:
        candidates = kg.matches_by_competition.get(competition, [])
    elif season is not None:
        candidates = kg.matches_by_season.get(season, [])
    else:
        candidates = kg.matches

    results: List[Match] = []
    for m in candidates:
        if team_key:
            if home_only and m.home_key != team_key:
                continue
            if away_only and m.away_key != team_key:
                continue
            if not (home_only or away_only) and not m.involves(team_key):
                continue
        if opp_key and not m.involves(opp_key):
            continue
        if competition and m.competition != competition:
            continue
        if season is not None and m.season != season:
            continue
        if df and (m.match_date is None or m.match_date < df):
            continue
        if dt and (m.match_date is None or m.match_date > dt):
            continue
        results.append(m)

    results.sort(key=_sort_key, reverse=True)
    if limit is not None:
        results = results[:limit]
    return [m.to_dict() for m in results]


def head_to_head(
    kg: KnowledgeGraph,
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
) -> dict:
    """Aggregate the rivalry between two teams.

    Returns total matches, each team's wins, draws, and goals, plus the list of
    matches (newest first).
    """
    a_key = normalize_team_name(team_a)
    b_key = normalize_team_name(team_b)

    a_wins = b_wins = draws = 0
    a_goals = b_goals = 0
    matches: List[Match] = []

    for m in kg.matches_by_team.get(a_key, []):
        if not m.involves(b_key):
            continue
        if competition and m.competition != competition:
            continue
        matches.append(m)
        if not m.has_score:
            continue
        # Determine each team's goals in this match.
        if m.home_key == a_key:
            ga, gb = m.home_goal, m.away_goal
        else:
            ga, gb = m.away_goal, m.home_goal
        a_goals += ga
        b_goals += gb
        if ga > gb:
            a_wins += 1
        elif gb > ga:
            b_wins += 1
        else:
            draws += 1

    matches.sort(key=_sort_key, reverse=True)
    return {
        "team_a": kg.display_name(a_key),
        "team_b": kg.display_name(b_key),
        "total_matches": len(matches),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "matches": [m.to_dict() for m in matches],
    }


def last_match(kg: KnowledgeGraph, team_a: str, team_b: str) -> Optional[dict]:
    """Most recent match between two teams, or None if they never met."""
    h2h = head_to_head(kg, team_a, team_b)
    matches = h2h["matches"]
    return matches[0] if matches else None
