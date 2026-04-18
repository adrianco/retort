"""MCP server exposing Brazilian soccer data tools."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import pandas as pd

from .data_loader import load_all
from .query import QueryEngine


def _df_to_records(df: pd.DataFrame, max_rows: int = 50) -> list[dict]:
    if df is None or df.empty:
        return []
    out = df.head(max_rows).copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
    return json.loads(out.to_json(orient="records", date_format="iso"))


def _format_result(result: Any) -> str:
    if isinstance(result, pd.DataFrame):
        return json.dumps(_df_to_records(result), ensure_ascii=False, indent=2)
    if isinstance(result, dict):
        clean = {}
        for k, v in result.items():
            if isinstance(v, pd.DataFrame):
                clean[k] = _df_to_records(v)
            else:
                clean[k] = v
        return json.dumps(clean, ensure_ascii=False, indent=2, default=str)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


TOOL_DEFS = [
    {
        "name": "find_matches",
        "description": "Find matches filtered by team, opponent, competition, season or date range.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "opponent": {"type": "string"},
                "competition": {"type": "string"},
                "season": {"type": "integer"},
                "date_from": {"type": "string"},
                "date_to": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    },
    {
        "name": "head_to_head",
        "description": "Head-to-head record between two teams across all competitions.",
        "inputSchema": {
            "type": "object",
            "required": ["team_a", "team_b"],
            "properties": {
                "team_a": {"type": "string"},
                "team_b": {"type": "string"},
            },
        },
    },
    {
        "name": "team_record",
        "description": "Compute a team's record (W/D/L, goals, points).",
        "inputSchema": {
            "type": "object",
            "required": ["team"],
            "properties": {
                "team": {"type": "string"},
                "season": {"type": "integer"},
                "competition": {"type": "string"},
                "home_only": {"type": "boolean", "default": False},
                "away_only": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "standings",
        "description": "Final standings for a competition/season computed from match data.",
        "inputSchema": {
            "type": "object",
            "required": ["competition", "season"],
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "integer"},
            },
        },
    },
    {
        "name": "find_players",
        "description": "Search FIFA player database by name, nationality, club, position, rating.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "nationality": {"type": "string"},
                "club": {"type": "string"},
                "position": {"type": "string"},
                "min_overall": {"type": "integer"},
                "limit": {"type": "integer", "default": 25},
            },
        },
    },
    {
        "name": "biggest_wins",
        "description": "Biggest victories by goal margin, optionally filtered by competition.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "average_goals",
        "description": "Average goals per match and home win rate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "integer"},
            },
        },
    },
    {
        "name": "top_scoring_teams",
        "description": "Teams with most goals scored in a given competition/season.",
        "inputSchema": {
            "type": "object",
            "required": ["competition", "season"],
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "integer"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "dataset_summary",
        "description": "Return row counts for each loaded dataset.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def dispatch(engine: QueryEngine, name: str, args: dict) -> Any:
    args = dict(args or {})
    if name == "find_matches":
        return engine.find_matches(**args)
    if name == "head_to_head":
        return engine.head_to_head(**args)
    if name == "team_record":
        return engine.team_record(**args)
    if name == "standings":
        return engine.standings(**args)
    if name == "find_players":
        return engine.find_players(**args)
    if name == "biggest_wins":
        return engine.biggest_wins(**args)
    if name == "average_goals":
        return engine.average_goals(**args)
    if name == "top_scoring_teams":
        return engine.top_scoring_teams(**args)
    if name == "dataset_summary":
        return engine.data.summary()
    raise ValueError(f"Unknown tool: {name}")


def build_server(engine: QueryEngine):
    from mcp.server import Server
    import mcp.types as types

    server = Server("brazilian-soccer")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(name=t["name"], description=t["description"],
                       inputSchema=t["inputSchema"])
            for t in TOOL_DEFS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        try:
            result = dispatch(engine, name, arguments or {})
            text = _format_result(result)
        except Exception as e:
            text = json.dumps({"error": str(e), "tool": name, "arguments": arguments})
        return [types.TextContent(type="text", text=text)]

    return server


async def _run() -> None:
    from mcp.server.stdio import stdio_server
    engine = QueryEngine(load_all())
    server = build_server(engine)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
