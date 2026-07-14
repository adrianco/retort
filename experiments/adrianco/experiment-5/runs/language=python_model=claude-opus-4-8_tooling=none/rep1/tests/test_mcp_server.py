"""
================================================================================
 BDD tests: MCP server integration
================================================================================
Feature: MCP server
  I want the query engine exposed as MCP tools returning formatted answers
  So that an LLM client can call them over the Model Context Protocol.

These tests drive the FastMCP server the same way a client would: listing tools
and invoking them by name, then asserting on the rendered text answers.
================================================================================
"""

import asyncio

import pytest

# Skip the whole module gracefully if the optional ``mcp`` package is absent.
pytest.importorskip("mcp")

from brazilian_soccer_mcp.server import build_server


@pytest.fixture(scope="module")
def server(engine):
    # Given a server built over the shared engine
    return build_server(engine)


def _call(server, name, **kwargs):
    """Invoke an MCP tool by name and return its text output."""
    async def run():
        result = await server.call_tool(name, kwargs)
        # FastMCP returns (content_list, ...) or a structured result depending on
        # version; normalize to the text of the first content block.
        content = result[0] if isinstance(result, tuple) else result
        block = content[0]
        return getattr(block, "text", str(block))
    return asyncio.run(run())


class TestServerToolRegistration:
    def test_expected_tools_are_registered(self, server):
        # When I list the server's tools
        names = {t.name for t in asyncio.run(server.list_tools())}
        # Then all five capability categories are represented
        for expected in ("find_matches", "team_record", "head_to_head",
                         "find_player", "players_at_club", "top_players",
                         "standings", "champion", "relegated_teams",
                         "average_goals", "biggest_wins"):
            assert expected in names


class TestServerToolInvocation:
    def test_find_matches_tool_returns_formatted_answer(self, server):
        # When I call find_matches for the Fla-Flu derby
        out = _call(server, "find_matches", team="Flamengo", opponent="Fluminense")
        # Then the answer mentions both teams and a head-to-head line
        assert "Flamengo" in out and "Fluminense" in out
        assert "Head-to-head" in out

    def test_champion_tool_names_the_2019_winner(self, server):
        # When I ask the champion tool about 2019
        out = _call(server, "champion", season=2019)
        # Then Flamengo is named
        assert "Flamengo" in out

    def test_standings_tool_renders_a_table(self, server):
        # When I request 2019 standings
        out = _call(server, "standings", season=2019)
        # Then the rendered table is led by the champion
        assert "standings" in out.lower()
        assert "1. Flamengo" in out

    def test_top_players_tool_lists_brazilians(self, server):
        # When I ask for the top Brazilian players
        out = _call(server, "top_players", nationality="Brazil", limit=3)
        # Then a ranked list with overall ratings is returned
        assert "Overall:" in out
        assert "1." in out
