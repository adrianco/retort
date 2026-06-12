"""End-to-end tests of the MCP tool layer.

Exercises the tools the way an MCP client would: by name, through
``FastMCP.call_tool``, asserting on the formatted text responses.
"""

import asyncio

import pytest

import server


def call(tool_name: str, args: dict) -> str:
    """Invoke an MCP tool by name and return its text output."""
    result = asyncio.run(server.mcp.call_tool(tool_name, args))
    content = result[0] if isinstance(result, tuple) else result
    return content[0].text


EXPECTED_TOOLS = {
    "find_matches", "head_to_head", "team_record", "standings",
    "top_scoring_teams", "list_competitions", "list_seasons", "list_teams",
    "average_goals", "biggest_wins", "search_players", "get_player",
    "brazilian_players_by_club",
}


def test_all_tools_registered():
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names


def test_standings_tool_text():
    text = call("standings", {"competition": "Série A", "season": 2019, "top": 5})
    assert "2019" in text
    assert "Flamengo" in text
    assert "Champion" in text


def test_find_matches_tool_text():
    text = call("find_matches", {"team": "Flamengo", "opponent": "Fluminense", "limit": 5})
    assert "Flamengo" in text and "Fluminense" in text


def test_head_to_head_tool_text():
    text = call("head_to_head", {"team1": "Palmeiras", "team2": "Santos"})
    assert "head-to-head" in text.lower()
    assert "Palmeiras" in text and "Santos" in text


def test_team_record_tool_text():
    text = call("team_record", {"team": "Corinthians", "season": 2022,
                                "competition": "Série A", "venue": "home"})
    assert "Corinthians" in text
    assert "Win rate" in text


def test_player_tools_text():
    text = call("search_players", {"nationality": "Brazil", "limit": 3})
    assert "Neymar" in text
    detail = call("get_player", {"name": "Neymar"})
    assert "Neymar" in detail and "Overall" in detail


def test_average_goals_tool_text():
    text = call("average_goals", {"competition": "Série A"})
    assert "Average goals per match" in text


def test_biggest_wins_tool_text():
    text = call("biggest_wins", {"competition": "Libertadores", "limit": 3})
    assert "margin" in text.lower()


def test_get_player_not_found():
    text = call("get_player", {"name": "Nonexistent Player XYZ"})
    assert "No player found" in text


@pytest.mark.parametrize("tool,args", [
    ("list_competitions", {}),
    ("list_seasons", {"competition": "Série A"}),
    ("list_teams", {"competition": "Série A", "season": 2019}),
])
def test_discovery_tools_text(tool, args):
    text = call(tool, args)
    assert isinstance(text, str) and len(text) > 0
