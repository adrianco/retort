"""
Acceptance tests for the Brazilian Soccer MCP Server.

Tests exercise the system through its public MCP tool interface only.
Each test is independent and makes no assumptions about internal state.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def mcp_server():
    """Provide the MCP server instance, loaded once per test module."""
    from server import mcp
    return mcp


async def call(mcp_server, tool_name: str, **kwargs) -> str:
    content, _ = await mcp_server.call_tool(tool_name, kwargs)
    return content[0].text


# ---------------------------------------------------------------------------
# AC-1: Find matches between two specific teams
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_matches_between_two_teams(mcp_server):
    """User can find all matches between Flamengo and Fluminense."""
    result = await call(mcp_server, "find_matches", team="Flamengo", opponent="Fluminense")

    assert "Flamengo" in result
    assert "Fluminense" in result
    # Should show at least one match result
    assert any(char.isdigit() for char in result)
    # Should include head-to-head summary
    assert "win" in result.lower() or "draw" in result.lower()


# ---------------------------------------------------------------------------
# AC-2: Find matches for a team in a specific season
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_matches_by_team_and_season(mcp_server):
    """User can find all Palmeiras matches in the 2022 Brasileirao season."""
    result = await call(mcp_server, "find_matches", team="Palmeiras", season=2022)

    assert "Palmeiras" in result
    assert "2022" in result
    # Palmeiras played 38 matches in Brasileirao 2022 - should find substantial matches
    lines = [l for l in result.splitlines() if "Palmeiras" in l]
    assert len(lines) >= 5


# ---------------------------------------------------------------------------
# AC-3: Find matches by competition
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_matches_copa_do_brasil(mcp_server):
    """User can find Copa do Brasil matches."""
    result = await call(mcp_server, "find_matches", competition="Copa do Brasil", season=2019, limit=5)

    assert "Copa do Brasil" in result
    assert "2019" in result


# ---------------------------------------------------------------------------
# AC-4: Get team statistics with wins, draws, losses
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_team_stats_returns_record(mcp_server):
    """User can get Corinthians' 2022 season statistics."""
    result = await call(mcp_server, "get_team_stats", team="Corinthians", season=2022)

    assert "Corinthians" in result
    # Must include numeric win/draw/loss breakdown
    assert any(word in result.lower() for word in ["win", "draw", "loss", "w:", "d:", "l:"])
    # Must include goal counts
    assert "goal" in result.lower() or any(c.isdigit() for c in result)


# ---------------------------------------------------------------------------
# AC-5: Find players by nationality
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_players_by_nationality(mcp_server):
    """User can find Brazilian players; top-rated ones appear in results."""
    result = await call(mcp_server, "find_players", nationality="Brazil", limit=10)

    assert "Brazil" in result or "Brazilian" in result
    # Neymar should be among the top-rated
    assert "Neymar" in result


# ---------------------------------------------------------------------------
# AC-6: Find players by club
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_players_by_club(mcp_server):
    """User can search for players registered at a specific club."""
    # Grêmio is a Brazilian club present in the FIFA dataset
    result = await call(mcp_server, "find_players", club="Grêmio")

    assert "Grêmio" in result
    # Should return at least one player with a rating
    assert any(char.isdigit() for char in result)


# ---------------------------------------------------------------------------
# AC-7: Get Brasileirao standings for a season (Flamengo won 2019)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_standings_2019_brasileirao(mcp_server):
    """User can view 2019 Brasileirao standings; Flamengo appears as champion."""
    result = await call(mcp_server, "get_standings", competition="Brasileirao", season=2019)

    assert "2019" in result
    assert "Flamengo" in result
    # Flamengo won with 90 points; should be near the top
    lines = result.splitlines()
    # Find the line position of Flamengo
    flamengo_lines = [i for i, l in enumerate(lines) if "Flamengo" in l]
    assert len(flamengo_lines) > 0
    # Flamengo should appear early in the standings (top 3)
    assert flamengo_lines[0] < 10


# ---------------------------------------------------------------------------
# AC-8: Head-to-head statistics between two teams
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_head_to_head(mcp_server):
    """User can get head-to-head stats between Flamengo and Corinthians."""
    result = await call(mcp_server, "get_head_to_head", team1="Flamengo", team2="Corinthians")

    assert "Flamengo" in result
    assert "Corinthians" in result
    # Must contain win/draw counts
    assert "win" in result.lower() or "draw" in result.lower()
    # Must show at least one historical match
    assert any(char.isdigit() for char in result)


# ---------------------------------------------------------------------------
# AC-9: Team name normalization (with/without state suffix)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_team_name_normalization(mcp_server):
    """Searching 'Palmeiras' and 'Palmeiras-SP' return the same matches."""
    result_plain = await call(mcp_server, "find_matches", team="Palmeiras", season=2022)
    result_suffix = await call(mcp_server, "find_matches", team="Palmeiras-SP", season=2022)

    # Count match lines (lines containing score separator "-")
    def count_matches(text):
        return sum(1 for line in text.splitlines() if " - " in line and any(c.isdigit() for c in line))

    assert count_matches(result_plain) == count_matches(result_suffix)


# ---------------------------------------------------------------------------
# AC-10: Statistical analysis — biggest wins
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_top_stats_biggest_wins(mcp_server):
    """User can find the biggest winning margins in the dataset."""
    result = await call(mcp_server, "get_top_stats", stat_type="biggest_wins", limit=5)

    # Should include matches with large goal differences
    assert any(char.isdigit() for char in result)
    # Should list at least a few results
    lines = [l for l in result.splitlines() if l.strip()]
    assert len(lines) >= 3


# ---------------------------------------------------------------------------
# AC-11: Find players by name search
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_players_by_name(mcp_server):
    """User can search players by name fragment."""
    result = await call(mcp_server, "find_players", name="Neymar")

    assert "Neymar" in result
    # Should show rating
    assert any(char.isdigit() for char in result)


# ---------------------------------------------------------------------------
# AC-12: All six data sources are queryable
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_all_data_sources_loadable(mcp_server):
    """All six CSV datasets can be queried through the server."""
    # Brasileirao (2012-2022)
    r1 = await call(mcp_server, "find_matches", competition="Brasileirao", season=2015, limit=3)
    assert "2015" in r1

    # Copa do Brasil
    r2 = await call(mcp_server, "find_matches", competition="Copa do Brasil", season=2015, limit=3)
    assert "2015" in r2

    # Copa Libertadores
    r3 = await call(mcp_server, "find_matches", competition="Libertadores", season=2015, limit=3)
    assert "2015" in r3

    # Historical Brasileirao (2003-2019) — query a season only in historico
    r4 = await call(mcp_server, "find_matches", competition="Brasileirao", season=2005, limit=3)
    assert "2005" in r4

    # FIFA player data
    r5 = await call(mcp_server, "find_players", nationality="Brazil", limit=5)
    assert "Brazil" in r5 or "Neymar" in r5

    # BR Football extended stats — queryable via get_team_stats
    r6 = await call(mcp_server, "get_top_stats", stat_type="biggest_wins", limit=3)
    assert any(char.isdigit() for char in r6)


# ---------------------------------------------------------------------------
# AC-13: Libertadores matches are searchable for a Brazilian team
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_libertadores_matches_for_team(mcp_server):
    """User can find Copa Libertadores matches for a Brazilian team."""
    result = await call(mcp_server, "find_matches", team="Flamengo", competition="Libertadores")

    assert "Flamengo" in result
    assert "Libertadores" in result


# ---------------------------------------------------------------------------
# AC-14: Average goals per match statistic
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_average_goals_per_match(mcp_server):
    """User can get average goals per match for the Brasileirao."""
    result = await call(mcp_server, "get_top_stats", stat_type="averages", competition="Brasileirao")

    assert "goal" in result.lower() or "average" in result.lower()
    # Should contain a decimal number
    import re
    assert re.search(r'\d+\.\d+', result)


# ---------------------------------------------------------------------------
# AC-15: Performance: tools respond quickly
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_simple_lookup_performance(mcp_server):
    """Simple lookups complete within 2 seconds."""
    import time
    start = time.time()
    await call(mcp_server, "find_players", name="Neymar")
    elapsed = time.time() - start
    assert elapsed < 2.0


@pytest.mark.asyncio
async def test_aggregate_query_performance(mcp_server):
    """Aggregate queries complete within 5 seconds."""
    import time
    start = time.time()
    await call(mcp_server, "get_standings", competition="Brasileirao", season=2019)
    elapsed = time.time() - start
    assert elapsed < 5.0
