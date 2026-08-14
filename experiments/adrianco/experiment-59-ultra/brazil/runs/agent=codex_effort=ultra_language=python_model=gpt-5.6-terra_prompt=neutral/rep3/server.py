"""MCP entry point for the offline Brazilian soccer knowledge graph.

The domain layer is intentionally importable without the MCP SDK.  This module
defers data loading until a tool is called and gives a clear install message if
the optional runtime dependency is unavailable.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from soccer_knowledge_graph import SoccerKnowledgeGraph

try:  # Keep tests and the query layer usable in minimal Python environments.
    from mcp.server.fastmcp import FastMCP
except ImportError as error:  # pragma: no cover - depends on the host environment
    FastMCP = None  # type: ignore[assignment,misc]
    _MCP_IMPORT_ERROR: ImportError | None = error
else:
    _MCP_IMPORT_ERROR = None


_graph: SoccerKnowledgeGraph | None = None


def get_graph(data_dir: str | Path | None = None) -> SoccerKnowledgeGraph:
    """Return the lazily-loaded graph; optionally use a supplied data directory."""

    global _graph
    if data_dir is not None:
        return SoccerKnowledgeGraph(data_dir)
    if _graph is None:
        _graph = SoccerKnowledgeGraph()
    return _graph


def list_available_data() -> dict[str, object]:
    """List source coverage, load counts, and dataset-mode semantics."""

    return get_graph().list_available_data()


def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    stage: str | None = None,
    round: str | None = None,
    source: str | None = None,
    dataset_mode: str = "canonical",
    limit: int = 25,
) -> dict[str, object]:
    """Search local match data by team, venue, competition, date, season, or source."""

    return get_graph().search_matches(
        team=team,
        opponent=opponent,
        home_team=home_team,
        away_team=away_team,
        competition=competition,
        season=season,
        start_date=start_date,
        end_date=end_date,
        stage=stage,
        round=round,
        source=source,
        dataset_mode=dataset_mode,
        limit=limit,
    )


def get_team_statistics(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
    dataset_mode: str = "canonical",
) -> dict[str, object]:
    """Calculate a club's match, W/D/L, goals, points, and win-rate record."""

    return get_graph().get_team_statistics(
        team, season=season, competition=competition, venue=venue, dataset_mode=dataset_mode
    )


def compare_teams(
    team_a: str,
    team_b: str,
    season: int | None = None,
    competition: str | None = None,
    dataset_mode: str = "canonical",
    limit: int = 25,
) -> dict[str, object]:
    """Compare two clubs head-to-head and return their most recent fixtures."""

    return get_graph().compare_teams(
        team_a,
        team_b,
        season=season,
        competition=competition,
        dataset_mode=dataset_mode,
        limit=limit,
    )


def search_players(
    query: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
    include_attributes: bool = False,
) -> dict[str, object]:
    """Search the bundled FIFA player snapshot by name, club, nationality, or rating."""

    return get_graph().search_players(
        query=query,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
        include_attributes=include_attributes,
    )


def get_standings(
    season: int,
    competition: str = "Brasileirão",
    dataset_mode: str = "canonical",
) -> dict[str, object]:
    """Calculate table standings from the local completed fixture results."""

    return get_graph().get_standings(season, competition=competition, dataset_mode=dataset_mode)


def get_competition_statistics(
    competition: str | None = None,
    season: int | None = None,
    dataset_mode: str = "canonical",
) -> dict[str, object]:
    """Calculate goal averages and home/draw/away result rates."""

    return get_graph().get_competition_statistics(
        competition=competition, season=season, dataset_mode=dataset_mode
    )


def get_competition_bracket(
    season: int,
    competition: str = "Libertadores",
    dataset_mode: str = "canonical",
) -> dict[str, object]:
    """Group a cup competition's season fixtures into stage/round brackets."""

    return get_graph().get_competition_bracket(
        season, competition=competition, dataset_mode=dataset_mode
    )


def get_relegated_teams(
    season: int,
    competition: str = "Brasileirão",
    bottom: int = 4,
    dataset_mode: str = "canonical",
) -> dict[str, object]:
    """Return bottom calculated table positions from the bundled match results."""

    return get_graph().get_relegated_teams(
        season, competition=competition, bottom=bottom, dataset_mode=dataset_mode
    )


def get_best_team_record(
    venue: str = "home",
    competition: str | None = None,
    season: int | None = None,
    dataset_mode: str = "canonical",
    limit: int = 10,
) -> dict[str, object]:
    """Rank teams by their home, away, or overall record."""

    return get_graph().get_best_team_record(
        venue=venue,
        competition=competition,
        season=season,
        dataset_mode=dataset_mode,
        limit=limit,
    )


def get_biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    dataset_mode: str = "canonical",
    limit: int = 10,
) -> dict[str, object]:
    """Return completed fixtures ordered by their winning margin."""

    return get_graph().get_biggest_wins(
        competition=competition, season=season, dataset_mode=dataset_mode, limit=limit
    )


def get_team_competitions(team: str, dataset_mode: str = "canonical") -> dict[str, object]:
    """List the competitions in which a team appears."""

    return get_graph().get_team_competitions(team, dataset_mode=dataset_mode)


def search_derbies(
    season: int | None = None,
    competition: str | None = None,
    dataset_mode: str = "canonical",
    limit: int = 25,
) -> dict[str, object]:
    """Find known traditional derbies represented in the match data."""

    return get_graph().search_derbies(
        season=season, competition=competition, dataset_mode=dataset_mode, limit=limit
    )


def get_entity_relationships(
    entity: str,
    entity_type: str = "team",
    dataset_mode: str = "canonical",
    limit: int = 25,
) -> dict[str, object]:
    """Inspect team/player graph relationships such as opponents and competitions."""

    return get_graph().get_entity_relationships(
        entity, entity_type=entity_type, dataset_mode=dataset_mode, limit=limit
    )


def ask_soccer(question: str, limit: int = 10, dataset_mode: str = "canonical") -> dict[str, object]:
    """Answer a common natural-language Brazilian soccer question from local data."""

    return get_graph().ask_soccer(question, limit=limit, dataset_mode=dataset_mode)


TOOL_FUNCTIONS = (
    list_available_data,
    search_matches,
    get_team_statistics,
    compare_teams,
    search_players,
    get_standings,
    get_competition_statistics,
    get_competition_bracket,
    get_relegated_teams,
    get_best_team_record,
    get_biggest_wins,
    get_team_competitions,
    search_derbies,
    get_entity_relationships,
    ask_soccer,
)


def create_mcp_server() -> Any:
    """Create a FastMCP server without eagerly reading the CSV files."""

    if FastMCP is None:
        detail = f" ({_MCP_IMPORT_ERROR})" if _MCP_IMPORT_ERROR else ""
        raise RuntimeError(
            "The MCP runtime is unavailable. Install project dependencies with "
            "`python -m pip install -r requirements.txt` before starting the server." + detail
        )
    server = FastMCP(
        "Brazilian Soccer Knowledge Graph",
        instructions=(
            "Offline Brazilian soccer data from the six bundled CSV datasets. "
            "Use structured tools for exact results and ask_soccer for common natural-language queries."
        ),
    )
    for function in TOOL_FUNCTIONS:
        server.tool()(function)
    return server


try:  # Do not make importing the query functions depend on the MCP SDK.
    mcp = create_mcp_server() if FastMCP is not None else None
except Exception:  # pragma: no cover - protects direct data-service use from SDK drift
    mcp = None


def main() -> int:
    """Run the MCP server over stdio for a desktop MCP client."""

    if mcp is None:
        print(
            "MCP runtime unavailable. Install dependencies with: python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by an MCP client
    raise SystemExit(main())
