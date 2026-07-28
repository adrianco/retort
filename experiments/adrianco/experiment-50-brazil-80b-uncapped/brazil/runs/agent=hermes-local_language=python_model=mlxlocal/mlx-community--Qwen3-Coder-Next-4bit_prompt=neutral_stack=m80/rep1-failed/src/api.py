# API endpoints for Brazilian Soccer MCP Server
"""API endpoints for the Brazilian Soccer MCP Server."""

from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from src.models import Match, Player, TeamStats, TeamComparison, CompetitionStandings, QueryResponse
from src.data_utils import QueryEngine


app = FastAPI(
    title="Brazilian Soccer MCP Server",
    description="Model Context Protocol server for Brazilian soccer data",
    version="1.0.0"
)

query_engine = QueryEngine()


# Request/Response models
class MatchQueryRequest(BaseModel):
    team1: Optional[str] = None
    team2: Optional[str] = None
    season: Optional[int] = None
    competition: Optional[str] = None
    limit: int = 100


class TeamStatsRequest(BaseModel):
    team: str
    season: Optional[int] = None
    competition: Optional[str] = None


class TeamComparisonRequest(BaseModel):
    team1: str
    team2: str


class PlayerSearchRequest(BaseModel):
    name: Optional[str] = None
    club: Optional[str] = None
    nationality: Optional[str] = None
    position: Optional[str] = None


class CompetitionStandingsRequest(BaseModel):
    competition: str
    season: int


# Match Endpoints
@app.get("/api/matches", response_model=QueryResponse)
async def get_matches(
    team1: Optional[str] = Query(None, description="First team name"),
    team2: Optional[str] = Query(None, description="Second team name"),
    season: Optional[int] = Query(None, description="Season year"),
    competition: Optional[str] = Query(None, description="Competition name"),
    limit: int = Query(100, description="Maximum number of results"),
):
    """Find matches by criteria."""
    try:
        engine = QueryEngine()
        
        if team1 and team2:
            matches = engine.find_matches_by_teams(team1, team2, limit)
        elif team1:
            matches = engine.find_matches_by_team(team1, season, competition)
        else:
            matches = engine.get_all_matches()
            if season:
                matches = [m for m in matches if m.season == season]
            if competition:
                matches = [m for m in matches if m.competition.lower() == competition.lower()]
        
        # Limit results
        matches = matches[:limit]
        
        return QueryResponse(
            query_type="match_search",
            success=True,
            message=f"Found {len(matches)} matches",
            data=[m.to_dict() for m in matches],
            count=len(matches),
            metadata={
                "team1": team1,
                "team2": team2,
                "season": season,
                "competition": competition,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/matches/{match_id}", response_model=QueryResponse)
async def get_match(match_id: int):
    """Get a specific match by ID."""
    try:
        engine = QueryEngine()
        matches = engine.get_all_matches()
        
        for match in matches:
            if match.id == match_id:
                return QueryResponse(
                    query_type="match_by_id",
                    success=True,
                    message=f"Found match {match_id}",
                    data=match.to_dict(),
                    count=1,
                )
        
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Team Endpoints
@app.get("/api/teams/stats", response_model=TeamStats)
async def get_team_stats(team: str, season: Optional[int] = Query(None), competition: Optional[str] = Query(None)):
    """Get team statistics."""
    try:
        engine = QueryEngine()
        stats = engine.get_team_stats(team, season, competition)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teams/comparison", response_model=TeamComparison)
async def get_team_comparison(team1: str, team2: str):
    """Get head-to-head comparison between two teams."""
    try:
        engine = QueryEngine()
        comparison = engine.get_team_comparison(team1, team2)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Player Endpoints
@app.get("/api/players/search", response_model=QueryResponse)
async def search_players(
    name: Optional[str] = Query(None, description="Player name to search"),
    club: Optional[str] = Query(None, description="Club name"),
    nationality: Optional[str] = Query(None, description="Nationality"),
    position: Optional[str] = Query(None, description="Position"),
    limit: int = Query(100, description="Maximum number of results"),
):
    """Search for players."""
    try:
        engine = QueryEngine()
        
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
        
        return QueryResponse(
            query_type="player_search",
            success=True,
            message=f"Found {len(players)} players",
            data=[p.to_dict() for p in players],
            count=len(players),
            metadata={
                "name": name,
                "club": club,
                "nationality": nationality,
                "position": position,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/players/brazilian/top", response_model=QueryResponse)
async def get_top_brazilian_players(limit: int = Query(10, description="Number of top players")):
    """Get top rated Brazilian players."""
    try:
        engine = QueryEngine()
        players = engine.get_top_brazilian_players(limit)
        
        return QueryResponse(
            query_type="brazilian_players",
            success=True,
            message=f"Found {len(players)} top Brazilian players",
            data=[p.to_dict() for p in players],
            count=len(players),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Competition Endpoints
@app.get("/api/competitions/standings", response_model=QueryResponse)
async def get_competition_standings(competition: str, season: int):
    """Get competition standings for a season."""
    try:
        engine = QueryEngine()
        standings = engine.get_competition_standings(competition, season)
        
        return QueryResponse(
            query_type="competition_standings",
            success=True,
            message=f"Found {len(standings)} teams",
            data=[s.to_dict() for s in standings],
            count=len(standings),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Statistical Analysis Endpoints
@app.get("/api/stats/big-wins", response_model=QueryResponse)
async def get_big_wins(competition: Optional[str] = Query(None), limit: int = Query(10)):
    """Get biggest wins in matches."""
    try:
        engine = QueryEngine()
        wins = engine.get_big_wins(competition, limit)
        
        return QueryResponse(
            query_type="big_wins",
            success=True,
            message=f"Found {len(wins)} big wins",
            data=[w.to_dict() for w in wins],
            count=len(wins),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/average-goals", response_model=QueryResponse)
async def get_average_goals(competition: Optional[str] = Query(None)):
    """Get average goals per match."""
    try:
        engine = QueryEngine()
        avg = engine.get_average_goals_per_match(competition)
        
        return QueryResponse(
            query_type="average_goals",
            success=True,
            message=f"Average goals per match: {avg}",
            data={"average": avg},
            count=1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/home-win-rate", response_model=QueryResponse)
async def get_home_win_rate():
    """Get home win rate."""
    try:
        engine = QueryEngine()
        rate = engine.get_home_win_rate()
        
        return QueryResponse(
            query_type="home_win_rate",
            success=True,
            message=f"Home win rate: {rate}%",
            data={"rate": rate},
            count=1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Brazilian Soccer MCP Server",
        "version": "1.0.0",
        "description": "Model Context Protocol server for Brazilian soccer data",
        "endpoints": [
            "/api/matches - Find matches",
            "/api/matches/{id} - Get match by ID",
            "/api/teams/stats - Get team statistics",
            "/api/teams/comparison - Get team comparison",
            "/api/players/search - Search players",
            "/api/players/brazilian/top - Get top Brazilian players",
            "/api/competitions/standings - Get competition standings",
            "/api/stats/big-wins - Get big wins",
            "/api/stats/average-goals - Get average goals",
            "/api/stats/home-win-rate - Get home win rate",
        ],
    }
