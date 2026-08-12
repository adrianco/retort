"""FastMCP transport exposing the Brazilian soccer query service."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from .service import SoccerService

mcp = FastMCP("Brazilian Soccer", instructions=(
    "Query the bundled historical Brazilian football match and FIFA player datasets. "
    "Team aliases, accents, state suffixes, and multiple date formats are normalized automatically."
))


@lru_cache(maxsize=1)
def service() -> SoccerService:
    return SoccerService()


@mcp.tool()
def search_matches(team: str | None = None, opponent: str | None = None,
                   competition: str | None = None, season: int | None = None,
                   start_date: str | None = None, end_date: str | None = None,
                   stage: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Find matches by team/opponent, competition, season, date range, or round/stage."""
    return service().search_matches(team, opponent, competition, season, start_date, end_date, stage, limit)


@mcp.tool()
def team_statistics(team: str, season: int | None = None, competition: str | None = None,
                    venue: str = "all") -> dict[str, Any]:
    """Calculate a team's W/D/L, goals, points, and win rate; venue is all, home, or away."""
    return service().team_statistics(team, season, competition, venue)


@mcp.tool()
def compare_teams(team1: str, team2: str, season: int | None = None,
                  competition: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Return head-to-head results and win/draw totals for two teams."""
    return service().head_to_head(team1, team2, season, competition, limit)


@mcp.tool()
def calculate_standings(season: int, competition: str = "Brasileirão", limit: int = 30) -> dict[str, Any]:
    """Calculate a final-style points table from all matching results in a season."""
    return service().standings(season, competition, limit)


@mcp.tool()
def competition_statistics(competition: str | None = None, season: int | None = None) -> dict[str, Any]:
    """Calculate goals/match, home and away wins, draws, and home-win rate."""
    return service().competition_statistics(competition, season)


@mcp.tool()
def biggest_wins(competition: str | None = None, season: int | None = None,
                 limit: int = 10) -> dict[str, Any]:
    """Find matches with the largest winning margins."""
    return service().biggest_wins(competition, season, limit)


@mcp.tool()
def search_players(name: str | None = None, nationality: str | None = None,
                   club: str | None = None, position: str | None = None,
                   min_overall: int | None = None, limit: int = 50) -> dict[str, Any]:
    """Search FIFA players by name, nationality, club, position, or minimum overall rating."""
    return service().search_players(name, nationality, club, position, min_overall, limit)


@mcp.tool()
def team_competitions(team: str, season: int | None = None) -> dict[str, Any]:
    """List every competition in which a team appears, optionally for one season."""
    return service().team_competitions(team, season)


@mcp.tool()
def dataset_summary() -> dict[str, Any]:
    """Report load counts for all six bundled datasets."""
    return service().dataset_summary()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

