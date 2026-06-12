"""Brazilian Soccer MCP Server.

Exposes six tools over the Model Context Protocol (stdio transport):
  search_matches, head_to_head, get_team_record, get_standings,
  search_players, get_statistics
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from data_loader import DataLoader
from query_engine import QueryEngine

mcp = FastMCP("Brazilian Soccer")

_loader = DataLoader()
_engine = QueryEngine(_loader)


@mcp.tool()
def search_matches(
    team: str = "",
    opponent: str = "",
    competition: str = "",
    season: int = 0,
    date_from: str = "",
    date_to: str = "",
    limit: int = 20,
) -> str:
    """Search Brazilian soccer matches by team, opponent, competition, season, or date range.

    team: Team name (e.g. "Flamengo", "Palmeiras-SP")
    opponent: Opponent team name — combined with `team` for head-to-head lookup
    competition: Competition name substring (e.g. "Brasileirão", "Copa do Brasil", "Libertadores")
    season: Four-digit year (e.g. 2023). Use 0 to skip.
    date_from: Start date filter in YYYY-MM-DD format
    date_to: End date filter in YYYY-MM-DD format
    limit: Maximum results to return (default 20)
    """
    return _engine.search_matches(
        team=team or None,
        opponent=opponent or None,
        competition=competition or None,
        season=season or None,
        date_from=date_from or None,
        date_to=date_to or None,
        limit=limit,
    )


@mcp.tool()
def head_to_head(
    team1: str,
    team2: str,
    competition: str = "",
    season: int = 0,
    limit: int = 20,
) -> str:
    """Head-to-head record and match history between two teams.

    team1: First team name (e.g. "Flamengo")
    team2: Second team name (e.g. "Fluminense")
    competition: Optional competition filter
    season: Optional season year filter (0 = all seasons)
    limit: Maximum recent matches to list
    """
    return _engine.head_to_head(
        team1=team1,
        team2=team2,
        competition=competition or None,
        season=season or None,
        limit=limit,
    )


@mcp.tool()
def get_team_record(
    team: str,
    competition: str = "",
    season: int = 0,
    home_away: str = "all",
) -> str:
    """Win/draw/loss record and goals statistics for a team.

    team: Team name (e.g. "Corinthians")
    competition: Optional competition filter
    season: Optional season year (0 = all seasons)
    home_away: "all" (default), "home", or "away"
    """
    return _engine.get_team_record(
        team=team,
        competition=competition or None,
        season=season or None,
        home_away=home_away,
    )


@mcp.tool()
def get_standings(
    season: int,
    competition: str = "Brasileirão",
) -> str:
    """Calculate league standings for a season from match results.

    season: Four-digit year (e.g. 2019)
    competition: Competition name (default "Brasileirão"). Also try "Serie A".
    """
    return _engine.get_standings(season=season, competition=competition)


@mcp.tool()
def search_players(
    name: str = "",
    nationality: str = "",
    club: str = "",
    position: str = "",
    min_overall: int = 0,
    max_overall: int = 0,
    limit: int = 20,
) -> str:
    """Search the FIFA player database for players matching given criteria.

    name: Player name (partial match, e.g. "Neymar")
    nationality: Nationality (e.g. "Brazil")
    club: Club name (e.g. "Flamengo")
    position: Position code (e.g. "GK", "ST", "CAM")
    min_overall: Minimum FIFA overall rating (0 = no filter)
    max_overall: Maximum FIFA overall rating (0 = no filter)
    limit: Maximum results (default 20)
    """
    return _engine.search_players(
        name=name or None,
        nationality=nationality or None,
        club=club or None,
        position=position or None,
        min_overall=min_overall or None,
        max_overall=max_overall or None,
        limit=limit,
    )


@mcp.tool()
def get_statistics(
    stat_type: str,
    competition: str = "",
    season: int = 0,
    limit: int = 10,
) -> str:
    """Get aggregate match statistics.

    stat_type: One of:
      - "goals_per_match"   — average goals, home/draw/away rates
      - "biggest_wins"      — matches with largest goal difference
      - "best_home_record"  — teams ranked by home win percentage
      - "best_away_record"  — teams ranked by away win percentage
      - "top_teams_goals"   — teams ranked by total goals scored
    competition: Optional competition filter
    season: Optional season year filter (0 = all seasons)
    limit: Number of entries to show (default 10)
    """
    return _engine.get_statistics(
        stat_type=stat_type,
        competition=competition or None,
        season=season or None,
        limit=limit,
    )


if __name__ == "__main__":
    mcp.run()
