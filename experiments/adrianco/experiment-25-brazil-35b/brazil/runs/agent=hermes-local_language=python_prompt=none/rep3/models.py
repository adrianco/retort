# Brazilian Soccer MCP Server - Pydantic Models
# Defines all data models for the MCP tools using Pydantic.
# Provides structured request/response types for the MCP protocol.

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# --- Request Models ---

class MatchSearchRequest(BaseModel):
    """Request model for searching matches."""
    team: Optional[str] = Field(None, description="Team name to filter matches (home or away)")
    date_from: Optional[str] = Field(None, description="Start date in ISO format (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date in ISO format (YYYY-MM-DD)")
    competition: Optional[str] = Field(None, description="Competition name to filter (e.g., Brasileirao, Copa do Brasil, Libertadores)")
    season: Optional[int] = Field(None, description="Season year to filter")


class TeamStatsRequest(BaseModel):
    """Request model for team statistics."""
    team: str = Field(..., description="Team name")
    competition: Optional[str] = Field(None, description="Competition name to filter (optional)")


class HeadToHeadRequest(BaseModel):
    """Request model for head-to-head comparison."""
    team1: str = Field(..., description="First team name")
    team2: str = Field(..., description="Second team name")
    competition: Optional[str] = Field(None, description="Competition name to filter (optional)")


class PlayerSearchRequest(BaseModel):
    """Request model for player search."""
    nationality: Optional[str] = Field(None, description="Nationality to filter (e.g., Brazil)")
    club: Optional[str] = Field(None, description="Club name to filter (partial match)")
    position: Optional[str] = Field(None, description="Position to filter (e.g., Forward, GK)")
    min_overall: Optional[int] = Field(None, description="Minimum FIFA overall rating")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum number of results")


class SeasonStandingsRequest(BaseModel):
    """Request model for season standings."""
    season: int = Field(..., ge=2000, le=2025, description="Season year")
    competition: str = Field(default="Brasileirao", description="Competition name")


class AverageGoalsRequest(BaseModel):
    """Request model for average goals statistics."""
    pass


class TopScoringMatchesRequest(BaseModel):
    """Request model for top scoring matches."""
    limit: int = Field(default=20, ge=1, le=100, description="Number of matches to return")


class PlayerByClubRequest(BaseModel):
    """Request model for players at a specific club."""
    club: str = Field(..., description="Club name to search")
    position: Optional[str] = Field(None, description="Position filter (e.g., Forward)")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum number of results")


class PlayerByNationalityRequest(BaseModel):
    """Request model for players by nationality."""
    nationality: str = Field(..., description="Nationality to filter")
    min_overall: Optional[int] = Field(None, description="Minimum FIFA overall rating")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum number of results")


# --- Response Models ---

class MatchResponse(BaseModel):
    """Response model for a single match."""
    date: Optional[str] = Field(None, description="Match date (ISO format)")
    home_team: str = Field(..., description="Home team name (normalized)")
    away_team: str = Field(..., description="Away team name (normalized)")
    home_goals: int = Field(..., description="Goals scored by home team")
    away_goals: int = Field(..., description="Goals scored by away team")
    competition: str = Field(..., description="Competition name")
    season: Optional[int] = Field(None, description="Season year")
    round: Optional[str] = Field(None, description="Match round number")
    stage: Optional[str] = Field(None, description="Tournament stage (for Libertadores)")
    home_corners: Optional[int] = Field(None, description="Home team corners")
    away_corners: Optional[int] = Field(None, description="Away team corners")
    home_shots: Optional[int] = Field(None, description="Home team shots")
    away_shots: Optional[int] = Field(None, description="Away team shots")


class TeamStatsResponse(BaseModel):
    """Response model for team statistics."""
    team: str = Field(..., description="Team name")
    matches: int = Field(..., description="Total matches played")
    wins: int = Field(..., description="Number of wins")
    draws: int = Field(..., description="Number of draws")
    losses: int = Field(..., description="Number of losses")
    goals_for: int = Field(..., description="Total goals scored")
    goals_against: int = Field(..., description="Total goals conceded")
    win_rate: float = Field(..., description="Win rate percentage")


class HeadToHeadResponse(BaseModel):
    """Response model for head-to-head comparison."""
    team1: str = Field(..., description="First team name")
    team2: str = Field(..., description="Second team name")
    total_matches: int = Field(..., description="Total matches between teams")
    team1_wins: int = Field(..., description="Team 1 wins")
    team2_wins: int = Field(..., description="Team 2 wins")
    draws: int = Field(..., description="Draws")
    matches: List[Dict[str, Any]] = Field(default_factory=list, description="Individual match results")


class PlayerResponse(BaseModel):
    """Response model for a player."""
    id: int = Field(..., description="Player ID")
    name: str = Field(..., description="Player name")
    age: int = Field(..., description="Player age")
    nationality: str = Field(..., description="Player nationality")
    overall: int = Field(..., description="FIFA overall rating")
    potential: int = Field(..., description="FIFA potential rating")
    club: str = Field(..., description="Current club")
    position: str = Field(..., description="Playing position")
    jersey_number: int = Field(..., description="Jersey number")
    height: str = Field(..., description="Player height")
    weight: str = Field(..., description="Player weight")
    preferred_foot: str = Field(..., description="Preferred foot")


class AverageGoalsResponse(BaseModel):
    """Response model for average goals statistics."""
    total_matches: int = Field(..., description="Total matches analyzed")
    total_goals: int = Field(..., description="Total goals scored")
    average_goals_per_match: float = Field(..., description="Average goals per match")
    home_win_rate: float = Field(..., description="Home win rate percentage")
    away_win_rate: float = Field(..., description="Away win rate percentage")
    draw_rate: float = Field(..., description="Draw rate percentage")


class StandingsResponse(BaseModel):
    """Response model for season standings."""
    season: int = Field(..., description="Season year")
    competition: str = Field(..., description="Competition name")
    standings: List[Dict[str, Any]] = Field(default_factory=list, description="Team standings sorted by points")


class TopScoringMatchResponse(BaseModel):
    """Response model for a high-scoring match."""
    date: Optional[str] = Field(None, description="Match date")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    home_goals: int = Field(..., description="Home goals")
    away_goals: int = Field(..., description="Away goals")
    total_goals: int = Field(..., description="Total goals in match")
    competition: str = Field(..., description="Competition name")


class MCPResponse(BaseModel):
    """Generic MCP tool response wrapper."""
    success: bool = Field(..., description="Whether the request succeeded")
    message: str = Field(..., description="Response message or summary")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    errors: List[str] = Field(default_factory=list, description="List of error messages if any")


class ToolsListResponse(BaseModel):
    """Response for listing available MCP tools."""
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="List of available tools")
    tool_count: int = Field(..., description="Number of tools available")


class HealthCheckResponse(BaseModel):
    """Response for health check / info endpoint."""
    status: str = Field(..., description="Server status")
    datasets_loaded: bool = Field(..., description="Whether datasets are loaded")
    total_matches: int = Field(..., description="Total matches loaded")
    total_players: int = Field(..., description="Total players loaded")
    teams_count: int = Field(..., description="Unique teams found")
    data_sources: Dict[str, int] = Field(..., description="Match counts per data source")
