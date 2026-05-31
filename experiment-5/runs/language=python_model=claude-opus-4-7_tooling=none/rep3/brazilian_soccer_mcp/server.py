"""MCP server exposing the Brazilian-soccer query layer.

Tools surfaced to MCP clients:

    find_matches              -- search matches by team / opponent / season / competition / date range
    head_to_head              -- aggregate two-team record across all competitions
    team_stats                -- W/D/L/GF/GA for one team, optionally filtered
    compare_teams             -- side-by-side team_stats + head_to_head
    find_players              -- filter the FIFA player table
    top_brazilian_players     -- highest-rated Brazilians
    brazilian_players_by_club -- group Brazilian players by club
    competition_standings     -- computed league table for one season
    biggest_wins              -- largest score margins in the dataset
    overall_stats             -- aggregate goal/win-rate stats
    best_home_record          -- ranked home-record leaders
    best_away_record          -- ranked away-record leaders
    top_scoring_teams         -- ranked goal-scoring leaders
    champion                  -- the season winner
    list_seasons              -- seasons present for a competition
    list_competitions         -- competition labels in the data

The server speaks MCP over stdio.  Tool dispatch is delegated to the
pure-Python `queries` module; the dataset is loaded once at startup.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import queries
from .data_loader import Dataset, load_dataset

logger = logging.getLogger("brazilian_soccer_mcp")


# --------------------------------------------------------------------------- #
# Tool registry
# --------------------------------------------------------------------------- #


def _tool_definitions() -> list[Tool]:
    return [
        Tool(
            name="find_matches",
            description="Search matches by team / opponent / season / competition / date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "opponent": {"type": "string"},
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "date_from": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                    "home_only": {"type": "boolean", "default": False},
                    "away_only": {"type": "boolean", "default": False},
                    "limit": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="head_to_head",
            description="Aggregate W/D/L between two teams across all competitions in the data.",
            inputSchema={
                "type": "object",
                "required": ["team_a", "team_b"],
                "properties": {
                    "team_a": {"type": "string"},
                    "team_b": {"type": "string"},
                },
            },
        ),
        Tool(
            name="team_stats",
            description="Wins/draws/losses/goals/win-rate for one team, optionally filtered by season/competition/venue.",
            inputSchema={
                "type": "object",
                "required": ["team"],
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                    "venue": {"type": "string", "enum": ["home", "away", "all"], "default": "all"},
                },
            },
        ),
        Tool(
            name="compare_teams",
            description="Side-by-side stats for two teams plus their head-to-head record.",
            inputSchema={
                "type": "object",
                "required": ["team_a", "team_b"],
                "properties": {
                    "team_a": {"type": "string"},
                    "team_b": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                },
            },
        ),
        Tool(
            name="find_players",
            description="Filter the FIFA player table by name/nationality/club/position/min overall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string"},
                    "club": {"type": "string"},
                    "position": {"type": "string"},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer", "default": 50},
                },
            },
        ),
        Tool(
            name="top_brazilian_players",
            description="Highest-rated Brazilian players from the FIFA dataset.",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 10}},
            },
        ),
        Tool(
            name="brazilian_players_by_club",
            description="Brazilian players grouped by club with count and average overall rating.",
            inputSchema={
                "type": "object",
                "properties": {"top_n_clubs": {"type": "integer", "default": 10}},
            },
        ),
        Tool(
            name="competition_standings",
            description="Computed league table for one competition and season.",
            inputSchema={
                "type": "object",
                "required": ["competition", "season"],
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="biggest_wins",
            description="Matches with the largest absolute score margin.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="overall_stats",
            description="Aggregate goal totals and home/away/draw rates.",
            inputSchema={
                "type": "object",
                "properties": {"competition": {"type": "string"}},
            },
        ),
        Tool(
            name="best_home_record",
            description="Teams ranked by home-game win rate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "min_matches": {"type": "integer", "default": 5},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="best_away_record",
            description="Teams ranked by away-game win rate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "min_matches": {"type": "integer", "default": 5},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="top_scoring_teams",
            description="Teams ranked by total goals scored.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="champion",
            description="Winner of a competition for a given season (top of computed standings).",
            inputSchema={
                "type": "object",
                "required": ["competition", "season"],
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="list_seasons",
            description="Distinct seasons present in the dataset (optionally for one competition).",
            inputSchema={
                "type": "object",
                "properties": {"competition": {"type": "string"}},
            },
        ),
        Tool(
            name="list_competitions",
            description="Distinct competition labels in the dataset.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


_TOOL_DISPATCH = {
    "find_matches": queries.find_matches,
    "head_to_head": queries.head_to_head,
    "team_stats": queries.team_stats,
    "compare_teams": queries.compare_teams,
    "find_players": queries.find_players,
    "top_brazilian_players": queries.top_brazilian_players,
    "brazilian_players_by_club": queries.brazilian_players_by_club,
    "competition_standings": queries.competition_standings,
    "biggest_wins": queries.biggest_wins,
    "overall_stats": queries.overall_stats,
    "best_home_record": queries.best_home_record,
    "best_away_record": queries.best_away_record,
    "top_scoring_teams": queries.top_scoring_teams,
    "champion": queries.champion,
    "list_seasons": queries.list_seasons,
    "list_competitions": queries.list_competitions,
}


def dispatch_tool(dataset: Dataset, name: str, arguments: dict[str, Any] | None) -> Any:
    """Look up and invoke a query tool against the loaded dataset."""
    fn = _TOOL_DISPATCH.get(name)
    if fn is None:
        raise ValueError(f"unknown tool: {name}")
    return fn(dataset, **(arguments or {}))


# --------------------------------------------------------------------------- #
# Server construction
# --------------------------------------------------------------------------- #


def build_server(dataset: Dataset | None = None) -> tuple[Server, Dataset]:
    """Return a configured Server plus the dataset it serves."""
    if dataset is None:
        dataset = load_dataset()
    server: Server = Server(
        "brazilian-soccer-mcp",
        version="1.0.0",
        instructions=(
            "Knowledge-graph-style query interface over six Kaggle Brazilian-soccer "
            "datasets (Brasileirão, Copa do Brasil, Libertadores, extended match stats, "
            "historical Brasileirão 2003-2019, and the FIFA player database). "
            "Use the tools to look up matches, teams, players, competitions, and stats."
        ),
    )

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return _tool_definitions()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        try:
            result = dispatch_tool(dataset, name, arguments)
            payload = json.dumps(result, ensure_ascii=False, indent=2, default=str)
            return [TextContent(type="text", text=payload)]
        except Exception as exc:  # surface to client cleanly
            logger.exception("tool %s failed", name)
            return [TextContent(type="text", text=f"error: {exc}")]

    return server, dataset


async def run_async() -> None:
    server, _ = build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    """Synchronous entrypoint -- runs the MCP server over stdio."""
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_async())


if __name__ == "__main__":
    main()
