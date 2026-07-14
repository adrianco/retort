"""BDD scenarios: the MCP server itself.

Feature: MCP Server
  The knowledge base is exposed as MCP tools that an LLM client can call.
"""

import asyncio
import json

import pytest

import server


EXPECTED_TOOLS = {
    "search_matches",
    "get_head_to_head",
    "get_team_statistics",
    "get_team_competitions",
    "get_standings",
    "get_cup_finals",
    "get_libertadores_bracket",
    "search_players",
    "get_players_by_club_summary",
    "get_average_goals",
    "get_biggest_wins",
    "get_best_record",
    "get_data_summary",
}


def call_tool(name: str, arguments: dict | None = None) -> dict:
    """Invoke an MCP tool and return its structured (JSON) payload."""
    result = asyncio.run(server.mcp.call_tool(name, arguments or {}))
    # FastMCP returns (content_blocks, structured) or just content blocks
    if isinstance(result, tuple):
        content, structured = result
        if structured is not None:
            return structured.get("result", structured)
    else:
        content = result
    return json.loads(content[0].text)


class TestToolRegistration:
    def test_all_tools_registered(self):
        # Given the MCP server module
        tools = asyncio.run(server.mcp.list_tools())
        names = {t.name for t in tools}
        # Then every required capability is exposed as a tool
        assert EXPECTED_TOOLS <= names

    def test_tools_have_descriptions(self):
        tools = asyncio.run(server.mcp.list_tools())
        for tool in tools:
            assert tool.description, f"{tool.name} has no description"


class TestToolInvocation:
    def test_search_matches_via_mcp(self):
        # When an MCP client calls search_matches
        payload = call_tool("search_matches", {
            "team": "Flamengo", "opponent": "Fluminense", "limit": 5,
        })
        # Then it receives structured match data
        assert payload["total_found"] >= 40
        assert len(payload["matches"]) == 5
        first = payload["matches"][0]
        assert {"date", "competition", "home_team", "away_team", "score"} <= set(first)

    def test_head_to_head_via_mcp(self):
        payload = call_tool("get_head_to_head", {
            "team1": "Palmeiras", "team2": "Santos",
        })
        assert payload["total_matches"] > 0

    def test_standings_via_mcp(self):
        payload = call_tool("get_standings", {"season": 2019})
        assert "Flamengo" in payload["champion"]

    def test_player_search_via_mcp(self):
        payload = call_tool("search_players", {"name": "Neymar"})
        assert payload["players"][0]["name"] == "Neymar Jr"

    def test_data_summary_via_mcp(self):
        payload = call_tool("get_data_summary", {})
        assert payload["total_players"] == 18207
        assert len(payload["sources"]) == 6 - 1  # five match files
        assert payload["total_matches"] > 15000

    def test_unknown_team_is_handled_gracefully(self):
        # When a client asks about a team that does not exist
        payload = call_tool("search_matches", {"team": "Real Madrid CF XYZ"})
        # Then an empty result (not an error) is returned
        assert payload["total_found"] == 0
        assert payload["matches"] == []


class TestQueryPerformance:
    """Scenario: simple lookups < 2s, aggregates < 5s (TASK.md)."""

    @pytest.fixture(autouse=True)
    def _warm(self, kb):
        # Given the data is loaded (load time excluded, as the server
        # loads once at startup)
        pass

    def test_simple_lookup_under_2_seconds(self, kb):
        import time
        start = time.monotonic()
        kb.find_matches(team="Flamengo", opponent="Corinthians", limit=10)
        assert time.monotonic() - start < 2.0

    def test_aggregate_query_under_5_seconds(self, kb):
        import time
        start = time.monotonic()
        kb.standings(2019)
        kb.average_goals(competition="Serie A")
        kb.best_record(venue="away")
        assert time.monotonic() - start < 5.0
