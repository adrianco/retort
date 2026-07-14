"""Smoke tests for the FastMCP server wiring."""
import asyncio

import pytest

from brazilian_soccer.data_loader import Match, Player
from brazilian_soccer.knowledge_base import SoccerKB
from brazilian_soccer import server as srv

EXPECTED_TOOLS = {
    "find_matches", "head_to_head", "team_record", "standings",
    "search_players", "competition_stats", "biggest_wins",
    "list_competitions", "list_seasons",
}


@pytest.fixture
def kb():
    matches = [
        Match("Brasileirão Série A", "Flamengo", "Santos", 2, 0,
              season=2019, date="2019-05-01", round="1"),
        Match("Copa Libertadores", "Flamengo", "Santos", 5, 0,
              season=2019, date="2019-06-01", stage="final"),
    ]
    players = [Player(2, "Gabriel Barbosa", 22, "Brazil", 78, 85, "Flamengo", "ST")]
    return SoccerKB(matches, players)


def _text(call_result):
    content, _structured = call_result
    return "\n".join(c.text for c in content)


def test_all_expected_tools_registered(kb):
    server = srv.build_server(kb=kb)
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS.issubset(names)


def test_find_matches_tool_executes(kb):
    server = srv.build_server(kb=kb)
    result = asyncio.run(server.call_tool("find_matches", {"team": "Flamengo"}))
    text = _text(result)
    assert "Flamengo" in text
    assert "5-0" in text


def test_standings_tool_executes(kb):
    server = srv.build_server(kb=kb)
    result = asyncio.run(server.call_tool(
        "standings", {"competition": "Brasileirão", "season": 2019}))
    assert "Standings" in _text(result)


def test_build_server_loads_real_data_dir():
    # build_server with a data_dir should construct a usable KB.
    server = srv.build_server(data_dir="data/kaggle")
    result = asyncio.run(server.call_tool(
        "standings", {"competition": "Brasileirão Série A", "season": 2019}))
    assert "Flamengo" in _text(result)
