"""MCP server entry point.

Exposes the :class:`SoccerQueries` API as MCP tools over stdio. Each tool
returns a JSON-serialised text payload so any LLM client can parse the
results.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .data_loader import DataStore, load_all
from .queries import SoccerQueries


def _tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="summary",
            description="Return dataset summary: total matches, players, competitions, source files.",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        types.Tool(
            name="list_competitions",
            description="List all available competitions in the dataset.",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        types.Tool(
            name="list_seasons",
            description="List all seasons available, optionally filtered by competition.",
            inputSchema={
                "type": "object",
                "properties": {"competition": {"type": "string"}},
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="list_teams",
            description="List all team names appearing in matches, optionally filtered.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                },
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="find_matches",
            description="Find matches by team, opponent, competition, season, or date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Primary team filter (home, away, or either)"},
                    "opponent": {"type": "string", "description": "Opposing team (used with team)"},
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD"},
                    "home_only": {"type": "boolean"},
                    "away_only": {"type": "boolean"},
                    "limit": {"type": "integer", "default": 50},
                },
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="head_to_head",
            description="Head-to-head record between two teams across all competitions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_a": {"type": "string"},
                    "team_b": {"type": "string"},
                    "season": {"type": "integer"},
                },
                "required": ["team_a", "team_b"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="team_stats",
            description="Aggregate W/D/L/goal stats for a team. Optionally filter by season, competition, or venue (home/away).",
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"},
                    "competition": {"type": "string"},
                    "venue": {"type": "string", "enum": ["home", "away", "all"]},
                },
                "required": ["team"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="standings",
            description="Compute a final league table from match results for a competition/season.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                },
                "required": ["competition", "season"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="find_players",
            description="Search FIFA player data by name, nationality, club, position, and minimum rating.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "nationality": {"type": "string"},
                    "club": {"type": "string"},
                    "position": {"type": "string"},
                    "min_overall": {"type": "integer"},
                    "limit": {"type": "integer", "default": 25},
                },
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="top_brazilian_players",
            description="Top-rated Brazilian players sorted by FIFA overall rating.",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 10}},
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="biggest_wins",
            description="Largest goal margins, optionally filtered by competition and season.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                    "limit": {"type": "integer", "default": 10},
                },
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="average_goals_per_match",
            description="Average goals per match plus home/away/draw rates for the filtered subset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {"type": "string"},
                    "season": {"type": "integer"},
                },
                "additionalProperties": False,
            },
        ),
    ]


def _dispatch(q: SoccerQueries, name: str, args: dict[str, Any]) -> Any:
    if name == "summary":
        return q.summary()
    if name == "list_competitions":
        return q.list_competitions()
    if name == "list_seasons":
        return q.list_seasons(args.get("competition"))
    if name == "list_teams":
        return q.list_teams(args.get("competition"), args.get("season"))
    if name == "find_matches":
        venue_args = args.copy()
        return q.find_matches(**venue_args)
    if name == "head_to_head":
        return q.head_to_head(**args)
    if name == "team_stats":
        venue = args.get("venue")
        if venue == "all":
            venue = None
        return q.team_stats(
            team=args["team"],
            season=args.get("season"),
            competition=args.get("competition"),
            venue=venue,
        )
    if name == "standings":
        return q.standings(args["competition"], args["season"])
    if name == "find_players":
        return q.find_players(**args)
    if name == "top_brazilian_players":
        return q.top_brazilian_players(args.get("limit", 10))
    if name == "biggest_wins":
        return q.biggest_wins(**args)
    if name == "average_goals_per_match":
        return q.average_goals_per_match(**args)
    raise ValueError(f"Unknown tool: {name}")


def build_server(store: DataStore | None = None) -> Server:
    store = store or load_all(os.environ.get("BSMCP_DATA_DIR"))
    queries = SoccerQueries(store)
    server: Server = Server("brazilian-soccer-mcp")

    @server.list_tools()
    async def _list() -> list[types.Tool]:
        return _tools()

    @server.call_tool()
    async def _call(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
        args = arguments or {}
        try:
            result = _dispatch(queries, name, args)
        except Exception as exc:  # surface errors as readable text
            payload = {"error": str(exc), "tool": name, "arguments": args}
            return [types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, indent=2))]
        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2, default=str),
            )
        ]

    return server


async def _run() -> None:
    server = build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
