"""Tests for the MCP tool functions themselves (not the stdio transport)."""

import pytest

from soccer_mcp import server


@pytest.fixture(autouse=True)
def _reset_repo_cache():
    server._repo = None
    yield
    server._repo = None


def test_tools_registered_with_descriptions():
    tool_names = {
        "list_teams",
        "list_competitions",
        "list_seasons",
        "find_matches",
        "head_to_head",
        "team_record",
        "standings",
        "biggest_wins",
        "average_goals",
        "best_record",
        "search_players",
        "top_players",
    }
    registered = {t.name for t in server.mcp._tool_manager.list_tools()}
    assert tool_names <= registered
    for tool in server.mcp._tool_manager.list_tools():
        if tool.name in tool_names:
            assert tool.description, f"{tool.name} is missing a description"


def test_find_matches_tool_returns_plain_dicts():
    result = server.find_matches(team="Flamengo", opponent="Fluminense", limit=5)
    assert isinstance(result, list)
    assert len(result) <= 5
    for m in result:
        assert isinstance(m, dict)
        assert "home_team" in m and "away_team" in m


def test_standings_tool_returns_2019_champion():
    rows = server.standings("Brasileirao Serie A", 2019, min_matches=30)
    assert rows[0]["team"] == "Flamengo"
    assert rows[0]["points"] == 90


def test_head_to_head_tool():
    result = server.head_to_head("Flamengo", "Fluminense")
    assert result["matches_found"] > 0


def test_search_players_tool():
    result = server.search_players(name="Neymar")
    assert any("Neymar" in p["name"] for p in result)


def test_top_players_tool_brazil():
    result = server.top_players(nationality="Brazil", n=5)
    assert len(result) == 5
    assert all(p["nationality"] == "Brazil" for p in result)


def test_get_repository_is_cached():
    a = server.get_repository()
    b = server.get_repository()
    assert a is b
