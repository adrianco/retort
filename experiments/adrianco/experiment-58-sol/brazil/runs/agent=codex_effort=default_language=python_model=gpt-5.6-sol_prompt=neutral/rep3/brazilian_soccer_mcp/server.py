"""MCP stdio adapter for the Brazilian soccer query service.

This module deliberately uses the SDK's low-level ``Server`` API.  FastMCP's
import path changed between MCP Python SDK generations, while the protocol
handlers used here (tools/list, tools/call, resources/list, resources/read)
remain available in both supported generations.
"""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from typing import Any, Callable

import mcp.server.stdio as mcp_stdio
import mcp.types as types
from mcp.server.models import InitializationOptions

try:  # MCP Python SDK 2.x
    from mcp.server.lowlevel import NotificationOptions, Server
except ImportError:  # MCP Python SDK 1.x
    from mcp.server import NotificationOptions, Server

from .query import NaturalLanguageQuery
from .service import SoccerService


SERVER_NAME = "brazilian-soccer-knowledge-graph"
SERVER_VERSION = "1.0.0"
DATASET_URI = "soccer://datasets"


def _object_schema(
    properties: dict[str, dict[str, Any]], required: tuple[str, ...] = ()
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = list(required)
    return schema


STRING = {"type": "string"}
NULLABLE_STRING = {"type": ["string", "null"], "default": None}
NULLABLE_INTEGER = {"type": ["integer", "null"], "default": None}
LIMIT = {"type": "integer", "minimum": 1, "maximum": 200, "default": 25}
OFFSET = {"type": "integer", "minimum": 0, "default": 0}


# Keeping the definitions as data makes the advertised protocol contract easy
# to test without loading all 42,061 dataset rows.
TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "ask_soccer",
        "description": "Route a natural-language soccer question to deterministic analytics.",
        "inputSchema": _object_schema(
            {"question": STRING, "limit": {**LIMIT, "default": 20}}, ("question",)
        ),
    },
    {
        "name": "search_matches",
        "description": "Find scored matches by team, opponent, season, competition, dates, venue side, stage, or source.",
        "inputSchema": _object_schema(
            {
                "team": NULLABLE_STRING,
                "opponent": NULLABLE_STRING,
                "season": NULLABLE_INTEGER,
                "competition": NULLABLE_STRING,
                "start_date": NULLABLE_STRING,
                "end_date": NULLABLE_STRING,
                "side": {"type": "string", "enum": ["home", "away", "either"], "default": "either"},
                "stage": NULLABLE_STRING,
                "source": NULLABLE_STRING,
                "deduplicate": {"type": "boolean", "default": True},
                "limit": LIMIT,
                "offset": OFFSET,
            }
        ),
    },
    {
        "name": "team_statistics",
        "description": "Calculate wins, draws, losses, goals, points, and win rate for a team.",
        "inputSchema": _object_schema(
            {
                "team": STRING,
                "season": NULLABLE_INTEGER,
                "competition": NULLABLE_STRING,
                "side": {"type": "string", "enum": ["home", "away", "either"], "default": "either"},
            },
            ("team",),
        ),
    },
    {
        "name": "head_to_head",
        "description": "Compare two teams and return their W/D/L record plus recent meetings.",
        "inputSchema": _object_schema(
            {
                "team1": STRING,
                "team2": STRING,
                "season": NULLABLE_INTEGER,
                "competition": NULLABLE_STRING,
                "limit": LIMIT,
            },
            ("team1", "team2"),
        ),
    },
    {
        "name": "search_players",
        "description": "Search FIFA players by name, nationality, club, position family, and rating.",
        "inputSchema": _object_schema(
            {
                "name": NULLABLE_STRING,
                "nationality": NULLABLE_STRING,
                "club": NULLABLE_STRING,
                "position": NULLABLE_STRING,
                "min_overall": NULLABLE_INTEGER,
                "sort_by": {"type": "string", "enum": ["overall", "potential", "age", "name"], "default": "overall"},
                "limit": LIMIT,
                "offset": OFFSET,
            }
        ),
    },
    {
        "name": "standings",
        "description": "Calculate season standings from one canonical match source.",
        "inputSchema": _object_schema(
            {
                "season": {"type": "integer"},
                "competition": {"type": "string", "default": "Brasileirão Série A"},
                "limit": {**LIMIT, "default": 30},
            },
            ("season",),
        ),
    },
    {
        "name": "competition_statistics",
        "description": "Calculate goals per match and home-win, away-win, and draw rates.",
        "inputSchema": _object_schema(
            {"competition": NULLABLE_STRING, "season": NULLABLE_INTEGER}
        ),
    },
    {
        "name": "biggest_victories",
        "description": "Return matches ranked by winning margin.",
        "inputSchema": _object_schema(
            {"competition": NULLABLE_STRING, "season": NULLABLE_INTEGER, "limit": {**LIMIT, "default": 10}}
        ),
    },
    {
        "name": "best_record",
        "description": "Rank teams by home or away win rate.",
        "inputSchema": _object_schema(
            {
                "side": {"type": "string", "enum": ["home", "away"]},
                "season": NULLABLE_INTEGER,
                "competition": NULLABLE_STRING,
                "min_matches": {"type": "integer", "minimum": 1, "default": 5},
                "limit": {**LIMIT, "default": 10},
            },
            ("side",),
        ),
    },
    {
        "name": "team_competitions",
        "description": "List competitions in which a team appears.",
        "inputSchema": _object_schema(
            {"team": STRING, "season": NULLABLE_INTEGER}, ("team",)
        ),
    },
    {
        "name": "derby_matches",
        "description": "Find known Brazilian derby matches.",
        "inputSchema": _object_schema(
            {"season": NULLABLE_INTEGER, "limit": {**LIMIT, "default": 100}}
        ),
    },
    {
        "name": "competition_finals",
        "description": "Find labeled finals or infer Copa do Brasil final legs from the highest round.",
        "inputSchema": _object_schema(
            {"competition": STRING, "season": NULLABLE_INTEGER, "limit": {**LIMIT, "default": 100}},
            ("competition",),
        ),
    },
    {
        "name": "club_profile",
        "description": "Join a team's match statistics, competitions, and FIFA player records.",
        "inputSchema": _object_schema(
            {
                "team": STRING,
                "season": NULLABLE_INTEGER,
                "competition": NULLABLE_STRING,
                "player_limit": LIMIT,
            },
            ("team",),
        ),
    },
    {
        "name": "compare_seasons",
        "description": "Compare aggregate scoring and outcomes across two seasons.",
        "inputSchema": _object_schema(
            {
                "season1": {"type": "integer"},
                "season2": {"type": "integer"},
                "competition": {"type": "string", "default": "Brasileirão Série A"},
            },
            ("season1", "season2"),
        ),
    },
    {
        "name": "dataset_status",
        "description": "Report load status and row counts for every required CSV file.",
        "inputSchema": _object_schema({}),
    },
)


@lru_cache(maxsize=1)
def get_service() -> SoccerService:
    """Load the bundled CSV repository once per server process."""
    return SoccerService()


def dispatch_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    service: SoccerService | None = None,
) -> dict[str, Any]:
    """Dispatch one validated MCP tool name to the deterministic service."""
    soccer = service or get_service()
    kwargs = dict(arguments or {})
    operations: dict[str, Callable[..., dict[str, Any]]] = {
        "search_matches": soccer.search_matches,
        "team_statistics": soccer.team_statistics,
        "head_to_head": soccer.head_to_head,
        "search_players": soccer.search_players,
        "standings": soccer.standings,
        "competition_statistics": soccer.competition_statistics,
        "biggest_victories": soccer.biggest_victories,
        "best_record": soccer.best_record,
        "team_competitions": soccer.team_competitions,
        "derby_matches": soccer.derby_matches,
        "competition_finals": soccer.competition_finals,
        "club_profile": soccer.club_profile,
        "compare_seasons": soccer.compare_seasons,
        "dataset_status": soccer.dataset_status,
    }
    if name == "ask_soccer":
        question = kwargs.pop("question")
        return NaturalLanguageQuery(soccer).ask(question, **kwargs)
    operation = operations.get(name)
    if operation is None:
        raise ValueError(f"Unknown MCP tool: {name}")
    return operation(**kwargs)


server = Server(SERVER_NAME)
# Backward-compatible public name used by some MCP launchers and probes.
mcp = server


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Advertise all deterministic query and analytics operations."""
    return [types.Tool(**definition) for definition in TOOL_DEFINITIONS]


@server.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """Execute a tool and return portable JSON as MCP text content."""
    result = dispatch_tool(name, arguments)
    return [
        types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        )
    ]


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """Advertise the historical dataset inventory resource."""
    return [
        types.Resource(
            uri=DATASET_URI,
            name="Brazilian soccer dataset inventory",
            description="Usable row counts for all six bundled historical Kaggle CSV files.",
            mimeType="text/plain",
        )
    ]


@server.read_resource()
async def read_resource(uri: Any) -> str:
    """Read the dataset inventory resource."""
    if str(uri).rstrip("/") != DATASET_URI:
        raise ValueError(f"Unknown MCP resource: {uri}")
    status = get_service().dataset_status()
    lines = ["Bundled Brazilian soccer dataset inventory:"]
    lines.extend(
        f"- {name}: {count} usable rows"
        for name, count in status["rows_by_source"].items()
    )
    lines.append("Data is historical and must not be represented as live.")
    return "\n".join(lines)


async def run() -> None:
    """Serve MCP JSON-RPC over stdin/stdout until the client disconnects."""
    async with mcp_stdio.stdio_server() as (read_stream, write_stream):
        if hasattr(server, "create_initialization_options"):
            initialization_options = server.create_initialization_options()
        else:  # pragma: no cover - retained for early 1.x SDK compatibility
            initialization_options = InitializationOptions(
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
        await server.run(read_stream, write_stream, initialization_options)


def main() -> None:
    """Synchronous console-script entrypoint using stdio transport."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
