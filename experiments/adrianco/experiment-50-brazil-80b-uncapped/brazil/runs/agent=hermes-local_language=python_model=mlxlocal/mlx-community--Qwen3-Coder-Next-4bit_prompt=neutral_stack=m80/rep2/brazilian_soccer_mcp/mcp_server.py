"""MCP Server implementation for Brazilian Soccer using the MCP SDK."""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mcp.server.stdio
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.types import CallToolRequest, CallToolResult
from mcp.server.lowlevel.server import LifespanResultT

from .data_loader import DataFileManager
from .match_queries import MatchQueryEngine
from .team_queries import TeamQueryEngine
from .player_queries import PlayerQueryEngine
from .competition_queries import CompetitionQueryEngine
from .statistical_analysis import StatisticalAnalysisEngine


class BrazilianSoccerMCPServer:
    """MCP Server for Brazilian Soccer Data."""
    
    def __init__(self, data_dir: str = None):
        """Initialize the MCP server with optional data directory."""
        if data_dir is None:
            # Default to data/kaggle relative to this module
            module_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(module_dir, '..', 'data', 'kaggle')
        
        self.data_dir = os.path.abspath(data_dir)
        self.data_manager = DataFileManager(data_dir)
        self.match_engine = MatchQueryEngine(data_dir)
        self.team_engine = TeamQueryEngine(data_dir)
        self.player_engine = PlayerQueryEngine(data_dir)
        self.competition_engine = CompetitionQueryEngine(data_dir)
        self.stats_engine = StatisticalAnalysisEngine(data_dir)
        
        # Initialize MCP server
        self.server = Server("brazilian-soccer-server", version="1.0.0")
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        # Match find tool
        @self.server.call_tool()
        async def find_matches(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Find matches by criteria."""
            team1 = tool_args.get('team1')
            team2 = tool_args.get('team2')
            competition = tool_args.get('competition')
            season = tool_args.get('season')
            limit = tool_args.get('limit', 20)
            
            matches = self.match_engine.find_matches(
                team1=team1,
                team2=team2,
                competition=competition,
                season=season,
                limit=limit
            )
            return {"content": matches, "isError": False}
        
        # Match by teams tool
        @self.server.call_tool()
        async def get_match_by_teams(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get matches between two specific teams."""
            team1 = tool_args.get('team1')
            team2 = tool_args.get('team2')
            limit = tool_args.get('limit', 20)
            
            result = self.match_engine.get_match_by_teams(team1, team2, limit)
            return {"content": result, "isError": False}
        
        # Team statistics tool
        @self.server.call_tool()
        async def get_team_statistics(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get comprehensive statistics for a team."""
            team = tool_args.get('team')
            season = tool_args.get('season')
            competition = tool_args.get('competition')
            
            result = self.team_engine.get_team_statistics(
                team=team,
                season=season,
                competition=competition
            )
            return {"content": result, "isError": False}
        
        # Team home record tool
        @self.server.call_tool()
        async def get_team_home_record(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get home record for a team."""
            team = tool_args.get('team')
            season = tool_args.get('season')
            
            result = self.team_engine.get_team_home_record(team=team, season=season)
            return {"content": result, "isError": False}
        
        # Team away record tool
        @self.server.call_tool()
        async def get_team_away_record(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get away record for a team."""
            team = tool_args.get('team')
            season = tool_args.get('season')
            
            result = self.team_engine.get_team_away_record(team=team, season=season)
            return {"content": result, "isError": False}
        
        # Team head-to-head tool
        @self.server.call_tool()
        async def get_head_to_head(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get head-to-head record between two teams."""
            team1 = tool_args.get('team1')
            team2 = tool_args.get('team2')
            limit = tool_args.get('limit', 20)
            
            result = self.team_engine.get_head_to_head(team1, team2, limit)
            return {"content": result, "isError": False}
        
        # Team competitions tool
        @self.server.call_tool()
        async def get_competitions_for_team(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get competitions for a team."""
            team = tool_args.get('team')
            
            competitions = self.team_engine.get_competitions_for_team(team)
            return {"content": {"competitions": competitions}, "isError": False}
        
        # Player search tool
        @self.server.call_tool()
        async def search_players(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Search players by name."""
            name = tool_args.get('name')
            nationality = tool_args.get('nationality')
            club = tool_args.get('club')
            position = tool_args.get('position')
            limit = tool_args.get('limit', 20)
            
            if name:
                players = self.player_engine.search_players(name, limit)
            elif nationality:
                players = self.player_engine.get_players_by_nationality(nationality, limit)
            elif club:
                players = self.player_engine.get_players_by_club(club, limit)
            elif position:
                players = self.player_engine.get_players_by_position(position, limit)
            else:
                players = self.player_engine.get_all_players()[:limit]
            
            return {"content": {"players": players, "count": len(players)}, "isError": False}
        
        # Brazilian top rated players tool
        @self.server.call_tool()
        async def get_brazilian_top_rated(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get top rated Brazilian players."""
            limit = tool_args.get('limit', 20)
            
            players = self.player_engine.get_brazilian_top_rated(limit)
            return {"content": {"players": players, "count": len(players)}, "isError": False}
        
        # Players by club tool
        @self.server.call_tool()
        async def get_players_by_club(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get players by club."""
            club = tool_args.get('club')
            nationality = tool_args.get('nationality')
            limit = tool_args.get('limit', 50)
            
            players = self.player_engine.get_players_by_club(club, limit)
            
            if nationality:
                players = [
                    p for p in players
                    if nationality.lower() in str(p.get('Nationality', '')).lower()
                ]
            
            return {"content": {"players": players, "count": len(players)}, "isError": False}
        
        # Competition standings tool
        @self.server.call_tool()
        async def get_competition_standings(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get competition standings."""
            competition = tool_args.get('competition')
            season = tool_args.get('season')
            
            result = self.competition_engine.get_competition_standings(competition, season)
            return {"content": result, "isError": False}
        
        # Competition champion tool
        @self.server.call_tool()
        async def get_champion(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get champion of a competition."""
            competition = tool_args.get('competition')
            season = tool_args.get('season')
            
            champion = self.competition_engine.get_champion(competition, season)
            return {"content": {"competition": competition, "season": season, "champion": champion}, "isError": False}
        
        # Cup bracket tool
        @self.server.call_tool()
        async def get_cup_bracket(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get cup bracket for knockout competitions."""
            competition = tool_args.get('competition')
            season = tool_args.get('season')
            
            result = self.competition_engine.get_cup_bracket(competition, season)
            return {"content": result, "isError": False}
        
        # Average goals tool
        @self.server.call_tool()
        async def get_average_goals(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get average goals per match."""
            competition = tool_args.get('competition')
            
            avg = self.stats_engine.get_average_goals_per_match(competition)
            return {"content": {"average_goals": avg, "competition": competition}, "isError": False}
        
        # Biggest victories tool
        @self.server.call_tool()
        async def get_biggest_victories(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get biggest victories."""
            competition = tool_args.get('competition')
            limit = tool_args.get('limit', 10)
            
            victories = self.stats_engine.get_biggest_victories(competition, limit)
            return {"content": {"biggest_victories": victories, "count": len(victories)}, "isError": False}
        
        # Home win rate tool
        @self.server.call_tool()
        async def get_home_win_rate(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get home win rate."""
            competition = tool_args.get('competition')
            
            rate = self.stats_engine.get_home_win_rate(competition)
            return {"content": {"home_win_rate": rate, "competition": competition}, "isError": False}
        
        # Team trend tool
        @self.server.call_tool()
        async def get_team_trend(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get team performance trend."""
            team = tool_args.get('team')
            season = tool_args.get('season')
            competition = tool_args.get('competition')
            matches_back = tool_args.get('matches_back', 10)
            
            trend = self.stats_engine.get_team_performance_trend(
                team, season, competition, matches_back
            )
            return {"content": trend, "isError": False}
        
        # Head-to-head stats tool
        @self.server.call_tool()
        async def get_head_to_head_stats(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get detailed head-to-head statistics."""
            team1 = tool_args.get('team1')
            team2 = tool_args.get('team2')
            
            result = self.stats_engine.get_head_to_head_statistics(team1, team2)
            return {"content": result, "isError": False}
        
        # Competition summary tool
        @self.server.call_tool()
        async def get_competition_summary(
            tool_name: str,
            tool_args: Dict[str, Any]
        ) -> List[Dict[str, Any]]:
            """Get competition or season summary."""
            season = tool_args.get('season')
            competition = tool_args.get('competition')
            
            if season and competition:
                stats = self.stats_engine.get_competition_statistics(competition)
                return {"content": {"competition": competition, "season": season, "statistics": stats}, "isError": False}
            elif season:
                summary = self.stats_engine.get_season_summary(season)
                return {"content": summary, "isError": False}
            else:
                return {"content": {"error": "season parameter required"}, "isError": True}
    
    def get_tools(self) -> List[Tool]:
        """Get list of registered tools."""
        return [
            Tool(
                name="find_matches",
                description="Find matches by criteria such as team, competition, season, or date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team1": {"type": "string", "description": "First team name"},
                        "team2": {"type": "string", "description": "Second team name"},
                        "competition": {"type": "string", "description": "Competition name (Brasileirão, Copa do Brasil, Libertadores)"},
                        "season": {"type": "integer", "description": "Season year"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 20}
                    }
                }
            ),
            Tool(
                name="get_match_by_teams",
                description="Get matches between two specific teams with head-to-head statistics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team1": {"type": "string", "description": "First team name"},
                        "team2": {"type": "string", "description": "Second team name"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 20}
                    }
                }
            ),
            Tool(
                name="get_team_statistics",
                description="Get comprehensive statistics for a team including wins, losses, draws, goals",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name"},
                        "season": {"type": "integer", "description": "Season year"},
                        "competition": {"type": "string", "description": "Competition name"}
                    }
                }
            ),
            Tool(
                name="get_team_home_record",
                description="Get home record for a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name"},
                        "season": {"type": "integer", "description": "Season year"}
                    }
                }
            ),
            Tool(
                name="get_team_away_record",
                description="Get away record for a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name"},
                        "season": {"type": "integer", "description": "Season year"}
                    }
                }
            ),
            Tool(
                name="get_head_to_head",
                description="Get head-to-head record between two teams",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team1": {"type": "string", "description": "First team name"},
                        "team2": {"type": "string", "description": "Second team name"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 20}
                    }
                }
            ),
            Tool(
                name="get_competitions_for_team",
                description="Get list of competitions a team has played in",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name"}
                    }
                }
            ),
            Tool(
                name="search_players",
                description="Search players by name, nationality, club, or position",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Player name to search"},
                        "nationality": {"type": "string", "description": "Nationality filter"},
                        "club": {"type": "string", "description": "Club filter"},
                        "position": {"type": "string", "description": "Position filter"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 20}
                    }
                }
            ),
            Tool(
                name="get_brazilian_top_rated",
                description="Get top rated Brazilian players",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 20}
                    }
                }
            ),
            Tool(
                name="get_players_by_club",
                description="Get players by club with optional nationality filter",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "club": {"type": "string", "description": "Club name"},
                        "nationality": {"type": "string", "description": "Nationality filter"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 50}
                    }
                }
            ),
            Tool(
                name="get_competition_standings",
                description="Get competition standings for a specific season",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Competition name"},
                        "season": {"type": "integer", "description": "Season year"}
                    }
                }
            ),
            Tool(
                name="get_champion",
                description="Get champion of a competition for a specific season",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Competition name"},
                        "season": {"type": "integer", "description": "Season year"}
                    }
                }
            ),
            Tool(
                name="get_cup_bracket",
                description="Get cup bracket for knockout competitions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Competition name"},
                        "season": {"type": "integer", "description": "Season year"}
                    }
                }
            ),
            Tool(
                name="get_average_goals",
                description="Get average goals per match",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Competition name"}
                    }
                }
            ),
            Tool(
                name="get_biggest_victories",
                description="Get biggest victories by goal difference",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Competition name"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                    }
                }
            ),
            Tool(
                name="get_home_win_rate",
                description="Get home win rate percentage",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Competition name"}
                    }
                }
            ),
            Tool(
                name="get_team_trend",
                description="Get team performance trend",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name"},
                        "season": {"type": "integer", "description": "Season year"},
                        "competition": {"type": "string", "description": "Competition name"},
                        "matches_back": {"type": "integer", "description": "Number of recent matches", "default": 10}
                    }
                }
            ),
            Tool(
                name="get_head_to_head_stats",
                description="Get detailed head-to-head statistics between two teams",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team1": {"type": "string", "description": "First team name"},
                        "team2": {"type": "string", "description": "Second team name"}
                    }
                }
            ),
            Tool(
                name="get_competition_summary",
                description="Get competition or season summary",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "season": {"type": "integer", "description": "Season year"},
                        "competition": {"type": "string", "description": "Competition name"}
                    }
                }
            ),
        ]


async def run_server(data_dir: str = None):
    """Run the MCP server."""
    server = BrazilianSoccerMCPServer(data_dir)
    
    # Create tools list for MCP protocol
    tools = server.get_tools()
    
    async def run_stdio():
        """Run server using stdio transport."""
        async def run(read, write):
            server_session = mcp.server.stdio.ServerSession(
                server.server,
                initialize_params=None,
                notification_options=None,
                experimental_capabilities=None,
            )
            await server_session.run(read, write)
        
        await mcp.server.stdio.stdio_server(run)
    
    await run_stdio()


# Create a default server instance
default_server = BrazilianSoccerMCPServer()


if __name__ == "__main__":
    asyncio.run(run_server())
