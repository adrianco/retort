"""Tests for the MCP server wiring."""

import datetime as dt

import pytest

from brazilian_soccer.data_loader import Match, Player
from brazilian_soccer.queries import KnowledgeBase
from brazilian_soccer.server import build_server


@pytest.fixture
def kb():
    matches = [
        Match(competition="Brasileirão", season=2020, date=dt.date(2020, 1, 1),
              round="1", stage=None, home_team="Palmeiras-SP", away_team="Santos",
              home_goal=2, away_goal=1),
    ]
    players = [
        Player(player_id=1, name="Neymar Jr", age=27, nationality="Brazil",
               overall=92, potential=92, club="Paris Saint-Germain",
               position="LW", jersey_number=10),
    ]
    return KnowledgeBase(matches, players)


@pytest.fixture
def server(kb):
    return build_server(kb)


@pytest.mark.asyncio
async def test_server_registers_expected_tools(server):
    names = {t.name for t in await server.list_tools()}
    expected = {
        "search_matches", "head_to_head", "team_record", "standings",
        "search_players", "statistics", "biggest_wins",
    }
    assert expected <= names


@pytest.mark.asyncio
async def test_search_matches_tool_returns_text(server):
    _content, result = await server.call_tool("search_matches", {"team": "Palmeiras"})
    assert "Palmeiras" in result["result"]
    assert "2-1" in result["result"]


@pytest.mark.asyncio
async def test_search_players_tool(server):
    _content, result = await server.call_tool("search_players", {"nationality": "Brazil"})
    assert "Neymar Jr" in result["result"]


def test_build_server_without_kb_loads_real_data():
    # Smoke test: building with no KB loads the real datasets lazily.
    server = build_server()
    assert server is not None
