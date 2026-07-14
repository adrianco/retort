"""
Brazilian Soccer MCP Server

Exposes five tools over the Model Context Protocol (stdio transport):
  find_matches     – search matches by team, competition, season, date
  get_team_stats   – win/draw/loss and goal statistics for a team
  find_players     – search FIFA player database
  get_standings    – league table calculated from match results
  get_statistics   – aggregate analysis (biggest wins, avg goals, home record)
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import mcp.types as types
from mcp.server import Server

from data_loader import DataLoader


def build_server(data_dir: str) -> Server:
    """Construct and return a configured MCP Server instance."""
    loader = DataLoader(data_dir)
    app = Server("brazilian-soccer-mcp")

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="find_matches",
                description=(
                    "Search Brazilian soccer matches across Brasileirão, Copa do Brasil, "
                    "and Copa Libertadores. Filter by team, opponent (head-to-head), "
                    "competition, season, or date range."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name (partial match)"},
                        "opponent": {"type": "string", "description": "Opponent team for head-to-head"},
                        "competition": {
                            "type": "string",
                            "description": "brasileirao | copa_do_brasil | libertadores",
                        },
                        "season": {"type": "integer", "description": "Season year (e.g. 2023)"},
                        "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
                        "date_to": {"type": "string", "description": "End date YYYY-MM-DD"},
                        "limit": {"type": "integer", "description": "Max results (default 50)"},
                    },
                },
            ),
            types.Tool(
                name="get_team_stats",
                description=(
                    "Return win/draw/loss record and goal statistics for a team, "
                    "optionally filtered by competition and/or season."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name"},
                        "competition": {"type": "string", "description": "Competition filter"},
                        "season": {"type": "integer", "description": "Season year filter"},
                    },
                    "required": ["team"],
                },
            ),
            types.Tool(
                name="find_players",
                description=(
                    "Search the FIFA player database by name, nationality, club, "
                    "position, or minimum overall rating. Results sorted by rating."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Player name (partial match)"},
                        "nationality": {"type": "string", "description": "Nationality (e.g. Brazil)"},
                        "club": {"type": "string", "description": "Club name (partial match)"},
                        "position": {"type": "string", "description": "Playing position (e.g. ST, GK)"},
                        "min_rating": {"type": "integer", "description": "Minimum overall rating"},
                        "limit": {"type": "integer", "description": "Max results (default 20)"},
                    },
                },
            ),
            types.Tool(
                name="get_standings",
                description=(
                    "Calculate competition standings table for a given season, "
                    "sorted by points. Teams earn 3 pts for a win, 1 for a draw."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "season": {"type": "integer", "description": "Season year (e.g. 2019)"},
                        "competition": {
                            "type": "string",
                            "description": "brasileirao (default) | copa_do_brasil | libertadores",
                        },
                    },
                    "required": ["season"],
                },
            ),
            types.Tool(
                name="get_statistics",
                description=(
                    "Compute aggregate statistics across matches. "
                    "stat_type must be one of: biggest_wins | avg_goals | home_record"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stat_type": {
                            "type": "string",
                            "description": "biggest_wins | avg_goals | home_record",
                        },
                        "competition": {"type": "string", "description": "Competition filter"},
                        "season": {"type": "integer", "description": "Season filter"},
                        "limit": {"type": "integer", "description": "Max results (default 10)"},
                    },
                    "required": ["stat_type"],
                },
            ),
        ]

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.Content]:
        dispatch = {
            "find_matches": loader.find_matches,
            "get_team_stats": loader.get_team_stats,
            "find_players": loader.find_players,
            "get_standings": loader.get_standings,
            "get_statistics": loader.get_statistics,
        }
        if name not in dispatch:
            raise ValueError(f"Unknown tool: {name}")

        result = dispatch[name](**arguments)
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    return app


async def _serve(data_dir: str) -> None:
    from mcp.server.stdio import stdio_server

    server = build_server(data_dir)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    data_dir = os.environ.get("DATA_DIR", "data/kaggle")
    asyncio.run(_serve(data_dir))
