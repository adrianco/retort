"""
Brazilian Soccer MCP Server
Main server file that integrates all components
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from data_loader import SoccerDataLoader
from query_engine import (
    SoccerQueryEngine,
    TeamStats,
    MatchResult,
    PlayerInfo,
    CompetitionStandings,
    BigWin,
)

# Initialize components
DATA_DIR = Path(__file__).parent / "data" / "kaggle"
data_loader = SoccerDataLoader(DATA_DIR)
query_engine = SoccerQueryEngine(data_loader)

# FastAPI app
app = FastAPI()


class QueryRequest(BaseModel):
    """Query request model"""
    action: str = Field(..., description="Action to perform")
    params: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")


class QueryResponse(BaseModel):
    """Query response model"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "name": "Brazilian Soccer MCP Server",
        "version": "1.0.0",
        "description": "MCP Server for Brazilian soccer data queries",
        "endpoints": [
            "/query",
            "/health",
            "/stats",
        ]
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/stats")
def get_data_stats():
    """Get data statistics"""
    stats = {
        "brasileirao_matches": len(data_loader.brasileirao_df) if data_loader.brasileirao_df is not None else 0,
        "copa_do_brasil_matches": len(data_loader.copa_do_brasil_df) if data_loader.copa_do_brasil_df is not None else 0,
        "libertadores_matches": len(data_loader.libertadores_df) if data_loader.libertadores_df is not None else 0,
        "br_football_matches": len(data_loader.br_football_df) if data_loader.br_football_df is not None else 0,
        "campeonato_matches": len(data_loader.campeonato_brasileiro_df) if data_loader.campeonato_brasileiro_df is not None else 0,
        "fifa_players": len(data_loader.fifa_df) if data_loader.fifa_df is not None else 0,
    }
    return stats


@app.post("/query")
def execute_query(request: QueryRequest):
    """Execute a query"""
    action = request.action
    params = request.params
    
    try:
        if action == "find_matches_between_teams":
            team1 = params.get("team1", "")
            team2 = params.get("team2", "")
            result = query_engine.find_matches_between_teams(team1, team2)
            return {"success": True, "data": result}

        elif action == "get_team_statistics":
            team = params.get("team", "")
            season = params.get("season")
            competition = params.get("competition")
            stats = query_engine.get_team_statistics(team, season, competition)
            return {"success": True, "data": stats.model_dump()}

        elif action == "get_player_by_name":
            name = params.get("name", "")
            player = query_engine.get_player_by_name(name)
            if player:
                return {"success": True, "data": player.model_dump()}
            return {"success": False, "error": "Player not found"}

        elif action == "get_players_by_club":
            club = params.get("club", "")
            players = query_engine.get_players_by_club(club)
            return {"success": True, "data": [p.model_dump() for p in players]}

        elif action == "get_brazilian_players":
            players = query_engine.get_brazilian_players()
            return {"success": True, "data": [p.model_dump() for p in players]}

        elif action == "get_competition_standings":
            competition = params.get("competition", "")
            season = params.get("season", 2012)
            standings = query_engine.get_competition_standings(competition, season)
            return {"success": True, "data": standings}

        elif action == "get_big_wins":
            limit = params.get("limit", 10)
            wins = query_engine.get_big_wins(limit)
            return {"success": True, "data": wins}

        elif action == "get_head_to_head":
            team1 = params.get("team1", "")
            team2 = params.get("team2", "")
            h2h = query_engine.get_head_to_head(team1, team2)
            return {"success": True, "data": h2h}

        elif action == "find_matches_by_team":
            team = params.get("team", "")
            limit = params.get("limit", 10)
            matches = query_engine.find_matches_by_team(team, limit)
            return {"success": True, "data": matches}

        elif action == "get_team_match_history":
            team = params.get("team", "")
            season = params.get("season")
            history = query_engine.get_team_match_history(team, season)
            return {"success": True, "data": history}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
