"""Smoke test for the MCP server wiring.

Drives the FastMCP server through its ``list_tools`` / ``call_tool`` APIs
without spinning up a stdio transport, so the test stays in-process.
"""
from __future__ import annotations

import json

import pytest  # noqa: F401  (used by fixtures)

from soccer_mcp import server


@pytest.fixture(autouse=True)
def _reset_store():
    server.reset_store()
    yield
    server.reset_store()


def test_tools_are_registered():
    import asyncio
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "find_matches", "head_to_head", "team_record", "compare_teams",
        "find_players", "top_brazilian_players", "players_by_club",
        "competition_standings", "competition_summary",
        "average_goals_per_match", "biggest_wins",
        "best_home_record", "best_away_record",
        "overall_statistics", "list_competitions", "list_seasons",
    }
    missing = expected - names
    assert not missing, f"missing tools: {missing}"


def test_call_tool_returns_payload():
    import asyncio
    result = asyncio.run(server.mcp.call_tool("overall_statistics", {}))
    # FastMCP returns a list of TextContent items + a structured payload.
    if isinstance(result, tuple):
        text_items, structured = result
    else:  # older API returned just the text items
        text_items, structured = result, None

    assert text_items, "tool returned no text content"
    text = text_items[0].text
    payload = structured or json.loads(text)
    assert payload["matches_total"] > 20000
    assert payload["players_total"] > 10000


def test_overview_resource():
    import asyncio
    result = asyncio.run(server.mcp.read_resource("soccer://overview"))
    # FastMCP returns an iterable of ReadResourceContents
    items = list(result)
    assert items
    payload = json.loads(items[0].content)
    assert "matches_total" in payload
