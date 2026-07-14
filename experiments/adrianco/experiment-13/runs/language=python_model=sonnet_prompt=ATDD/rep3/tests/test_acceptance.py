"""
Acceptance tests for the Brazilian Soccer MCP Server.

These tests exercise only the public MCP tool interface - no access to internals.
Each test starts from a fresh server connection with no shared state.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.shared.memory import create_connected_server_and_client_session


def _load_server():
    from server import mcp
    return mcp


async def _call_tool(session, tool_name: str, arguments: dict) -> dict:
    result = await session.call_tool(tool_name, arguments)
    assert not result.isError, f"Tool {tool_name} returned error: {result.content}"
    assert result.content, f"Tool {tool_name} returned no content"
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# 1. Find matches between two specific teams (head-to-head search)
# ---------------------------------------------------------------------------

def test_find_matches_between_flamengo_and_fluminense():
    """Finding matches by two teams returns only matches where both teams appear."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "find_matches", {
                "team1": "Flamengo",
                "team2": "Fluminense",
                "limit": 100,
            })

        assert data["total_found"] > 0, "Should find Flamengo vs Fluminense matches"
        assert len(data["matches"]) > 0

        for match in data["matches"]:
            home = match["home_team"].lower()
            away = match["away_team"].lower()
            assert "flamengo" in home or "flamengo" in away, f"Flamengo missing: {match}"
            assert "fluminense" in home or "fluminense" in away, f"Fluminense missing: {match}"

        # Result includes basic match fields
        first = data["matches"][0]
        assert "date" in first
        assert "home_goals" in first
        assert "away_goals" in first
        assert "competition" in first

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 2. Find team matches filtered by season
# ---------------------------------------------------------------------------

def test_find_palmeiras_matches_in_2022():
    """Filtering matches by team and season returns only that team's matches from that year."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "find_matches", {
                "team": "Palmeiras",
                "season": 2022,
                "limit": 100,
            })

        assert data["total_found"] > 0, "Should find Palmeiras matches in 2022"

        for match in data["matches"]:
            home = match["home_team"].lower()
            away = match["away_team"].lower()
            assert "palmeiras" in home or "palmeiras" in away, (
                f"Palmeiras not in match: {match}"
            )
            assert match["season"] == 2022, f"Wrong season: {match['season']}"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 3. Team statistics structure and content
# ---------------------------------------------------------------------------

def test_get_team_stats_returns_wins_draws_losses():
    """Team stats include wins, draws, losses, goals, and a win rate."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "get_team_stats", {
                "team": "Flamengo",
                "competition": "brasileirao",
                "season": 2019,
            })

        assert data["team"] == "Flamengo"
        assert data["matches_played"] == 38, f"Brasileirao has 38 rounds: {data}"
        assert data["wins"] == 28
        assert data["draws"] == 6
        assert data["losses"] == 4
        assert data["points"] == 90
        assert "goals_for" in data
        assert "goals_against" in data
        assert "win_rate" in data

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 4. Player search by nationality
# ---------------------------------------------------------------------------

def test_find_players_by_nationality_brazil():
    """Searching for Brazilian players returns only players with Brazilian nationality."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "find_players", {
                "nationality": "Brazil",
                "limit": 50,
            })

        assert data["total_found"] > 0, "Should find Brazilian players"
        assert len(data["players"]) > 0

        for player in data["players"]:
            assert player["nationality"] == "Brazil", (
                f"Expected Brazil nationality, got: {player['nationality']}"
            )

        # Players have expected fields
        first = data["players"][0]
        assert "name" in first
        assert "overall" in first
        assert "position" in first
        assert "club" in first

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 5. Player search by club
# ---------------------------------------------------------------------------

def test_find_players_at_santos():
    """Searching players by club returns only players from that club."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "find_players", {
                "club": "Santos",
                "limit": 50,
            })

        assert data["total_found"] > 0, "Should find Santos players in FIFA data"

        for player in data["players"]:
            assert "santos" in player["club"].lower(), (
                f"Expected Santos club, got: {player['club']}"
            )

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 6. Head-to-head record between two teams
# ---------------------------------------------------------------------------

def test_get_head_to_head_palmeiras_vs_santos():
    """Head-to-head tool returns match count and win breakdown for each team."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "get_head_to_head", {
                "team1": "Palmeiras",
                "team2": "Santos",
            })

        assert data["team1"] == "Palmeiras"
        assert data["team2"] == "Santos"
        assert data["total_matches"] > 0, "Should find Palmeiras vs Santos matches"
        assert "team1_wins" in data
        assert "team2_wins" in data
        assert "draws" in data

        # Win totals + draws should equal total matches
        total = data["team1_wins"] + data["team2_wins"] + data["draws"]
        assert total == data["total_matches"], (
            f"Wins + draws ({total}) != total_matches ({data['total_matches']})"
        )

        assert "recent_matches" in data
        assert len(data["recent_matches"]) > 0

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 7. Competition standings – 2019 Brasileirao champion
# ---------------------------------------------------------------------------

def test_get_2019_brasileirao_standings_shows_flamengo_champion():
    """The 2019 Brasileirao standings should show Flamengo as the leader with 90 points."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "get_standings", {
                "season": 2019,
                "competition": "brasileirao",
            })

        assert data["season"] == 2019
        assert data["competition"] == "brasileirao"
        assert len(data["standings"]) > 0

        champion = data["standings"][0]
        assert "flamengo" in champion["team"].lower(), (
            f"Expected Flamengo as champion, got: {champion['team']}"
        )
        assert champion["points"] == 90, f"Flamengo should have 90 points, got {champion['points']}"

        # Standings entries have required fields
        for entry in data["standings"][:5]:
            assert "team" in entry
            assert "points" in entry
            assert "wins" in entry
            assert "draws" in entry
            assert "losses" in entry

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 8. Find matches filtered by competition
# ---------------------------------------------------------------------------

def test_find_copa_do_brasil_matches():
    """Filtering by competition returns only matches from that competition."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "find_matches", {
                "competition": "copa_do_brasil",
                "limit": 50,
            })

        assert data["total_found"] > 0, "Should find Copa do Brasil matches"

        for match in data["matches"]:
            assert "copa_do_brasil" in match["competition"].lower(), (
                f"Wrong competition: {match['competition']}"
            )

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 9. Statistical analysis – biggest wins
# ---------------------------------------------------------------------------

def test_get_statistics_biggest_wins_are_sorted_by_goal_difference():
    """Biggest wins statistic returns matches sorted by goal difference descending."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "get_statistics", {
                "stat_type": "biggest_wins",
                "limit": 10,
            })

        assert "results" in data
        assert len(data["results"]) > 0

        first = data["results"][0]
        assert "home_team" in first
        assert "away_team" in first
        assert "home_goals" in first
        assert "away_goals" in first
        assert "goal_difference" in first

        # Should be sorted descending by goal difference
        goal_diffs = [r["goal_difference"] for r in data["results"]]
        assert goal_diffs == sorted(goal_diffs, reverse=True), (
            "Results should be sorted by goal difference descending"
        )

        # The biggest win should have a large margin
        assert first["goal_difference"] >= 5, (
            f"Biggest win margin too small: {first['goal_difference']}"
        )

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 10. Player search by position
# ---------------------------------------------------------------------------

def test_find_players_by_goalkeeper_position():
    """Searching players by position GK returns only goalkeepers."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "find_players", {
                "position": "GK",
                "limit": 20,
            })

        assert data["total_found"] > 0, "Should find GK players"

        for player in data["players"]:
            assert player["position"] == "GK", (
                f"Expected GK, got: {player['position']}"
            )

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 11. All six CSV files are loadable (data coverage)
# ---------------------------------------------------------------------------

def test_all_competitions_return_data():
    """Querying each competition returns results, confirming all datasets are loaded."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            for competition in ["brasileirao", "copa_do_brasil", "libertadores"]:
                data = await _call_tool(session, "find_matches", {
                    "competition": competition,
                    "limit": 1,
                })
                assert data["total_found"] > 0, (
                    f"No matches found for competition: {competition}"
                )

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 12. Find Libertadores matches for a Brazilian team
# ---------------------------------------------------------------------------

def test_find_libertadores_matches_for_flamengo():
    """Can find Copa Libertadores matches for a specific team."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "find_matches", {
                "team": "Flamengo",
                "competition": "libertadores",
                "limit": 50,
            })

        assert data["total_found"] > 0, "Should find Flamengo Libertadores matches"

        for match in data["matches"]:
            home = match["home_team"].lower()
            away = match["away_team"].lower()
            assert "flamengo" in home or "flamengo" in away

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 13. Average goals per match statistic
# ---------------------------------------------------------------------------

def test_get_statistics_goals_per_match():
    """Goals per match statistic returns a reasonable average for Brasileirao."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "get_statistics", {
                "stat_type": "goals_per_match",
                "competition": "brasileirao",
            })

        assert "average_goals_per_match" in data
        avg = data["average_goals_per_match"]
        # Brazilian football averages ~2-3 goals per match
        assert 1.5 <= avg <= 4.0, f"Unreasonable goals per match average: {avg}"
        assert "total_matches" in data
        assert data["total_matches"] > 0

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 14. Top Brazilian players are correctly ranked
# ---------------------------------------------------------------------------

def test_find_top_brazilian_players_ranked_by_overall():
    """Brazilian players can be retrieved sorted by overall rating descending."""
    async def run():
        mcp = _load_server()
        async with create_connected_server_and_client_session(mcp) as session:
            data = await _call_tool(session, "find_players", {
                "nationality": "Brazil",
                "limit": 10,
            })

        assert len(data["players"]) == 10

        ratings = [p["overall"] for p in data["players"]]
        assert ratings == sorted(ratings, reverse=True), (
            "Players should be sorted by overall rating descending"
        )

    asyncio.run(run())
