"""
==============================================================================
Module: brazilian_soccer.server
==============================================================================
CONTEXT
-------
The MCP (Model Context Protocol) server. It exposes the pure query functions in
``brazilian_soccer.queries`` as MCP *tools* so an LLM client (Claude Desktop,
etc.) can answer natural-language questions about Brazilian soccer by calling
them.

We use the official ``mcp`` Python SDK's ``FastMCP`` helper, which turns plain
Python functions (with type hints + docstrings) into well-described MCP tools
and serves them over stdio.

The knowledge graph is loaded once at process start (see
``knowledge_graph.get_graph``) and shared by every tool call, keeping latency
far inside the spec budget (< 2s simple / < 5s aggregate).

TOOLS EXPOSED
-------------
  find_matches, head_to_head, last_meeting,            (match queries)
  team_record, compare_teams,                          (team queries)
  search_players, top_players, brazilian_players_by_club,  (player queries)
  standings, list_competitions,                        (competition queries)
  competition_stats, biggest_wins,                     (statistics)
  best_home_record, best_away_record,
  dataset_summary                                      (introspection)

Run with:  python -m brazilian_soccer.server      (stdio transport)
==============================================================================
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import queries as q
from .knowledge_graph import get_graph

mcp = FastMCP("brazilian-soccer")


# --------------------------------------------------------------------------- #
# 1. MATCH QUERIES
# --------------------------------------------------------------------------- #
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: int = 50,
) -> dict:
    """Find matches filtered by team, opponent, competition and/or season.

    Args:
        team: Team name (any surface form, e.g. "Flamengo" or "Flamengo-RJ").
        opponent: Restrict to matches against this opponent.
        competition: "Brasileirão", "Copa do Brasil" or "Libertadores".
        season: Year of the season (e.g. 2019).
        home_only: Only matches where ``team`` played at home.
        away_only: Only matches where ``team`` played away.
        limit: Maximum number of matches to return.
    """
    return q.find_matches(
        get_graph(), team, opponent, competition, season,
        home_only, away_only, limit,
    )


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 50,
) -> dict:
    """Head-to-head record (wins/draws/goals) and match list between two teams."""
    return q.head_to_head(get_graph(), team_a, team_b, competition, season, limit)


@mcp.tool()
def last_meeting(team_a: str, team_b: str) -> dict:
    """Most recent match played between two teams (e.g. 'when did X last play Y')."""
    return q.last_meeting(get_graph(), team_a, team_b)


# --------------------------------------------------------------------------- #
# 2. TEAM QUERIES
# --------------------------------------------------------------------------- #
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> dict:
    """Win/loss/draw record and goals for a team.

    Args:
        team: Team name.
        season: Optional season year filter.
        competition: Optional competition filter.
        venue: 'all', 'home' or 'away'.
    """
    return q.team_record(get_graph(), team, season, competition, venue)


@mcp.tool()
def compare_teams(
    team_a: str,
    team_b: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
) -> dict:
    """Compare two teams' overall records plus their head-to-head."""
    return q.compare_teams(get_graph(), team_a, team_b, season, competition)


# --------------------------------------------------------------------------- #
# 3. PLAYER QUERIES
# --------------------------------------------------------------------------- #
@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 25,
) -> dict:
    """Search FIFA players by name, nationality, club, position and/or rating."""
    return q.search_players(
        get_graph(), name, nationality, club, position, min_overall, limit
    )


@mcp.tool()
def top_players(
    nationality: Optional[str] = "Brazil",
    club: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Highest-rated players for a nationality (default Brazil) and/or club."""
    return q.top_players(get_graph(), nationality, club, limit)


@mcp.tool()
def brazilian_players_by_club(limit: int = 15) -> dict:
    """Brazilian players grouped by club, with per-club average rating."""
    return q.brazilian_players_by_club(get_graph(), limit)


# --------------------------------------------------------------------------- #
# 4. COMPETITION QUERIES
# --------------------------------------------------------------------------- #
@mcp.tool()
def standings(competition: str, season: int, limit: Optional[int] = None) -> dict:
    """Compute a league table (3pts/win, 1/draw) from match results.

    Args:
        competition: e.g. "Brasileirão".
        season: Season year (e.g. 2019).
        limit: Optionally return only the top N rows.
    """
    return q.standings(get_graph(), competition, season, limit)


@mcp.tool()
def list_competitions() -> dict:
    """List available competitions and the seasons present for each."""
    return q.list_competitions(get_graph())


# --------------------------------------------------------------------------- #
# 5. STATISTICAL ANALYSIS
# --------------------------------------------------------------------------- #
@mcp.tool()
def competition_stats(
    competition: Optional[str] = None, season: Optional[int] = None
) -> dict:
    """Average goals per match, home/away win rate and draw rate for a filter."""
    return q.competition_stats(get_graph(), competition, season)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """Matches with the largest goal margin (optionally filtered)."""
    return q.biggest_wins(get_graph(), competition, season, limit)


@mcp.tool()
def best_home_record(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    limit: int = 10,
) -> dict:
    """Teams ranked by home win-rate (optionally filtered by competition/season)."""
    return q.best_home_record(get_graph(), competition, season, min_matches, limit)


@mcp.tool()
def best_away_record(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    limit: int = 10,
) -> dict:
    """Teams ranked by away win-rate (optionally filtered by competition/season)."""
    return q.best_away_record(get_graph(), competition, season, min_matches, limit)


@mcp.tool()
def dataset_summary() -> dict:
    """Summary of loaded data: match/player counts, competitions, seasons."""
    return get_graph().summary()


def main() -> None:
    """Entry point: load the graph then serve over stdio."""
    get_graph()  # warm the cache before accepting requests
    mcp.run()


if __name__ == "__main__":
    main()
