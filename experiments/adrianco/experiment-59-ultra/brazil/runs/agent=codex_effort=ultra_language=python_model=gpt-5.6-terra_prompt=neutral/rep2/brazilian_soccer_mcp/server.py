"""MCP transport adapter for :mod:`brazilian_soccer_mcp.service`.

Run with ``python -m brazilian_soccer_mcp`` or the
``brazilian-soccer-mcp`` console script.  The default stdio transport keeps
stdout reserved for MCP protocol messages.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Callable

from .fallback_mcp import FallbackMCP
from .service import SoccerQueryService


SERVER_INSTRUCTIONS = """You are a Brazilian soccer dataset assistant.
Use the structured tools for match, team, player, competition, and statistical
questions. Results are derived only from bundled CSV snapshots, not live data.
Keep source provenance and caveats in responses: FIFA club values are snapshots,
top-scorer events are unavailable, and calculated league tables use a documented
single-source-per-competition-season policy to avoid overlap double-counting.
"""


def create_server(
    data_directory: str | Path | None = None,
    *,
    mcp_factory: Callable[..., Any] | None = None,
) -> Any:
    """Build a FastMCP server and register its data-backed tools.

    ``mcp_factory`` is an intentionally small injection point for transport-free
    unit tests; production callers should leave it unset.
    """

    if mcp_factory is None:
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:  # pragma: no cover - depends on local environment
            # This preserves a working stdio MCP server when a host's global
            # mcp/Pydantic installation is inconsistent. A clean environment
            # still uses the official SDK above.
            mcp_factory = FallbackMCP
        else:
            mcp_factory = FastMCP

    directory = data_directory or os.environ.get("BRAZILIAN_SOCCER_DATA_DIR")
    service = SoccerQueryService.from_data_directory(directory)
    mcp = mcp_factory(
        "Brazilian Soccer Knowledge Graph",
        instructions=SERVER_INSTRUCTIONS,
    )

    @mcp.tool(
        name="data_summary",
        description="Describe the loaded CSV datasets, coverage, source files, and licenses.",
    )
    def data_summary() -> dict[str, Any]:
        return service.data_summary()

    @mcp.tool(
        name="knowledge_graph",
        description=(
            "Return a compact graph subgraph for a team or player: teams connect to matches, "
            "competitions, seasons, and opponents; players connect to FIFA club snapshots."
        ),
    )
    def knowledge_graph(
        entity_type: str,
        name: str,
        season: int | None = None,
        competition: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        return service.entity_graph(
            entity_type,
            name,
            season=season,
            competition=competition,
            limit=limit,
        )

    @mcp.tool(
        name="search_matches",
        description=(
            "Find match rows by team, opponent, season, competition, inclusive date range, "
            "home/away venue, round, stage, or source. Returns source provenance and formatted text."
        ),
    )
    def search_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        venue: str = "any",
        round_contains: str | None = None,
        stage_contains: str | None = None,
        source: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        return service.search_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            start_date=start_date,
            end_date=end_date,
            venue=venue,
            round_contains=round_contains,
            stage_contains=stage_contains,
            source=source,
            limit=limit,
        )

    @mcp.tool(
        name="team_statistics",
        description="Calculate a team's W/D/L, goals, points, and win rate for a selected scope.",
    )
    def team_statistics(
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str = "any",
        source: str | None = None,
    ) -> dict[str, Any]:
        return service.team_statistics(
            team,
            season=season,
            competition=competition,
            venue=venue,
            source=source,
        )

    @mcp.tool(
        name="compare_teams",
        description="Calculate orientation-independent head-to-head records for two teams.",
    )
    def compare_teams(
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
        source: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        return service.compare_teams(
            team_a,
            team_b,
            competition=competition,
            season=season,
            source=source,
            limit=limit,
        )

    @mcp.tool(
        name="search_players",
        description=(
            "Search FIFA player snapshots by name, nationality, club, position, and rating bounds. "
            "Club values are not historical lineups."
        ),
    )
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        return service.search_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
            limit=limit,
        )

    @mcp.tool(
        name="compare_players",
        description="Compare two player searches using FIFA ratings and available skill attributes.",
    )
    def compare_players(player_a: str, player_b: str) -> dict[str, Any]:
        return service.compare_players(player_a, player_b)

    @mcp.tool(
        name="competition_standings",
        description=(
            "Calculate a season standings table using 3 points for a win and 1 for a draw. "
            "The response documents tie breakers and coverage caveats."
        ),
    )
    def competition_standings(
        season: int,
        competition: str = "Brasileirão",
        source: str | None = None,
    ) -> dict[str, Any]:
        return service.competition_standings(
            season, competition=competition, source=source
        )

    @mcp.tool(
        name="competition_statistics",
        description="Calculate goals per match, home/away rates, draws, and largest winning margins.",
    )
    def competition_statistics(
        competition: str | None = None,
        season: int | None = None,
        source: str | None = None,
        biggest_wins_limit: int = 10,
    ) -> dict[str, Any]:
        return service.competition_statistics(
            competition=competition,
            season=season,
            source=source,
            biggest_wins_limit=biggest_wins_limit,
        )

    @mcp.tool(
        name="best_team_record",
        description="Rank teams by points per match, with documented deterministic tie breakers.",
    )
    def best_team_record(
        venue: str = "any",
        competition: str | None = None,
        season: int | None = None,
        source: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return service.best_team_record(
            venue=venue,
            competition=competition,
            season=season,
            source=source,
            limit=limit,
        )

    @mcp.tool(
        name="libertadores_by_stage",
        description="Group loaded Copa Libertadores match rows by their supplied stage values without inventing brackets.",
    )
    def libertadores_by_stage(season: int, limit_per_stage: int = 100) -> dict[str, Any]:
        return service.libertadores_by_stage(season, limit_per_stage=limit_per_stage)

    @mcp.tool(
        name="team_competitions",
        description="List the competitions where a team appears in loaded match rows.",
    )
    def team_competitions(team: str, source: str | None = None) -> dict[str, Any]:
        return service.team_competitions(team, source=source)

    @mcp.tool(
        name="derby_matches",
        description="Find matches in the server's explicit, curated traditional-rivalry mapping.",
    )
    def derby_matches(season: int | None = None, limit: int = 25) -> dict[str, Any]:
        return service.derby_matches(season=season, limit=limit)

    @mcp.tool(
        name="teams_by_goals",
        description="Rank teams by total goals in the selected competition and season scope.",
    )
    def teams_by_goals(
        competition: str | None = None, season: int | None = None, limit: int = 10
    ) -> dict[str, Any]:
        return service.teams_by_goals(competition=competition, season=season, limit=limit)

    @mcp.tool(
        name="compare_seasons",
        description="Compare aggregate goals and home/away results across two seasons.",
    )
    def compare_seasons(
        first_season: int, second_season: int, competition: str = "Brasileirão"
    ) -> dict[str, Any]:
        return service.compare_seasons(
            first_season, second_season, competition=competition
        )

    @mcp.tool(
        name="players_at_clubs_faced",
        description=(
            "Join a team's match opponents to FIFA club snapshots. The response explicitly states "
            "that this is not a historical lineup claim."
        ),
    )
    def players_at_clubs_faced(team: str, season: int, limit: int = 25) -> dict[str, Any]:
        return service.players_at_clubs_faced(team, season, limit=limit)

    @mcp.tool(
        name="top_scorers_status",
        description="Explain truthfully why individual scorer rankings cannot be calculated from the supplied schemas.",
    )
    def top_scorers_status(
        competition: str | None = None, season: int | None = None
    ) -> dict[str, Any]:
        return service.top_scorers_status(competition=competition, season=season)

    @mcp.tool(
        name="ask_brazilian_soccer",
        description=(
            "Convenience natural-language router for common soccer questions. For a follow-up like "
            "'What was the score?', pass the preceding match as context.last_match."
        ),
    )
    def ask_brazilian_soccer(
        question: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return service.answer_question(question, context=context)

    @mcp.resource(
        "soccer://datasets",
        name="Bundled Brazilian soccer datasets",
        description="Machine-readable dataset coverage and provenance for this MCP server.",
        mime_type="application/json",
    )
    def dataset_resource() -> dict[str, Any]:
        return service.data_summary()

    return mcp


def main(argv: list[str] | None = None) -> None:
    """Run the server using stdio by default, with opt-in network transports."""

    parser = argparse.ArgumentParser(description="Brazilian soccer MCP server")
    parser.add_argument(
        "--data-dir",
        help="Directory containing the six bundled CSV files (or BRAZILIAN_SOCCER_DATA_DIR).",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="MCP transport; stdio is the default for LLM integrations.",
    )
    arguments = parser.parse_args(argv)
    create_server(arguments.data_dir).run(transport=arguments.transport)


if __name__ == "__main__":  # pragma: no cover - exercised by console entry point
    main()
