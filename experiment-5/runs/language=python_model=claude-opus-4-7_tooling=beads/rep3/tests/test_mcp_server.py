"""BDD-style tests for the MCP server adapter layer.

Feature: MCP server exposes the soccer queries as tools
  Given the FastMCP instance is constructed
  When I list its registered tools
  Then I see every expected tool by name
  And I can invoke a tool and get back JSON-friendly data.
"""

from __future__ import annotations

import asyncio
import json


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


class TestServerTools:
    def test_all_required_tools_are_registered(self):
        from brazilian_soccer_mcp.server import mcp

        tools = _run(mcp.list_tools())
        names = {t.name for t in tools}
        required = {
            "find_matches", "head_to_head",
            "team_stats", "team_competitions",
            "find_players", "top_brazilian_players", "players_at_brazilian_clubs",
            "standings", "season_summary",
            "biggest_wins", "aggregate_stats",
            "top_scoring_teams", "best_records",
        }
        missing = required - names
        assert not missing, f"missing tools: {missing}"

    def test_standings_tool_returns_json_serializable_result(self):
        from brazilian_soccer_mcp.server import mcp

        result = _run(mcp.call_tool("standings", {"season": 2019, "competition": "Brasileirão"}))
        # FastMCP returns (content_list, structured_payload).
        assert isinstance(result, tuple)
        content, structured = result
        # The structured payload wraps the list under "result".
        assert isinstance(structured, dict) and "result" in structured
        rows = structured["result"]
        assert isinstance(rows, list) and len(rows) >= 20
        assert "Flamengo" in rows[0]["team"]
        # And every content block round-trips as JSON.
        for block in content:
            json.loads(block.text)
