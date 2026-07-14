"""MCP server entry point for the Brazilian soccer knowledge graph.

Exposes the functions in :mod:`brazilian_soccer_mcp.queries` as tools an LLM
client can invoke over the Model Context Protocol. Uses the FastMCP wrapper
from the official ``mcp`` Python SDK and the standard stdio transport so any
MCP-compatible client can launch it directly:

    python -m brazilian_soccer_mcp.server

Each tool returns a JSON-serializable dict; the MCP framework handles the
wire format.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .data_loader import DEFAULT_DATA_DIR, DataStore
from . import queries as q


def build_server(data_dir: Path | str | None = None) -> tuple[FastMCP, DataStore]:
    """Construct a configured FastMCP server plus its underlying DataStore."""
    if data_dir is None:
        data_dir = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR", str(DEFAULT_DATA_DIR))
    store = DataStore(data_dir=Path(data_dir))
    mcp = FastMCP("brazilian-soccer")

    # ------------------------------------------------------------------
    # Match tools
    # ------------------------------------------------------------------
    @mcp.tool()
    def search_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search matches by team, opponent, competition, season, or date range.

        ``competition`` is a substring match on the canonical names
        ("Serie A", "Copa do Brasil", "Libertadores", ...).
        Dates are ISO ("YYYY-MM-DD"). Returns most recent first.
        """
        return q.search_matches(
            store,
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    @mcp.tool()
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
    ) -> dict[str, Any]:
        """Compute head-to-head wins/draws/losses/goals between two clubs."""
        return q.head_to_head(
            store, team_a, team_b, competition=competition, season=season
        )

    @mcp.tool()
    def last_match(team_a: str, team_b: str) -> dict[str, Any]:
        """Return the most recent match between two clubs."""
        return q.last_match(store, team_a, team_b)

    # ------------------------------------------------------------------
    # Team tools
    # ------------------------------------------------------------------
    @mcp.tool()
    def team_record(
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str | None = None,
    ) -> dict[str, Any]:
        """Wins/draws/losses/goals for a single team.

        ``venue`` is "home", "away", or omitted for both.
        """
        return q.team_record(
            store, team, competition=competition, season=season, venue=venue
        )

    @mcp.tool()
    def top_scoring_teams(
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Teams ranked by total goals scored, filtered by season/competition."""
        return q.top_scoring_teams(
            store, competition=competition, season=season, limit=limit
        )

    @mcp.tool()
    def compare_teams(
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
    ) -> dict[str, Any]:
        """Stat-by-stat comparison of two teams plus their head-to-head record."""
        return q.compare_teams(
            store, team_a, team_b, competition=competition, season=season
        )

    # ------------------------------------------------------------------
    # Player tools
    # ------------------------------------------------------------------
    @mcp.tool()
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search FIFA player data by any combination of attributes."""
        return q.search_players(
            store,
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            limit=limit,
        )

    @mcp.tool()
    def top_brazilian_players(limit: int = 10) -> dict[str, Any]:
        """Top-rated Brazilian players, sorted by FIFA overall rating."""
        return q.top_players_by_nationality(store, "Brazil", limit=limit)

    @mcp.tool()
    def brazilian_player_summary() -> dict[str, Any]:
        """How many Brazilian players are at each Brazilian club, with avg rating."""
        return q.brazilian_player_summary(store)

    # ------------------------------------------------------------------
    # Competition tools
    # ------------------------------------------------------------------
    @mcp.tool()
    def season_standings(
        season: int,
        competition: str = "Brasileirão Serie A",
        limit: int = 20,
    ) -> dict[str, Any]:
        """League standings calculated from match results (3 for win, 1 for draw)."""
        return q.season_standings(store, season, competition=competition, limit=limit)

    @mcp.tool()
    def list_competitions() -> dict[str, Any]:
        """All competitions in the dataset and the number of matches in each."""
        return q.list_competitions(store)

    @mcp.tool()
    def list_seasons(competition: str | None = None) -> dict[str, Any]:
        """All seasons available, optionally filtered by competition."""
        return q.list_seasons(store, competition=competition)

    # ------------------------------------------------------------------
    # Statistical tools
    # ------------------------------------------------------------------
    @mcp.tool()
    def average_goals_per_match(
        competition: str | None = None, season: int | None = None
    ) -> dict[str, Any]:
        """Average goals per match across the filtered slice."""
        return q.average_goals_per_match(store, competition=competition, season=season)

    @mcp.tool()
    def biggest_wins(
        competition: str | None = None, season: int | None = None, limit: int = 10
    ) -> dict[str, Any]:
        """Matches with the biggest winning margins."""
        return q.biggest_wins(store, competition=competition, season=season, limit=limit)

    @mcp.tool()
    def home_away_split(
        competition: str | None = None, season: int | None = None
    ) -> dict[str, Any]:
        """Home-win / away-win / draw rates for the filtered slice."""
        return q.home_away_split(store, competition=competition, season=season)

    @mcp.tool()
    def best_home_records(
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 5,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Teams ranked by home win rate (requires at least ``min_matches`` home games)."""
        return q.best_home_records(
            store,
            competition=competition,
            season=season,
            min_matches=min_matches,
            limit=limit,
        )

    @mcp.tool()
    def best_away_records(
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 5,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Teams ranked by away win rate (requires at least ``min_matches`` away games)."""
        return q.best_away_records(
            store,
            competition=competition,
            season=season,
            min_matches=min_matches,
            limit=limit,
        )

    return mcp, store


def main() -> None:
    """Run the MCP server over stdio."""
    mcp, _ = build_server()
    mcp.run()


if __name__ == "__main__":
    main()
