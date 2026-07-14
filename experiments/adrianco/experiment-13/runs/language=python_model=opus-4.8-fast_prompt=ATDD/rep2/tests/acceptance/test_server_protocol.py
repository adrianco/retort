"""Acceptance: the MCP server surface itself.

The system is reachable as an MCP server and advertises the documented query
capabilities as tools. An empty system answers gracefully rather than failing.
"""

import pytest

pytestmark = pytest.mark.asyncio

EXPECTED_TOOLS = {
    "find_matches",
    "head_to_head",
    "team_record",
    "competition_standings",
    "competition_winner",
    "list_competitions",
    "competition_statistics",
    "biggest_wins",
    "search_players",
    "top_players",
}


async def test_server_advertises_query_tools(soccer_system):
    async with soccer_system.running() as client:
        tools = await client.tools()

    assert EXPECTED_TOOLS <= tools


async def test_empty_system_returns_no_matches_without_error(soccer_system):
    async with soccer_system.running() as client:
        result = await client.call("find_matches", team="Flamengo")

    assert result["count"] == 0
    assert result["matches"] == []


async def test_empty_system_returns_no_players_without_error(soccer_system):
    async with soccer_system.running() as client:
        result = await client.call("search_players", name="Nobody")

    assert result["count"] == 0


async def test_winner_of_unknown_season_is_none(soccer_system):
    soccer_system.add_brasileirao_match("Flamengo-RJ", "Santos-SP", 1, 0, 2019)

    async with soccer_system.running() as client:
        result = await client.call(
            "competition_winner", competition="Brasileirão", season=1999
        )

    assert result["winner"] is None
