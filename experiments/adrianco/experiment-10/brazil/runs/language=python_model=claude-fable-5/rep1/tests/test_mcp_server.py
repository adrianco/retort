"""Feature: MCP server

The server must expose the query capabilities as MCP tools and respond
within the performance budget (simple lookups < 2s, aggregates < 5s).
"""

import asyncio
import json
import time

import pytest

import server


EXPECTED_TOOLS = {
    "search_matches",
    "get_head_to_head",
    "get_team_stats",
    "get_team_competitions",
    "get_standings",
    "get_competition_stats",
    "get_biggest_wins",
    "get_best_records",
    "search_players",
    "get_player",
    "get_top_players",
    "get_data_summary",
}


def call_tool(name: str, args: dict) -> dict:
    contents = asyncio.run(server.mcp.call_tool(name, args))
    # FastMCP may return (content, structured) or just content
    if isinstance(contents, tuple):
        contents = contents[0]
    text = "".join(c.text for c in contents if hasattr(c, "text"))
    return json.loads(text)


class TestToolRegistration:
    def test_all_tools_are_registered(self):
        tools = asyncio.run(server.mcp.list_tools())
        names = {t.name for t in tools}
        assert EXPECTED_TOOLS <= names

    def test_tools_have_descriptions(self):
        tools = asyncio.run(server.mcp.list_tools())
        for tool in tools:
            if tool.name in EXPECTED_TOOLS:
                assert tool.description, f"{tool.name} is missing a description"


class TestToolCalls:
    def test_head_to_head_tool(self, db):
        result = call_tool("get_head_to_head",
                           {"team1": "Flamengo", "team2": "Fluminense"})
        assert result["total_matches"] > 0
        assert "summary" in result

    def test_standings_tool(self, db):
        result = call_tool("get_standings", {"season": 2019})
        assert result["champion"] == "Flamengo"

    def test_player_tool(self, db):
        result = call_tool("search_players",
                           {"nationality": "Brazil", "limit": 3})
        assert result["total_players"] > 500

    def test_unknown_team_returns_error_payload(self, db):
        result = call_tool("get_team_stats", {"team": "Borussia Tijuca"})
        assert "error" in result

    def test_data_summary_tool(self, db):
        result = call_tool("get_data_summary", {})
        assert result["total_matches"] > 15000
        assert result["total_players"] == 18207


class TestPerformance:
    def test_simple_lookup_under_2_seconds(self, db):
        start = time.monotonic()
        call_tool("search_matches", {"team": "Flamengo", "limit": 10})
        assert time.monotonic() - start < 2.0

    def test_aggregate_query_under_5_seconds(self, db):
        start = time.monotonic()
        call_tool("get_standings", {"season": 2019})
        call_tool("get_competition_stats", {"competition": "serie-a"})
        call_tool("get_best_records", {"venue": "away"})
        assert time.monotonic() - start < 5.0
