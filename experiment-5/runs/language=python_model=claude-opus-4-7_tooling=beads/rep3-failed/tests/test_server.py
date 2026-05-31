"""Feature: MCP server tools exposed end-to-end.

These tests don't speak the MCP protocol — they invoke the registered tool
functions directly through the FastMCP tool manager, which is enough to
exercise the surface area used by the protocol layer.
"""

import asyncio
import json

import pytest

from brazilian_soccer_mcp.server import build_server


@pytest.fixture(scope="module")
def server(knowledge):
    return build_server(knowledge)


def _call(server, name: str, **kwargs) -> dict:
    """Invoke a FastMCP tool and return its parsed JSON payload.

    FastMCP returns a list of ``TextContent`` items whose ``.text`` is the
    JSON-encoded tool result.
    """
    result = asyncio.run(server.call_tool(name, kwargs))
    assert isinstance(result, list) and result, f"empty result for {name}: {result!r}"
    return json.loads(result[0].text)


class TestMCPToolRegistration:
    def test_expected_tools_present(self, server):
        tools = asyncio.run(server.list_tools())
        names = {t.name for t in tools}
        expected = {
            "find_matches", "head_to_head",
            "team_stats", "team_seasons", "team_competitions",
            "find_players", "top_brazilian_players",
            "season_standings", "champion", "competitions", "seasons",
            "average_goals", "biggest_wins",
            "best_home_record", "best_away_record",
            "top_scoring_teams",
        }
        assert expected <= names


class TestMCPCalls:
    def test_find_matches_returns_payload(self, server):
        payload = _call(server, "find_matches", team="Flamengo", season=2019, limit=5)
        assert payload["count"] > 0
        assert len(payload["matches"]) <= 5

    def test_season_standings_call(self, server):
        payload = _call(server, "season_standings", season=2019)
        rows = payload["rows"]
        assert rows[0]["team"].lower() == "flamengo"
        assert rows[0]["points"] == 90

    def test_top_brazilian_players_call(self, server):
        payload = _call(server, "top_brazilian_players", limit=3)
        assert payload["count"] == 3
        assert payload["players"][0]["overall"] >= payload["players"][-1]["overall"]

    def test_average_goals_call(self, server):
        payload = _call(
            server, "average_goals", competition="Brasileirão Série A", season=2019
        )
        assert payload["matches"] > 0

    def test_competitions_lookup(self, server):
        payload = _call(server, "competitions")
        assert "Brasileirão Série A" in payload["competitions"]
