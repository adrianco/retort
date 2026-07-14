"""
Brazilian Soccer MCP Server.

Exposes a knowledge interface over the bundled Kaggle datasets as Model Context
Protocol tools, so an LLM client can answer natural-language questions about
Brazilian soccer players, teams, matches, competitions and statistics.

The tools are thin adapters over ``SoccerService``; all domain logic lives in
``soccer_service.py`` / ``soccer_data.py``. Run with ``python server.py`` to
serve over stdio (the standard MCP transport).

Published tools
---------------
* find_matches            -- matches by team / opponent / competition / season / date
* get_team_record         -- a team's W/D/L, goals and win-rate
* compare_teams           -- head-to-head between two teams
* search_players          -- FIFA players by name / nationality / club / position
* get_standings           -- league table for a season, computed from results
* get_competition_summary -- aggregate goal/result statistics + biggest wins
* list_team_competitions  -- which competitions a team appears in
* get_team_profile        -- combined match record + FIFA squad (cross-file)
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from soccer_service import SoccerService

mcp = FastMCP("brazilian-soccer")
_service = SoccerService()


@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """Find matches by team, opponent, competition, season and/or date range.

    When both ``team`` and ``opponent`` are given, the result also includes a
    head-to-head summary. Dates use ISO format (YYYY-MM-DD). Results are newest
    first.
    """
    return _service.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@mcp.tool()
def get_team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> dict:
    """Get a team's win/draw/loss record, goals and win rate.

    ``venue`` is one of "all", "home" or "away". Optionally restrict to a
    ``season`` and/or ``competition``.
    """
    return _service.get_team_record(
        team=team, season=season, competition=competition, venue=venue
    )


@mcp.tool()
def compare_teams(
    team_a: str,
    team_b: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
) -> dict:
    """Compare two teams head-to-head: wins, draws and goals between them."""
    return _service.compare_teams(
        team_a=team_a, team_b=team_b, season=season, competition=competition
    )


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Search FIFA players by name, nationality, club and/or position.

    Results are sorted by overall rating (highest first). For example,
    ``nationality="Brazil"`` returns the top Brazilian players.
    """
    return _service.search_players(
        name=name, nationality=nationality, club=club, position=position, limit=limit
    )


@mcp.tool()
def get_standings(
    season: int, competition: str = "Brasileirão", limit: int = 20
) -> dict:
    """Compute the league standings for a season directly from match results.

    Returns a points-ranked table (3 for a win, 1 for a draw) and the champion.
    """
    return _service.get_standings(season=season, competition=competition, limit=limit)


@mcp.tool()
def get_competition_summary(
    competition: Optional[str] = None, season: Optional[int] = None
) -> dict:
    """Aggregate statistics for a competition / season.

    Includes average goals per match, home/away/draw split, home win rate and
    the biggest-margin victories.
    """
    return _service.get_competition_summary(competition=competition, season=season)


@mcp.tool()
def list_team_competitions(team: str) -> dict:
    """List the competitions a team appears in, with match counts and seasons."""
    return _service.list_team_competitions(team=team)


@mcp.tool()
def get_team_profile(team: str) -> dict:
    """Combined profile: a team's overall match record plus its FIFA squad.

    Demonstrates a cross-file query joining match data with player data.
    """
    return _service.get_team_profile(team=team)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
