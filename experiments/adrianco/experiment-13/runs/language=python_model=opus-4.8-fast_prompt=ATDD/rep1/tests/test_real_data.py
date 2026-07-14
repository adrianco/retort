"""
Context
=======
End-to-end coverage check against the *real* provided Kaggle datasets in
``data/kaggle``. Where the acceptance suite uses tiny controlled fixtures for
determinism, this test confirms the success criteria that all six CSV files load
and are queryable through the MCP interface, that cross-file queries work, and
that the well-known sample questions return sensible answers. It is skipped if
the datasets are not present.
"""

import json
from pathlib import Path

import pytest

from mcp.shared.memory import create_connected_server_and_client_session

from brazilian_soccer_mcp.server import create_server
from tests.conftest import _error_text

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not DATA_DIR.exists(), reason="real datasets not present"),
]


async def _call(tool, **args):
    server = create_server(str(DATA_DIR))
    async with create_connected_server_and_client_session(server) as session:
        await session.initialize()
        result = await session.call_tool(tool, args)
        assert result.isError is False, _error_text(result)
        if result.structuredContent is not None:
            return result.structuredContent
        return json.loads(result.content[0].text)


async def test_all_match_files_are_loaded_and_queryable():
    # Brasileirão (Brasileirao_Matches.csv + novo_campeonato_brasileiro.csv)
    bra = await _call("find_matches", team="Flamengo", competition="Brasileirão")
    assert bra["count"] > 0
    # Copa do Brasil
    cup = await _call("find_matches", competition="Copa do Brasil")
    assert cup["count"] > 0
    # Libertadores
    lib = await _call("find_matches", competition="Libertadores")
    assert lib["count"] > 0


async def test_player_data_is_loaded():
    brazilians = await _call("search_players", nationality="Brazil", limit=5)
    assert brazilians["count"] > 0
    assert all(p["nationality"] == "Brazil" for p in brazilians["players"])


async def test_known_player_lookup():
    res = await _call("search_players", name="Neymar")
    assert res["count"] >= 1
    assert any("Neymar" in p["name"] for p in res["players"])


async def test_cross_file_team_and_player_query():
    # Player side: Santos squad members in the FIFA data.
    players = await _call("search_players", club="Santos", limit=5)
    # Match side: Santos fixtures in the match data.
    matches = await _call("find_matches", team="Santos")
    assert players["count"] > 0
    assert matches["count"] > 0


async def test_historical_season_standings_have_a_champion():
    standings = await _call("get_standings", season=2019, competition="Brasileirão")
    assert standings["champion"] is not None
    assert len(standings["standings"]) >= 16  # a full Série A table


async def test_competition_statistics_are_reasonable():
    stats = await _call("get_competition_stats", competition="Brasileirão")
    assert stats["matches"] > 1000
    assert 1.5 < stats["average_goals_per_match"] < 4.0
    assert 0.0 < stats["home_win_rate"] < 100.0
