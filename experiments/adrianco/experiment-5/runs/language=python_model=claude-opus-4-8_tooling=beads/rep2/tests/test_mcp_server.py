"""
================================================================================
test_mcp_server.py - BDD scenarios for the MCP tool layer
================================================================================

Feature: MCP server
  Scenario: Tools return formatted prose and the server registers them
    Given the engine is loaded
    When I call a tool function
    Then I receive a human-readable answer
    And building the FastMCP server registers every tool.
================================================================================
"""

import pytest

from brazilian_soccer_mcp import server


class TestToolFunctions:
    def test_head_to_head_tool_prose(self):
        out = server.head_to_head("Flamengo", "Fluminense")
        assert "head-to-head" in out.lower()
        assert "Flamengo" in out and "Fluminense" in out

    def test_standings_tool_prose(self):
        out = server.standings(2019, "serie_a")
        assert "Final Standings" in out
        assert "Flamengo" in out

    def test_search_players_tool_prose(self):
        out = server.search_players(nationality="Brazil", limit=3)
        assert "found" in out.lower()

    def test_data_summary_tool(self):
        out = server.data_summary()
        assert "matches" in out.lower()
        assert "players" in out.lower()

    def test_biggest_wins_tool(self):
        out = server.biggest_wins(competition="serie_a", limit=3)
        assert "Biggest victories" in out


class TestServerWiring:
    def test_all_tools_have_docstrings(self):
        # Every tool exposed to the LLM needs a description
        for tool in server._TOOLS:
            assert tool.__doc__ and tool.__doc__.strip()

    def test_build_mcp_registers_every_tool(self):
        mcp = pytest.importorskip("mcp")  # skip cleanly if SDK absent
        srv = server.build_mcp()
        # FastMCP exposes registered tools via list_tools (async) or _tool_manager
        names = {t.__name__ for t in server._TOOLS}
        registered = {t.name for t in srv._tool_manager.list_tools()}
        assert names <= registered
