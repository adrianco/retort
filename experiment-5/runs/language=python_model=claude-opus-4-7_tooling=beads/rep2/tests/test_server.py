"""Smoke tests for the MCP server surface.

We don't try to spin up a stdio transport — that's the framework's
responsibility. Instead we build the server, inspect the registered tool
list, and confirm a representative tool actually executes through MCP's call
path with realistic arguments.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from soccer_mcp.server import build_server


def _payload(call_result) -> dict:
    """Extract the JSON dict from whatever shape FastMCP returned."""
    if isinstance(call_result, tuple):
        content, structured = call_result
        if isinstance(structured, dict):
            return structured.get("result", structured) if "result" in structured else structured
        call_result = content
    if isinstance(call_result, list):
        # FastMCP returns a list of mcp.types.TextContent.
        for item in call_result:
            text = getattr(item, "text", None)
            if text:
                return json.loads(text)
    if isinstance(call_result, dict):
        return call_result.get("result", call_result)
    raise AssertionError(f"unexpected result shape: {call_result!r}")

EXPECTED_TOOLS = {
    "find_matches",
    "head_to_head",
    "last_match_between",
    "biggest_wins",
    "team_record",
    "home_away_split",
    "team_seasons",
    "team_competitions",
    "compare_teams",
    "top_scoring_teams",
    "search_players",
    "players_by_nationality",
    "players_by_club",
    "top_players",
    "brazilian_players_by_club",
    "standings",
    "champion",
    "relegated_teams",
    "libertadores_stages",
    "goals_per_match",
    "home_advantage",
    "best_home_record",
    "best_away_record",
    "season_comparison",
    "list_competitions",
    "list_seasons",
}


@pytest.fixture(scope="module")
def server():
    return build_server()


def test_registers_expected_tools(server) -> None:
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"missing tools: {missing}"


def test_call_head_to_head_tool(server) -> None:
    result = asyncio.run(server.call_tool("head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"}))
    payload = _payload(result)
    assert payload["matches_played"] > 0
    assert payload["team_a_wins"] + payload["team_b_wins"] + payload["draws"] == payload["matches_played"]


def test_call_champion_tool(server) -> None:
    result = asyncio.run(server.call_tool("champion", {"competition": "Brasileirão", "season": 2019}))
    payload = _payload(result)
    assert "Flamengo" in payload["team"]
