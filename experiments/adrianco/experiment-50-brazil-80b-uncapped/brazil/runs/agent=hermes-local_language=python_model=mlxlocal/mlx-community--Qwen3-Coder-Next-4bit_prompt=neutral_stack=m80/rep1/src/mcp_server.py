#!/usr/bin/env python3
"""MCP Server implementation for Brazilian Soccer data.

This module provides a Model Context Protocol (MCP) server for querying
Brazilian soccer data including matches, teams, players, competitions,
and statistics.
"""

import asyncio
import json
from typing import Optional
from mcp.server import FastMCP
from mcp.types import Tool

from src.models import Match, Player, TeamStats, TeamComparison, CompetitionStandings, BigWin, QueryResponse
from src.data_utils import DataUtils, DataLoader, QueryEngine


# Initialize FastMCP server
mcp = FastMCP(
    name="brazilian-soccer-mcp-server",
    instructions="A Model Context Protocol server for Brazilian soccer data. Provides tools to query matches, teams, players, competitions, and statistics from pre-downloaded Kaggle datasets.",
    host="127.0.0.1",
    port=8000,
)


def get_query_engine() -> QueryEngine:
    """Get or create a QueryEngine instance."""
    return QueryEngine()


# =============================================================================
# Match Query Tools
# =============================================================================

@mcp.tool()
def find_matches_by_teams(
    team1: str,
    team2: Optional[str] = None,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    limit: int = 100
) -> str:
    """Find matches by one or two teams, optionally filtered by season and competition.
    
    Args:
        team1: First team name to search for
        team2: Optional second team name (for head-to-head searches)
        season: Optional season year to filter by
        competition: Optional competition name (Brasileirão, Copa do Brasil, Libertadores)
        limit: Maximum number of results to return
    
    Returns:
        JSON string with match results
    """
    engine = get_query_engine()
    
    if team2:
        matches = engine.find_matches_by_teams(team1, team2, limit)
    else:
        matches = engine.find_matches_by_team(team1, season, competition)
    
    # Limit by season if specified (additional filtering)
    if season:
        matches = [m for m in matches if m.season == season]
    if competition:
        matches = [m for m in matches if m.competition.lower() == competition.lower()]
    
    matches = matches[:limit]
    
    results = {
        "query_type": "match_search",
        "success": True,
        "message": f"Found {len(matches)} matches",
        "data": [m.to_dict() for m in matches],
        "count": len(matches),
        "metadata": {
            "team1": team1,
            "team2": team2,
            "season": season,
            "competition": competition,
        },
    }
    return json.dumps(results, indent=2)


@mcp.tool()
def get_match_by_id(match_id: int) -> str:
    """Get a specific match by its ID.
    
    Args:
        match_id: The unique identifier for the match
    
    Returns:
        JSON string with match details
    """
    engine = get_query_engine()
    matches = engine.get_all_matches()
    
    for match in matches:
        if match.id == match_id:
            return json.dumps({
                "query_type": "match_by_id",
                "success": True,
                "message": f"Found match {match_id}",
                "data": match.to_dict(),
                "count": 1,
            }, indent=2)
    
    return json.dumps({
        "query_type": "match_by_id",
        "success": False,
        "message": f"Match {match_id} not found",
        "data": None,
        "count": 0,
    }, indent=2)


# =============================================================================
# Team Query Tools
# =============================================================================

@mcp.tool()
def get_team_stats(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None
) -> str:
    """Get statistics for a team, optionally filtered by season and competition.
    
    Args:
        team: Team name to get statistics for
        season: Optional season year
        competition: Optional competition name
    
    Returns:
        JSON string with team statistics
    """
    engine = get_query_engine()
    stats = engine.get_team_stats(team, season, competition)
    
    return json.dumps(stats.to_dict(), indent=2)


@mcp.tool()
def get_team_comparison(team1: str, team2: str) -> str:
    """Get head-to-head comparison between two teams.
    
    Args:
        team1: First team name
        team2: Second team name
    
    Returns:
        JSON string with head-to-head comparison
    """
    engine = get_query_engine()
    comparison = engine.get_team_comparison(team1, team2)
    
    return json.dumps(comparison.to_dict(), indent=2)


# =============================================================================
# Player Query Tools
# =============================================================================

@mcp.tool()
def search_players(
    name: Optional[str] = None,
    club: Optional[str] = None,
    nationality: Optional[str] = None,
    position: Optional[str] = None,
    limit: int = 100
) -> str:
    """Search for players by various criteria.
    
    Args:
        name: Player name to search for
        club: Filter by club name
        nationality: Filter by nationality
        position: Filter by position
        limit: Maximum number of results
    
    Returns:
        JSON string with player search results
    """
    engine = get_query_engine()
    
    if name:
        players = engine.get_player_by_name(name)
    elif club:
        players = engine.get_players_by_club(club)
    else:
        players = engine.loader.players
    
    if nationality:
        players = [p for p in players if p.nationality.lower() == nationality.lower()]
    
    if position:
        players = [p for p in players if position.lower() in p.position.lower()]
    
    players = players[:limit]
    
    results = {
        "query_type": "player_search",
        "success": True,
        "message": f"Found {len(players)} players",
        "data": [p.to_dict() for p in players],
        "count": len(players),
        "metadata": {
            "name": name,
            "club": club,
            "nationality": nationality,
            "position": position,
        },
    }
    return json.dumps(results, indent=2)


@mcp.tool()
def get_top_brazilian_players(limit: int = 10) -> str:
    """Get the top rated Brazilian players.
    
    Args:
        limit: Maximum number of players to return
    
    Returns:
        JSON string with top Brazilian players
    """
    engine = get_query_engine()
    players = engine.get_top_brazilian_players(limit)
    
    return json.dumps({
        "query_type": "brazilian_players",
        "success": True,
        "message": f"Found {len(players)} top Brazilian players",
        "data": [p.to_dict() for p in players],
        "count": len(players),
    }, indent=2)


# =============================================================================
# Competition Query Tools
# =============================================================================

@mcp.tool()
def get_competition_standings(competition: str, season: int) -> str:
    """Get competition standings for a specific season.
    
    Args:
        competition: Competition name (e.g., Brasileirão, Copa Libertadores)
        season: Season year
    
    Returns:
        JSON string with competition standings
    """
    engine = get_query_engine()
    standings = engine.get_competition_standings(competition, season)
    
    return json.dumps({
        "query_type": "competition_standings",
        "success": True,
        "message": f"Found {len(standings)} teams",
        "data": [s.to_dict() for s in standings],
        "count": len(standings),
    }, indent=2)


# =============================================================================
# Statistical Analysis Tools
# =============================================================================

@mcp.tool()
def get_big_wins(competition: Optional[str] = None, limit: int = 10) -> str:
    """Get biggest wins in matches (by goal difference).
    
    Args:
        competition: Optional competition filter
        limit: Maximum number of wins to return
    
    Returns:
        JSON string with big wins
    """
    engine = get_query_engine()
    wins = engine.get_big_wins(competition, limit)
    
    return json.dumps({
        "query_type": "big_wins",
        "success": True,
        "message": f"Found {len(wins)} big wins",
        "data": [w.to_dict() for w in wins],
        "count": len(wins),
    }, indent=2)


@mcp.tool()
def get_average_goals_per_match(competition: Optional[str] = None) -> str:
    """Calculate average goals per match.
    
    Args:
        competition: Optional competition filter
    
    Returns:
        JSON string with average goals
    """
    engine = get_query_engine()
    avg = engine.get_average_goals_per_match(competition)
    
    return json.dumps({
        "query_type": "average_goals",
        "success": True,
        "message": f"Average goals per match: {avg}",
        "data": {"average": avg},
        "count": 1,
    }, indent=2)


@mcp.tool()
def get_home_win_rate() -> str:
    """Calculate home win rate across all matches.
    
    Returns:
        JSON string with home win rate
    """
    engine = get_query_engine()
    rate = engine.get_home_win_rate()
    
    return json.dumps({
        "query_type": "home_win_rate",
        "success": True,
        "message": f"Home win rate: {rate}%",
        "data": {"rate": rate},
        "count": 1,
    }, indent=2)


# =============================================================================
# Utility Functions
# =============================================================================

@mcp.tool()
def list_competitions() -> str:
    """List all competitions in the dataset.
    
    Returns:
        JSON string with list of competitions
    """
    engine = get_query_engine()
    matches = engine.get_all_matches()
    
    competitions = set(m.competition for m in matches if m.competition)
    
    return json.dumps({
        "query_type": "list_competitions",
        "success": True,
        "message": f"Found {len(competitions)} competitions",
        "data": sorted(list(competitions)),
        "count": len(competitions),
    }, indent=2)


@mcp.tool()
def list_seasons(competition: Optional[str] = None) -> str:
    """List all available seasons in the dataset.
    
    Args:
        competition: Optional competition filter
    
    Returns:
        JSON string with list of seasons
    """
    engine = get_query_engine()
    matches = engine.get_all_matches()
    
    if competition:
        matches = [m for m in matches if m.competition.lower() == competition.lower()]
    
    seasons = set(m.season for m in matches if m.season)
    
    return json.dumps({
        "query_type": "list_seasons",
        "success": True,
        "message": f"Found {len(seasons)} seasons",
        "data": sorted(list(seasons)),
        "count": len(seasons),
    }, indent=2)


# =============================================================================
# Server Entry Point
# =============================================================================

def main():
    """Run the MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the Brazilian Soccer MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run using stdio transport")
    parser.add_argument("--mount-path", type=str, default="/", help="Mount path for SSE/streamable HTTP")
    
    args = parser.parse_args()
    
    if args.stdio:
        # Run with stdio transport
        asyncio.run(mcp.run_stdio_async())
    else:
        # Run with SSE transport
        mount_path = args.mount_path
        print(f"Starting MCP server on http://127.0.0.1:8000{mount_path}")
        print("Tools available:")
        for tool in mcp.list_tools():
            print(f"  - {tool.name}: {tool.description}")
        asyncio.run(mcp.run_sse_async(mount_path=mount_path))


if __name__ == "__main__":
    main()
