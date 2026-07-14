"""Brazilian Soccer MCP Server."""

from pathlib import Path
from typing import Optional
import json

from mcp.server.fastmcp import FastMCP

from data_loader import DataLoader
from query_engine import QueryEngine

# ─── Bootstrap ────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

_loader = DataLoader(DATA_DIR)
_engine = QueryEngine(_loader)

mcp = FastMCP("Brazilian Soccer")


# ─── Helper ───────────────────────────────────────────────────────────────────

def _to_json(obj) -> str:
    """Serialize object to a nicely formatted JSON string, handling date objects."""
    import datetime

    def default(o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        return str(o)

    return json.dumps(obj, indent=2, default=default, ensure_ascii=False)


# ─── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Find soccer matches with optional filters.

    Args:
        team: Team name (partial state suffix is stripped automatically)
        season: 4-digit year, e.g. 2022
        competition: One of 'brasileirao', 'cup', 'libertadores', 'historical', 'extended'
        date_from: Start date in YYYY-MM-DD format
        date_to: End date in YYYY-MM-DD format
        limit: Maximum number of results (default 20)
    """
    results = _engine.find_matches(
        team=team,
        season=season,
        competition=competition,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return _to_json(results)


@mcp.tool()
def head_to_head(team1: str, team2: str) -> str:
    """Get head-to-head statistics between two teams.

    Args:
        team1: First team name
        team2: Second team name
    """
    result = _engine.head_to_head(team1, team2)
    return _to_json(result)


@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """Get statistics for a team.

    Args:
        team: Team name
        competition: Filter by competition name
        season: Filter by year
        home_only: Count only home matches
        away_only: Count only away matches
    """
    result = _engine.get_team_stats(
        team=team,
        competition=competition,
        season=season,
        home_only=home_only,
        away_only=away_only,
    )
    return _to_json(result)


@mcp.tool()
def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_rating: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Search for FIFA player data.

    Args:
        name: Partial name match (case-insensitive)
        nationality: Filter by nationality
        club: Filter by club name
        position: Filter by position code (e.g. 'ST', 'GK')
        min_rating: Minimum overall rating
        limit: Maximum results (default 20)
    """
    results = _engine.find_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_rating=min_rating,
        limit=limit,
    )
    return _to_json(results)


@mcp.tool()
def get_standings(season: int, competition: str = "brasileirao") -> str:
    """Get league standings for a season.

    Args:
        season: The year (e.g. 2022)
        competition: Competition name (default 'brasileirao')
    """
    result = _engine.get_standings(season=season, competition=competition)
    return _to_json(result)


@mcp.tool()
def get_biggest_wins(competition: Optional[str] = None, limit: int = 10) -> str:
    """Get the biggest wins by goal difference.

    Args:
        competition: Optional competition filter
        limit: Maximum number of results (default 10)
    """
    result = _engine.get_biggest_wins(competition=competition, limit=limit)
    return _to_json(result)


@mcp.tool()
def competition_averages(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Get average statistics across matches.

    Args:
        competition: Optional competition filter
        season: Optional season (year) filter
    """
    result = _engine.competition_averages(competition=competition, season=season)
    return _to_json(result)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
