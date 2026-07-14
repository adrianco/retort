"""Feature: MCP server integration.

Given the MCP server
When a client connects over the MCP protocol
Then all tools are listed and calls return formatted text responses.
"""

import asyncio
import time

import pytest

import server
from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)

EXPECTED_TOOLS = {
    "search_matches", "head_to_head", "team_statistics",
    "competition_standings", "goal_statistics", "biggest_wins",
    "best_records", "search_players", "get_player", "data_summary",
}


def call(tool: str, arguments: dict | None = None) -> str:
    """Call a tool through a real in-memory MCP client/server session."""
    async def go():
        async with client_session(server.mcp._mcp_server) as session:
            result = await session.call_tool(tool, arguments or {})
            assert not result.isError, result.content
            return "".join(block.text for block in result.content
                           if block.type == "text")
    return asyncio.run(go())


class TestProtocol:
    def test_all_tools_listed(self):
        async def go():
            async with client_session(server.mcp._mcp_server) as session:
                return await session.list_tools()
        tools = asyncio.run(go())
        names = {t.name for t in tools.tools}
        assert names == EXPECTED_TOOLS

    def test_tools_have_descriptions(self):
        async def go():
            async with client_session(server.mcp._mcp_server) as session:
                return await session.list_tools()
        for tool in asyncio.run(go()).tools:
            assert tool.description and len(tool.description) > 20


class TestToolResponses:
    def test_search_matches_response_format(self):
        text = call("search_matches", {"team": "Flamengo",
                                       "opponent": "Fluminense", "limit": 5})
        assert "Found" in text and "Flamengo" in text and "Fluminense" in text

    def test_head_to_head_response(self):
        text = call("head_to_head", {"team1": "Palmeiras", "team2": "Santos"})
        assert "Head-to-head" in text
        assert "wins" in text and "draws" in text

    def test_team_statistics_response(self):
        text = call("team_statistics", {"team": "Corinthians",
                                        "season": 2022,
                                        "competition": "brasileirao",
                                        "venue": "home"})
        assert "Matches: 19" in text and "Win rate" in text

    def test_standings_response(self):
        text = call("competition_standings", {"season": 2019})
        assert text.splitlines()[1].startswith("1. Flamengo - 90 pts")
        assert "Champion" in text

    def test_player_search_response(self):
        text = call("search_players", {"nationality": "Brazil", "limit": 3})
        assert "Neymar Jr" in text

    def test_get_player_not_found_is_graceful(self):
        text = call("get_player", {"name": "Gabriel Barbosa"})
        assert "No player matching" in text

    def test_data_summary_response(self):
        text = call("data_summary")
        assert "Brasileirão Série A" in text
        assert "Copa Libertadores" in text

    def test_invalid_competition_is_reported_as_error(self):
        async def go():
            async with client_session(server.mcp._mcp_server) as session:
                return await session.call_tool(
                    "search_matches", {"competition": "Premier League"})
        result = asyncio.run(go())
        assert result.isError
        text = "".join(b.text for b in result.content if b.type == "text")
        assert "Unknown competition" in text


class TestQueryPerformance:
    """Scenario: simple lookups < 2s, aggregate queries < 5s."""

    @pytest.fixture(autouse=True)
    def warm(self):
        server.get_db()

    def test_simple_lookup_under_2_seconds(self):
        start = time.monotonic()
        call("search_matches", {"team": "Flamengo", "limit": 5})
        assert time.monotonic() - start < 2.0

    def test_aggregate_query_under_5_seconds(self):
        start = time.monotonic()
        call("best_records", {"venue": "away", "min_matches": 100})
        call("competition_standings", {"season": 2019})
        assert time.monotonic() - start < 5.0
