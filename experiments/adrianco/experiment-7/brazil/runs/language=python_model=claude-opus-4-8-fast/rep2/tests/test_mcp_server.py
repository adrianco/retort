"""
================================================================================
Module: tests.test_mcp_server
--------------------------------------------------------------------------------
Context:
    BDD scenarios verifying the MCP adapter layer (server.py): the tools are
    registered with the FastMCP server, are individually callable, and render
    the human-readable answer formats shown in TASK.md.

Responsibility:
    Smoke-test every MCP tool end-to-end (load -> query -> formatted text) and
    confirm the tool registry is exposed for an MCP client to discover.
================================================================================
"""

import asyncio

from brazilian_soccer_mcp import server


def test_all_tools_registered():
    # GIVEN the FastMCP server WHEN listing tools THEN all categories are present
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "find_matches",
        "head_to_head",
        "team_record",
        "team_competitions",
        "search_players",
        "get_player",
        "players_by_club",
        "standings",
        "champion",
        "list_competitions",
        "list_seasons",
        "match_statistics",
        "biggest_wins",
        "best_record",
    }
    assert expected <= names


class TestToolBehaviour:
    def test_find_matches_tool(self):
        out = server.find_matches(team="Flamengo", opponent="Fluminense", limit=5)
        assert "Flamengo" in out and "Fluminense" in out
        assert "-" in out  # contains a rendered scoreline / bullet

    def test_head_to_head_tool(self):
        out = server.head_to_head("Flamengo", "Fluminense")
        assert "head-to-head" in out.lower()
        assert "wins" in out.lower()

    def test_team_record_tool(self):
        out = server.team_record("Corinthians", season=2022,
                                competition="Brasileirão", venue="home")
        assert "Corinthians" in out
        assert "Win rate" in out

    def test_standings_tool(self):
        out = server.standings("Brasileirão", 2019)
        assert "Standings" in out
        assert "Flamengo" in out
        assert "Champion" in out

    def test_champion_tool(self):
        out = server.champion("Brasileirão", 2019)
        assert "Flamengo" in out
        assert "champion" in out.lower()

    def test_search_players_tool(self):
        out = server.search_players(nationality="Brazil", limit=5)
        assert "Overall" in out

    def test_get_player_tool(self):
        out = server.get_player("Neymar")
        assert "Neymar" in out
        assert "Overall" in out

    def test_match_statistics_tool(self):
        out = server.match_statistics(competition="Brasileirão")
        assert "Average goals per match" in out

    def test_biggest_wins_tool(self):
        out = server.biggest_wins(limit=3)
        assert "Biggest victories" in out

    def test_best_record_tool(self):
        out = server.best_record(venue="away", competition="Brasileirão", season=2019)
        assert "record" in out.lower()

    def test_list_tools_metadata(self):
        out = server.list_competitions()
        assert "Brasileirão Série A" in out
