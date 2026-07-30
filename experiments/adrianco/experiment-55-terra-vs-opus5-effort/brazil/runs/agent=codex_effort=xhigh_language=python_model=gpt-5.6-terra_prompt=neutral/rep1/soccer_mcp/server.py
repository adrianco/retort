"""MCP adapter exposing the Brazilian soccer query service as tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .service import SoccerData


def create_mcp_server(data_dir: str | Path | None = None) -> Any:
    """Build the MCP server lazily so service users do not need MCP installed."""
    try:
        from mcp.server.fastmcp import FastMCP
    except (ImportError, ModuleNotFoundError) as error:
        raise RuntimeError(
            "The MCP adapter requires the project dependencies. Run 'pip install -e .'."
        ) from error

    data = SoccerData.load(data_dir)
    server = FastMCP(
        "Brazilian Soccer",
        instructions="Query the bundled Brazilian soccer datasets using the provided tools. Team matching ignores accents and state suffixes.",
    )

    @server.tool()
    def data_summary() -> dict[str, Any]:
        """List all loaded datasets and their record counts."""
        return data.data_summary()

    @server.tool()
    def search_matches(
        team: str | None = None, opponent: str | None = None, competition: str | None = None,
        season: int | None = None, date_from: str | None = None, date_to: str | None = None,
        stage: str | None = None, round: str | None = None, source: str | None = None,
        limit: int = 50, order: str = "desc", include_duplicates: bool = False,
    ) -> dict[str, Any]:
        """Find matches by team, opponent, season, competition, date range, round, stage, or source."""
        return data.search_matches(team, opponent, competition, season, date_from, date_to, stage, round, source, limit, order, include_duplicates)

    @server.tool()
    def team_statistics(
        team: str, season: int | None = None, competition: str | None = None, venue: str = "all",
        source: str | None = None, include_duplicates: bool = False,
    ) -> dict[str, Any]:
        """Calculate a club's win/draw/loss record and goals, optionally by season and venue."""
        return data.team_statistics(team, season, competition, venue, source, include_duplicates)

    @server.tool()
    def head_to_head(
        team_a: str, team_b: str, competition: str | None = None, season: int | None = None,
        source: str | None = None, limit: int = 50, include_duplicates: bool = False,
    ) -> dict[str, Any]:
        """Compare two clubs and return their head-to-head record plus recent matching fixtures."""
        return data.head_to_head(team_a, team_b, competition, season, source, limit, include_duplicates)

    @server.tool()
    def team_overview(
        team: str, season: int | None = None, competition: str | None = None, source: str | None = None,
        match_limit: int = 10, player_limit: int = 20,
    ) -> dict[str, Any]:
        """Return a club's match record, competitions, recent fixtures, and FIFA player records."""
        return data.team_overview(team, season, competition, source, match_limit, player_limit)

    @server.tool()
    def competition_standings(
        competition: str = "Brasileirão", season: int | None = None, source: str | None = None,
        limit: int = 50, include_duplicates: bool = False,
    ) -> dict[str, Any]:
        """Calculate a competition's season standings from completed results."""
        return data.competition_standings(competition, season, source, limit, include_duplicates)

    @server.tool()
    def competition_statistics(
        competition: str | None = None, season: int | None = None, source: str | None = None,
        include_duplicates: bool = False, biggest_wins_limit: int = 10,
    ) -> dict[str, Any]:
        """Calculate goal averages, home/away win rates, biggest wins, and scoring leaders."""
        return data.competition_statistics(competition, season, source, include_duplicates, biggest_wins_limit)

    @server.tool()
    def search_players(
        name: str | None = None, nationality: str | None = None, club: str | None = None,
        position: str | None = None, min_overall: int | None = None, limit: int = 50,
    ) -> dict[str, Any]:
        """Find FIFA players by name, nationality, club, position group, and overall rating."""
        return data.search_players(name, nationality, club, position, min_overall, limit)

    @server.tool()
    def answer_question(question: str, limit: int = 20) -> dict[str, Any]:
        """Answer a supported natural-language soccer question by routing it to a data query."""
        return data.answer_question(question, limit)

    return server


def main() -> None:
    """Run the MCP server over standard input/output."""
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
