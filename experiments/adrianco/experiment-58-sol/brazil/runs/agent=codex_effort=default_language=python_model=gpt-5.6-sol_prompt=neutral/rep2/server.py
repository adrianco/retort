"""MCP server exposing the Brazilian soccer knowledge graph."""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from typing import Any

from query_engine import QueryEngine
from soccer_graph import SoccerGraph


@lru_cache(maxsize=1)
def get_graph() -> SoccerGraph:
    return SoccerGraph()


@lru_cache(maxsize=1)
def get_engine() -> QueryEngine:
    return QueryEngine(get_graph())


def search_matches(
    team: str | None = None, opponent: str | None = None,
    start_date: str | None = None, end_date: str | None = None,
    competition: str | None = None, season: int | None = None,
    stage: str | None = None, source: str | None = None, limit: int = 50,
) -> dict[str, Any]:
    """Find matches by team, opponent, dates, competition, season, stage, or source file."""
    matches = get_graph().find_matches(
        team=team, opponent=opponent, start_date=start_date, end_date=end_date,
        competition=competition, season=season, stage=stage, source=source, limit=limit,
    )
    return {"count": len(matches), "matches": [match.to_dict() for match in matches]}


def get_team_statistics(
    team: str, season: int | None = None, competition: str | None = None,
    venue: str = "all",
) -> dict[str, Any]:
    """Calculate a team's record, goals, points, and win rate."""
    return get_graph().team_statistics(team, season=season, competition=competition, venue=venue)


def compare_teams(
    team1: str, team2: str, competition: str | None = None,
    season: int | None = None, limit: int = 100,
) -> dict[str, Any]:
    """Return results and aggregate head-to-head record for two teams."""
    return get_graph().head_to_head(team1, team2, competition=competition, season=season, limit=limit)


def find_players(
    name: str | None = None, nationality: str | None = None,
    club: str | None = None, position: str | None = None,
    min_overall: int | None = None, limit: int = 50,
) -> dict[str, Any]:
    """Search FIFA players by name, nationality, club, position, and rating."""
    players = get_graph().search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, limit=limit,
    )
    return {"count": len(players), "players": [player.to_dict() for player in players]}


def get_standings(season: int, competition: str = "Brasileirão", limit: int = 30) -> dict[str, Any]:
    """Calculate a points table from supplied match results."""
    rows = get_graph().standings(season, competition, limit=limit)
    return {"season": season, "competition": competition, "count": len(rows), "standings": rows}


def get_competition_statistics(
    competition: str | None = None, season: int | None = None,
) -> dict[str, Any]:
    """Calculate goals-per-match and home/away/draw statistics."""
    return get_graph().aggregate_statistics(competition=competition, season=season)


def get_biggest_wins(
    competition: str | None = None, season: int | None = None, limit: int = 10,
) -> dict[str, Any]:
    """Find matches with the largest winning margins."""
    matches = get_graph().biggest_wins(competition=competition, season=season, limit=limit)
    return {"count": len(matches), "matches": matches}


def find_derbies(
    season: int | None = None, competition: str | None = None, limit: int = 100,
) -> dict[str, Any]:
    """Find traditional Brazilian rivalry matches in the supplied data."""
    matches = get_graph().find_derbies(season=season, competition=competition, limit=limit)
    return {"count": len(matches), "matches": matches}


def rank_teams(
    season: int | None = None, competition: str = "Brasileirão",
    venue: str = "all", metric: str = "points", limit: int = 20,
) -> dict[str, Any]:
    """Rank teams by points, wins, win rate, goals, or goal difference."""
    rows = get_graph().rank_teams(
        season=season, competition=competition, venue=venue, metric=metric, limit=limit,
    )
    return {"count": len(rows), "ranking": rows}


def get_club_overview(
    team: str, season: int | None = None, competition: str | None = None,
    player_limit: int = 20,
) -> dict[str, Any]:
    """Combine a club's match record, competitions, and FIFA player records."""
    return get_graph().club_overview(
        team, season=season, competition=competition, player_limit=player_limit,
    )


def ask_soccer(question: str, limit: int = 20) -> dict[str, Any]:
    """Answer a natural-language question using the deterministic soccer query engine."""
    return get_engine().ask(question, limit=limit)


def dataset_summary() -> dict[str, Any]:
    """Describe loaded files, coverage, entities, competitions, and date range."""
    return get_graph().dataset_summary()


def create_mcp_server() -> Any:
    """Create the MCP SDK v2 server and register all tools/resources/prompts."""
    try:
        from mcp.server import MCPServer
    except ImportError as exc:  # Keeps the query core usable without an optional transport install.
        raise RuntimeError("MCP SDK is not installed; run `pip install -e .`") from exc

    mcp_server = MCPServer(
        "Brazilian Soccer Knowledge Graph",
        instructions=(
            "Use these tools to answer questions about the bundled Brazilian soccer match "
            "and FIFA player datasets. Calculated standings describe the supplied data, not "
            "an external official table."
        ),
    )
    for function in (
        search_matches, get_team_statistics, compare_teams, find_players,
        get_standings, get_competition_statistics, get_biggest_wins,
        find_derbies, rank_teams, get_club_overview, ask_soccer, dataset_summary,
    ):
        mcp_server.tool()(function)

    @mcp_server.resource("soccer://dataset/summary")
    def soccer_dataset_summary() -> str:
        """Return a JSON description of the bundled knowledge graph."""
        return json.dumps(dataset_summary(), ensure_ascii=False, indent=2)

    @mcp_server.prompt()
    def analyze_brazilian_soccer(question: str) -> str:
        """Guide an LLM to answer a soccer question with evidence from server tools."""
        return (
            "Answer the following question only from Brazilian Soccer MCP tool results. "
            "State when a result is calculated from incomplete dataset coverage, preserve "
            f"accents in names, and cite match dates when available. Question: {question}"
        )

    return mcp_server


try:
    mcp = create_mcp_server()
except RuntimeError:
    # Importing service functions for unit tests must not require the optional network transport.
    mcp = None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport", choices=("stdio", "streamable-http"), default="stdio",
        help="stdio for local clients; streamable-http for deployment",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    active = mcp or create_mcp_server()
    if args.transport == "streamable-http":
        active.run(transport="streamable-http", host=args.host, port=args.port, stateless_http=True, json_response=True)
    else:
        active.run(transport="stdio")


if __name__ == "__main__":
    main()
