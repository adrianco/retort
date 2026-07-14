"""
================================================================================
BDD Feature: Response Formatting & MCP Server Wiring
================================================================================

CONTEXT
-------
Verifies that the formatting layer renders the spec's example answer shapes and
that the MCP server can be constructed and exposes the expected tools. The MCP
construction test is skipped automatically when the optional ``mcp`` SDK is not
installed (the engine itself never depends on it).
================================================================================
"""

import importlib.util

import pytest

from brazilian_soccer_mcp import formatting as fmt
from brazilian_soccer_mcp.normalize import COMP_BRASILEIRAO


class TestFormatting:
    """Feature: Render results into LLM-friendly text."""

    def test_format_matches(self, synthetic_kg):
        matches = synthetic_kg.find_matches(team="Flamengo", season=2023)
        out = fmt.format_matches(matches, header="Flamengo 2023:")
        assert "Flamengo 2023:" in out
        assert "Flamengo" in out and "-" in out

    def test_format_head_to_head(self, synthetic_kg):
        h2h = synthetic_kg.head_to_head("Flamengo", "Palmeiras")
        out = fmt.format_head_to_head(h2h)
        assert "Head-to-head in dataset:" in out
        assert "Flamengo 1 wins" in out

    def test_format_team_stats(self, synthetic_kg):
        out = fmt.format_team_stats(synthetic_kg.team_stats("Flamengo", season=2023))
        assert "Win rate: 50.0%" in out
        assert "Wins: 2" in out

    def test_format_standings(self, synthetic_kg):
        rows = synthetic_kg.standings(2023, COMP_BRASILEIRAO)
        out = fmt.format_standings(rows, 2023, COMP_BRASILEIRAO)
        assert "Champion" in out
        assert "Flamengo" in out

    def test_format_players(self, synthetic_kg):
        players = synthetic_kg.find_players(nationality="Brazil")
        out = fmt.format_players(players, header="Top Brazilians:")
        assert "1. Neymar Jr" in out
        assert "Overall: 92" in out


_HAS_MCP = importlib.util.find_spec("mcp") is not None


@pytest.mark.skipif(not _HAS_MCP, reason="mcp SDK not installed")
class TestServerWiring:
    """Feature: The MCP server builds and registers tools."""

    def test_server_builds(self):
        from brazilian_soccer_mcp.server import build_server
        server = build_server()
        assert server is not None

    def test_expected_tools_registered(self):
        import asyncio
        from brazilian_soccer_mcp.server import build_server
        server = build_server()
        tools = asyncio.run(server.list_tools())
        names = {t.name for t in tools}
        expected = {
            "search_matches", "head_to_head", "team_stats", "compare_teams",
            "search_players", "get_player", "league_standings",
            "season_champion", "average_goals", "biggest_wins",
        }
        assert expected.issubset(names)


def test_engine_importable_without_mcp():
    """The query engine must import even if the mcp SDK is absent."""
    from brazilian_soccer_mcp import KnowledgeGraph, load_knowledge_graph  # noqa
    assert KnowledgeGraph is not None
