"""MCP server entry point exposing Brazilian-soccer queries as tools.

Uses the FastMCP convenience layer from the official ``mcp`` Python SDK so
each query function becomes a callable MCP tool over stdio. Run with::

    brazilian-soccer-mcp

or programmatically via ``main()``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import queries as Q
from .data_loader import DataStore, load_all

mcp = FastMCP("brazilian-soccer")

_store: DataStore | None = None


def _ds() -> DataStore:
    global _store
    if _store is None:
        _store = load_all()
    return _store


# ---------------------------------------------------------------------------
# Match tools
# ---------------------------------------------------------------------------

@mcp.tool()
def find_matches(
    team: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search matches by team, competition, season, or date range."""
    return Q.find_matches(
        _ds(),
        team=team, home_team=home_team, away_team=away_team, opponent=opponent,
        competition=competition, season=season,
        date_from=date_from, date_to=date_to, limit=limit,
    )


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Head-to-head record and match list between two teams."""
    return Q.head_to_head(_ds(), team_a, team_b, competition=competition, season=season)


# ---------------------------------------------------------------------------
# Team tools
# ---------------------------------------------------------------------------

@mcp.tool()
def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> dict[str, Any]:
    """Team win/loss/draw record and goal totals. ``venue`` is all|home|away."""
    return Q.team_stats(_ds(), team, season=season, competition=competition, venue=venue)


@mcp.tool()
def team_competitions(team: str) -> list[dict[str, Any]]:
    """List competitions a team has appeared in, with match counts."""
    return Q.team_competitions(_ds(), team)


# ---------------------------------------------------------------------------
# Player tools
# ---------------------------------------------------------------------------

@mcp.tool()
def find_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Search FIFA player database by name / nationality / club / position."""
    return Q.find_players(
        _ds(), name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, limit=limit,
    )


@mcp.tool()
def top_brazilian_players(limit: int = 20) -> list[dict[str, Any]]:
    """Top FIFA-rated Brazilian players."""
    return Q.top_brazilian_players(_ds(), limit=limit)


@mcp.tool()
def players_at_brazilian_clubs() -> list[dict[str, Any]]:
    """Group FIFA players by Brazilian club (those that appear in match data)."""
    return Q.players_at_brazilian_clubs(_ds())


# ---------------------------------------------------------------------------
# Competition tools
# ---------------------------------------------------------------------------

@mcp.tool()
def standings(season: int, competition: str = "Brasileirão") -> list[dict[str, Any]]:
    """Compute the final standings for a season+competition."""
    return Q.standings(_ds(), season=season, competition=competition)


@mcp.tool()
def season_summary(season: int, competition: str = "Brasileirão") -> dict[str, Any]:
    """Champion, runner-up, last-place, and standings for a given season."""
    return Q.season_summary(_ds(), season=season, competition=competition)


# ---------------------------------------------------------------------------
# Statistical tools
# ---------------------------------------------------------------------------

@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Largest-margin victories matching the filter."""
    return Q.biggest_wins(_ds(), competition=competition, season=season, limit=limit)


@mcp.tool()
def aggregate_stats(
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Average goals per match, home/away/draw rates for the filter."""
    return Q.aggregate_stats(_ds(), competition=competition, season=season)


@mcp.tool()
def top_scoring_teams(
    season: int,
    competition: str = "Brasileirão",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Teams that scored the most goals in a season+competition."""
    return Q.top_scoring_teams(_ds(), season=season, competition=competition, limit=limit)


@mcp.tool()
def best_records(
    season: int,
    competition: str = "Brasileirão",
    venue: str = "home",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Teams with the best home or away record for a season+competition."""
    return Q.best_records(_ds(), season=season, competition=competition, venue=venue, limit=limit)


def main() -> None:
    """Entry point used by the console script."""
    # Trigger the (slow) initial load up-front so the first tool call is fast.
    _ds()
    mcp.run()


if __name__ == "__main__":
    main()
