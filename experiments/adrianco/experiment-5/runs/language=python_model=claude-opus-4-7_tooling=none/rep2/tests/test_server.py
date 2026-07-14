"""BDD: MCP server wiring.

Feature: MCP server
  As an MCP client
  I want the soccer queries exposed as MCP tools
  So that an LLM can call them over the protocol
"""

from __future__ import annotations

import asyncio
import json

import pytest

from brazilian_soccer_mcp.server import build_server


@pytest.fixture(scope="module")
def server_and_store():
    return build_server()


class TestToolsAreRegistered:
    """Scenario: every documented capability is exposed as an MCP tool."""

    def test_all_expected_tools_present(self, server_and_store) -> None:
        mcp, _ = server_and_store
        tools = asyncio.run(mcp.list_tools())
        names = {t.name for t in tools}
        expected = {
            "search_matches",
            "head_to_head",
            "last_match",
            "team_record",
            "top_scoring_teams",
            "compare_teams",
            "search_players",
            "top_brazilian_players",
            "brazilian_player_summary",
            "season_standings",
            "list_competitions",
            "list_seasons",
            "average_goals_per_match",
            "biggest_wins",
            "home_away_split",
            "best_home_records",
            "best_away_records",
        }
        missing = expected - names
        assert not missing, f"missing tools: {missing}"


class TestToolInvocation:
    """Scenario: invoke a tool through MCP and read the JSON result."""

    def test_head_to_head_through_mcp(self, server_and_store) -> None:
        mcp, _ = server_and_store
        # When I invoke the tool the way an MCP client would
        result = asyncio.run(
            mcp.call_tool(
                "head_to_head",
                {"team_a": "Flamengo", "team_b": "Fluminense"},
            )
        )
        # FastMCP returns (content_list, structured_content) in 1.x.
        # The structured output carries the dict our query returned.
        if isinstance(result, tuple):
            _, payload = result
        else:
            payload = result
        # Some FastMCP versions wrap the dict in a single "result" key.
        if isinstance(payload, dict) and set(payload.keys()) == {"result"}:
            payload = payload["result"]
        # When I read the payload
        # Then it has the head-to-head shape
        assert isinstance(payload, dict)
        assert payload["team_a"] == "Flamengo"
        assert payload["team_b"] == "Fluminense"
        assert payload["matches"] > 0
        # And it's JSON-serializable end-to-end
        json.dumps(payload)
