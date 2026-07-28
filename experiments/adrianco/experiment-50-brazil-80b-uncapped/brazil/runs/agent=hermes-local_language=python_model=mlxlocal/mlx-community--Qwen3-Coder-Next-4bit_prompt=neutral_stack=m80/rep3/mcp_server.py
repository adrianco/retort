"""
Brazilian Soccer MCP Server
A Model Context Protocol server for Brazilian soccer data
"""

import asyncio
import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, ImageContent, Tool, Prompt
from mcp.shared.exceptions import McpError
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions

# Local imports
from data_loader import SoccerDataLoader
from query_engine import (
    SoccerQueryEngine,
    TeamStats,
    MatchResult,
    PlayerInfo,
    CompetitionStandings,
    BigWin,
)

# Get data directory path
DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Initialize components
data_loader = SoccerDataLoader(DATA_DIR)
query_engine = SoccerQueryEngine(data_loader)

# Create MCP server
server = Server("brazilian-soccer-server")


def format_matches_response(matches: List[Dict], title: str = "Matches") -> str:
    """Format matches into a readable response"""
    if not matches:
        return f"No matches found for: {title}"
    
    lines = [f"{title} ({len(matches)} matches):", ""]
    for match in matches[:20]:  # Limit to 20 matches
        date = match.get('datetime', '')
        home = match.get('home_team', '')
        away = match.get('away_team', '')
        home_goal = match.get('home_goal', 0)
        away_goal = match.get('away_goal', 0)
        competition = match.get('competition', '')
        round_num = match.get('round', '')
        
        round_info = f" (Round {round_num})" if round_num else ""
        lines.append(f"- {date}: {home} {home_goal}-{away_goal} {away} [{competition}{round_info}]")
    
    if len(matches) > 20:
        lines.append(f"")
        lines.append(f"... and {len(matches) - 20} more matches")
    
    return "\n".join(lines)


def format_team_stats_response(stats: TeamStats, team: str) -> str:
    """Format team statistics into a readable response"""
    return f"""{team} Statistics:
- Matches: {stats.matches}
- Wins: {stats.wins}, Draws: {stats.draws}, Losses: {stats.losses}
- Goals For: {stats.goals_for}, Goals Against: {stats.goals_against}
- Goal Difference: {stats.goal_difference}
- Points: {stats.points}
- Win Rate: {stats.win_rate}%"""


def format_head_to_head_response(h2h: Dict, team1: str, team2: str) -> str:
    """Format head-to-head record into a readable response"""
    return f"""{team1} vs {team2} Head-to-Head:
- {team1} Wins: {h2h['team1_wins']}
- {team2} Wins: {h2h['team2_wins']}
- Draws: {h2h['draws']}
- Total Matches: {h2h['total_matches']}
"""


def format_player_response(player: PlayerInfo) -> str:
    """Format player information into a readable response"""
    return f"""{player.name}:
- ID: {player.id}
- Age: {player.age}
- Nationality: {player.nationality}
- Overall Rating: {player.overall}
- Potential: {player.potential}
- Club: {player.club}
- Position: {player.position}
- Jersey Number: {player.jersey_number}
- Height: {player.height}
- Weight: {player.weight}"""


def format_players_response(players: List[PlayerInfo], title: str) -> str:
    """Format list of players into a readable response"""
    if not players:
        return f"No players found for: {title}"
    
    lines = [f"{title} ({len(players)} players):", ""]
    for player in players[:20]:  # Limit to 20 players
        lines.append(f"- {player.name} ({player.position}) - {player.club} (Rating: {player.overall})")
    
    if len(players) > 20:
        lines.append(f"")
        lines.append(f"... and {len(players) - 20} more players")
    
    return "\n".join(lines)


def format_standings_response(standings: List[CompetitionStandings], competition: str, season: int) -> str:
    """Format competition standings into a readable response"""
    if not standings:
        return f"No standings found for {competition} {season}"
    
    lines = [f"{competition} {season} Standings:", ""]
    for standing in standings[:20]:  # Show top 20
        pos = standing.position
        team = standing.team
        pts = standing.points
        w = standing.wins
        d = standing.draws
        l = standing.losses
        gf = standing.goals_for
        ga = standing.goals_against
        gd = standing.goal_difference
        
        lines.append(f"{pos}. {team} - {pts} pts ({w}W, {d}D, {l}L) GF:{gf} GA:{ga} GD:{gd}")
    
    return "\n".join(lines)


def format_big_wins_response(wins: List[BigWin], limit: int) -> str:
    """Format big wins into a readable response"""
    if not wins:
        return f"No big wins found"
    
    lines = [f"Biggest Victories (Score difference >= 4 goals):", ""]
    for win in wins[:limit]:
        date = win.date
        home = win.home_team
        away = win.away_team
        home_goal = win.home_goal
        away_goal = win.away_goal
        competition = win.competition
        season = win.season
        
        season_info = f" ({season})" if season else ""
        lines.append(f"- {date}: {home} {home_goal}-{away_goal} {away} [{competition}{season_info}]")
    
    return "\n".join(lines)


# ========== Tool Handlers ==========

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools for the MCP server"""
    return [
        Tool(
            name="find_matches_between_teams",
            description="Find all matches between two teams",
            inputSchema={
                "type": "object",
                "properties": {
                    "team1": {"type": "string", "description": "First team name"},
                    "team2": {"type": "string", "description": "Second team name"},
                },
                "required": ["team1", "team2"],
            },
        ),
        Tool(
            name="find_matches_by_team",
            description="Find matches for a specific team",
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name"},
                    "limit": {"type": "integer", "description": "Maximum number of matches to return", "default": 10},
                },
                "required": ["team"],
            },
        ),
        Tool(
            name="find_matches_by_competition",
            description="Find matches by competition type",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string", "description": "Competition name (Brasileirao, Copa do Brasil, Libertadores)"},
                    "season": {"type": "integer", "description": "Season year"},
                    "limit": {"type": "integer", "description": "Maximum number of matches to return", "default": 10},
                },
                "required": ["competition"],
            },
        ),
        Tool(
            name="find_matches_by_date_range",
            description="Find matches within a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "team": {"type": "string", "description": "Optional team filter"},
                },
                "required": ["date_from", "date_to"],
            },
        ),
        Tool(
            name="get_team_statistics",
            description="Get comprehensive statistics for a team",
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name"},
                    "season": {"type": "integer", "description": "Season year (optional)"},
                    "competition": {"type": "string", "description": "Competition name (optional)"},
                },
                "required": ["team"],
            },
        ),
        Tool(
            name="get_head_to_head",
            description="Get head-to-head record between two teams",
            inputSchema={
                "type": "object",
                "properties": {
                    "team1": {"type": "string", "description": "First team name"},
                    "team2": {"type": "string", "description": "Second team name"},
                },
                "required": ["team1", "team2"],
            },
        ),
        Tool(
            name="get_player_by_name",
            description="Find a player by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Player name to search"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="get_players_by_club",
            description="Get all players from a club",
            inputSchema={
                "type": "object",
                "properties": {
                    "club": {"type": "string", "description": "Club name"},
                },
                "required": ["club"],
            },
        ),
        Tool(
            name="get_brazilian_players",
            description="Get all Brazilian players",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_competition_standings",
            description="Get competition standings for a season",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string", "description": "Competition name"},
                    "season": {"type": "integer", "description": "Season year"},
                },
                "required": ["competition", "season"],
            },
        ),
        Tool(
            name="get_big_wins",
            description="Get biggest wins in the dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of big wins to return", "default": 10},
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from the MCP client"""
    try:
        if name == "find_matches_between_teams":
            team1 = arguments.get("team1", "")
            team2 = arguments.get("team2", "")
            matches = query_engine.find_matches_between_teams(team1, team2)
            return [TextContent(text=format_matches_response(matches, f"{team1} vs {team2}"))]
        
        elif name == "find_matches_by_team":
            team = arguments.get("team", "")
            limit = arguments.get("limit", 10)
            matches = query_engine.find_matches_by_team(team, limit)
            return [TextContent(text=format_matches_response(matches, f"{team} Matches"))]
        
        elif name == "find_matches_by_competition":
            competition = arguments.get("competition", "")
            season = arguments.get("season")
            limit = arguments.get("limit", 10)
            
            # Get matches for the competition
            matches = query_engine.find_matches_by_team(competition, limit)
            if season:
                # Filter by season if provided
                matches = [m for m in matches if m.get('season') == season]
            
            return [TextContent(text=format_matches_response(matches, f"{competition} Matches"))]
        
        elif name == "find_matches_by_date_range":
            date_from = arguments.get("date_from", "")
            date_to = arguments.get("date_to", "")
            team = arguments.get("team", "")
            
            # Use get_all_matches with date filters
            all_matches = data_loader.get_all_matches(
                date_from=date_from,
                date_to=date_to,
                home_team=team if team else None,
                away_team=team if team else None,
            )
            
            return [TextContent(text=format_matches_response(all_matches, f"Matches {date_from} to {date_to}"))]
        
        elif name == "get_team_statistics":
            team = arguments.get("team", "")
            season = arguments.get("season")
            competition = arguments.get("competition")
            
            stats = query_engine.get_team_statistics(team, season, competition)
            return [TextContent(text=format_team_stats_response(stats, team))]
        
        elif name == "get_head_to_head":
            team1 = arguments.get("team1", "")
            team2 = arguments.get("team2", "")
            
            h2h = query_engine.get_head_to_head(team1, team2)
            return [TextContent(text=format_head_to_head_response(h2h, team1, team2))]
        
        elif name == "get_player_by_name":
            name = arguments.get("name", "")
            player = query_engine.get_player_by_name(name)
            
            if player:
                return [TextContent(text=format_player_response(player))]
            else:
                return [TextContent(text=f"Player '{name}' not found")]
        
        elif name == "get_players_by_club":
            club = arguments.get("club", "")
            players = query_engine.get_players_by_club(club)
            return [TextContent(text=format_players_response(players, f"{club} Players"))]
        
        elif name == "get_brazilian_players":
            players = query_engine.get_brazilian_players()
            return [TextContent(text=format_players_response(players, "Brazilian Players"))]
        
        elif name == "get_competition_standings":
            competition = arguments.get("competition", "")
            season = arguments.get("season", 2012)
            
            standings = query_engine.get_competition_standings(competition, season)
            return [TextContent(text=format_standings_response(standings, competition, season))]
        
        elif name == "get_big_wins":
            limit = arguments.get("limit", 10)
            wins = query_engine.get_big_wins(limit)
            return [TextContent(text=format_big_wins_response(wins, limit))]
        
        else:
            return [TextContent(text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(text=f"Error: {str(e)}")]


# ========== Main Entry Point ==========

async def main():
    """Main entry point for the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="brazilian-soccer-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
