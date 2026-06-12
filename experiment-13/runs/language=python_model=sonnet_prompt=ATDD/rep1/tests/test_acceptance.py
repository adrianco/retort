"""
Acceptance tests for the Brazilian Soccer MCP Server.

Each test exercises the server only through the public MCP tool interface
(JSON-RPC protocol layer) — no direct access to internal data structures.
Tests are atomic and independent; each gets a fresh server session.
"""
import asyncio
import json
import os
import sys

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")


@pytest.fixture
async def client():
    """
    Create an in-process MCP session backed by a fresh server instance.

    The MCP session (which uses anyio task groups internally) is kept entirely
    within a single asyncio Task so that anyio's cancel-scope never crosses a
    task boundary during fixture teardown.
    """
    from server import build_server

    server_instance = build_server(DATA_DIR)
    session_ref: list = []
    session_ready: asyncio.Event = asyncio.Event()
    test_done: asyncio.Event = asyncio.Event()
    error_ref: list = []

    async def _manage():
        try:
            async with create_connected_server_and_client_session(server_instance) as session:
                session_ref.append(session)
                session_ready.set()
                await test_done.wait()
        except Exception as exc:
            error_ref.append(exc)
            session_ready.set()

    task = asyncio.ensure_future(_manage())
    await session_ready.wait()

    if error_ref:
        task.cancel()
        raise error_ref[0]

    yield session_ref[0]

    test_done.set()
    try:
        await asyncio.wait_for(task, timeout=10)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        task.cancel()


async def call_tool(session, tool_name: str, **kwargs) -> dict:
    """Call an MCP tool and return the parsed JSON result."""
    result = await session.call_tool(tool_name, kwargs)
    assert not result.isError, f"Tool {tool_name} returned error: {result.content}"
    assert result.content, f"Tool {tool_name} returned no content"
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# Tool Discovery
# ---------------------------------------------------------------------------

class TestToolDiscovery:
    async def test_server_exposes_required_tools(self, client):
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        assert "find_matches" in names
        assert "get_team_stats" in names
        assert "find_players" in names
        assert "get_standings" in names
        assert "get_statistics" in names


# ---------------------------------------------------------------------------
# Match Queries
# ---------------------------------------------------------------------------

class TestMatchQueries:
    async def test_find_flamengo_matches_returns_results(self, client):
        result = await call_tool(client, "find_matches", team="Flamengo")
        assert result["total_found"] > 0
        assert len(result["matches"]) > 0

    async def test_every_returned_match_involves_requested_team(self, client):
        result = await call_tool(client, "find_matches", team="Flamengo", limit=50)
        for match in result["matches"]:
            involves = (
                "Flamengo" in match["home_team"]
                or "Flamengo" in match["away_team"]
            )
            assert involves, f"Match does not involve Flamengo: {match}"

    async def test_head_to_head_matches_involve_both_teams(self, client):
        result = await call_tool(
            client, "find_matches", team="Flamengo", opponent="Fluminense"
        )
        assert result["total_found"] > 0
        for match in result["matches"]:
            has_fla = "Flamengo" in match["home_team"] or "Flamengo" in match["away_team"]
            has_flu = "Fluminense" in match["home_team"] or "Fluminense" in match["away_team"]
            assert has_fla and has_flu, f"Not a Fla-Flu match: {match}"

    async def test_filter_by_copa_do_brasil_competition(self, client):
        result = await call_tool(client, "find_matches", competition="copa_do_brasil", limit=20)
        assert result["total_found"] > 0
        for match in result["matches"]:
            assert match["competition"] == "copa_do_brasil"

    async def test_filter_by_brasileirao_competition(self, client):
        result = await call_tool(client, "find_matches", competition="brasileirao", limit=20)
        assert result["total_found"] > 0
        for match in result["matches"]:
            assert match["competition"] == "brasileirao"

    async def test_filter_by_libertadores_competition(self, client):
        result = await call_tool(client, "find_matches", competition="libertadores", limit=20)
        assert result["total_found"] > 0
        for match in result["matches"]:
            assert match["competition"] == "libertadores"

    async def test_filter_by_season_returns_only_that_season(self, client):
        result = await call_tool(
            client, "find_matches", season=2022, competition="brasileirao"
        )
        assert result["total_found"] > 0
        for match in result["matches"]:
            assert match["season"] == 2022

    async def test_matches_include_score_fields(self, client):
        result = await call_tool(client, "find_matches", team="Palmeiras", season=2022)
        assert result["total_found"] > 0
        for match in result["matches"]:
            assert match["home_goal"] is not None
            assert match["away_goal"] is not None

    async def test_limit_parameter_caps_returned_matches(self, client):
        result = await call_tool(client, "find_matches", team="Flamengo", limit=7)
        assert len(result["matches"]) <= 7

    async def test_filter_by_date_range(self, client):
        result = await call_tool(
            client, "find_matches", date_from="2022-01-01", date_to="2022-12-31"
        )
        assert result["total_found"] > 0
        for match in result["matches"]:
            assert match["date"] >= "2022-01-01"
            assert match["date"] <= "2022-12-31"

    async def test_matches_include_required_fields(self, client):
        result = await call_tool(client, "find_matches", team="Corinthians", limit=5)
        required = {"date", "home_team", "away_team", "home_goal", "away_goal", "competition", "season"}
        for match in result["matches"]:
            for field in required:
                assert field in match, f"Missing field '{field}' in match: {match}"


# ---------------------------------------------------------------------------
# Team Statistics
# ---------------------------------------------------------------------------

class TestTeamStatistics:
    async def test_team_stats_include_all_required_fields(self, client):
        result = await call_tool(client, "get_team_stats", team="Palmeiras")
        required = ["team", "matches", "wins", "draws", "losses",
                    "goals_for", "goals_against", "win_rate"]
        for field in required:
            assert field in result, f"Missing field: {field}"

    async def test_win_draw_loss_sum_equals_total_matches(self, client):
        result = await call_tool(
            client, "get_team_stats", team="Corinthians",
            competition="brasileirao", season=2022
        )
        assert result["matches"] > 0
        assert result["wins"] + result["draws"] + result["losses"] == result["matches"]

    async def test_win_rate_is_percentage_between_0_and_100(self, client):
        result = await call_tool(client, "get_team_stats", team="Santos")
        assert 0 <= result["win_rate"] <= 100

    async def test_goals_are_non_negative(self, client):
        result = await call_tool(client, "get_team_stats", team="Flamengo")
        assert result["goals_for"] >= 0
        assert result["goals_against"] >= 0

    async def test_nonexistent_team_returns_zero_matches(self, client):
        result = await call_tool(client, "get_team_stats", team="Nonexistent Team XYZ999")
        assert result["matches"] == 0

    async def test_team_stats_can_be_filtered_by_competition_and_season(self, client):
        result_full = await call_tool(client, "get_team_stats", team="Palmeiras")
        result_filtered = await call_tool(
            client, "get_team_stats", team="Palmeiras",
            competition="brasileirao", season=2022
        )
        assert result_filtered["matches"] < result_full["matches"]


# ---------------------------------------------------------------------------
# Player Queries
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    async def test_find_brazilian_players_returns_results(self, client):
        result = await call_tool(client, "find_players", nationality="Brazil")
        assert result["total_found"] > 0
        assert len(result["players"]) > 0

    async def test_all_returned_players_match_nationality_filter(self, client):
        result = await call_tool(client, "find_players", nationality="Brazil")
        for player in result["players"]:
            assert "Brazil" in player["nationality"]

    async def test_find_players_at_fluminense(self, client):
        # FIFA data uses "Fluminense" (not "Flamengo") for the main Brazilian club
        result = await call_tool(client, "find_players", club="Fluminense")
        assert result["total_found"] > 0
        for player in result["players"]:
            assert "Fluminense" in player["club"]

    async def test_find_player_by_name(self, client):
        result = await call_tool(client, "find_players", name="Neymar")
        assert result["total_found"] > 0
        for player in result["players"]:
            assert "Neymar" in player["name"]

    async def test_player_records_include_required_fields(self, client):
        result = await call_tool(client, "find_players", nationality="Brazil", limit=5)
        required = ["name", "nationality", "club", "position", "overall"]
        for player in result["players"]:
            for field in required:
                assert field in player, f"Missing player field: {field}"

    async def test_min_rating_filter_excludes_lower_rated_players(self, client):
        result = await call_tool(client, "find_players", nationality="Brazil", min_rating=85)
        assert result["total_found"] > 0
        for player in result["players"]:
            assert player["overall"] >= 85

    async def test_player_limit_is_respected(self, client):
        result = await call_tool(client, "find_players", nationality="Brazil", limit=5)
        assert len(result["players"]) <= 5

    async def test_players_sorted_by_overall_rating_descending(self, client):
        result = await call_tool(client, "find_players", nationality="Brazil", limit=10)
        ratings = [p["overall"] for p in result["players"] if p["overall"] is not None]
        assert ratings == sorted(ratings, reverse=True)


# ---------------------------------------------------------------------------
# Competition Standings
# ---------------------------------------------------------------------------

class TestCompetitionStandings:
    async def test_2019_brasileirao_has_standings(self, client):
        result = await call_tool(client, "get_standings", season=2019, competition="brasileirao")
        assert result["total_matches"] > 0
        assert len(result["standings"]) > 0

    async def test_standings_include_required_fields(self, client):
        result = await call_tool(client, "get_standings", season=2022, competition="brasileirao")
        required = ["team", "played", "won", "drawn", "lost", "points", "position"]
        for entry in result["standings"]:
            for field in required:
                assert field in entry, f"Missing standings field: {field}"

    async def test_standings_math_is_consistent(self, client):
        result = await call_tool(client, "get_standings", season=2019, competition="brasileirao")
        for entry in result["standings"]:
            assert entry["won"] + entry["drawn"] + entry["lost"] == entry["played"]
            expected_pts = entry["won"] * 3 + entry["drawn"]
            assert entry["points"] == expected_pts, \
                f"Points mismatch for {entry['team']}: expected {expected_pts}, got {entry['points']}"

    async def test_leader_has_most_points(self, client):
        result = await call_tool(client, "get_standings", season=2019, competition="brasileirao")
        table = result["standings"]
        assert table[0]["points"] >= table[-1]["points"]

    async def test_positions_are_sequential_from_one(self, client):
        result = await call_tool(client, "get_standings", season=2019, competition="brasileirao")
        for i, entry in enumerate(result["standings"]):
            assert entry["position"] == i + 1

    async def test_flamengo_won_2019_brasileirao(self, client):
        result = await call_tool(client, "get_standings", season=2019, competition="brasileirao")
        champion = result["standings"][0]
        assert "Flamengo" in champion["team"], \
            f"Expected Flamengo as 2019 champion, got: {champion['team']}"


# ---------------------------------------------------------------------------
# Statistical Analysis
# ---------------------------------------------------------------------------

class TestStatisticalAnalysis:
    async def test_biggest_wins_returns_results(self, client):
        result = await call_tool(client, "get_statistics", stat_type="biggest_wins")
        assert len(result["results"]) > 0

    async def test_biggest_wins_sorted_by_goal_difference(self, client):
        result = await call_tool(client, "get_statistics", stat_type="biggest_wins", limit=10)
        wins = result["results"]
        for i in range(len(wins) - 1):
            assert wins[i]["goal_difference"] >= wins[i + 1]["goal_difference"]

    async def test_biggest_wins_goal_difference_matches_score(self, client):
        result = await call_tool(client, "get_statistics", stat_type="biggest_wins", limit=5)
        for win in result["results"]:
            expected_diff = abs(win["home_goal"] - win["away_goal"])
            assert win["goal_difference"] == expected_diff

    async def test_avg_goals_returns_positive_value(self, client):
        result = await call_tool(client, "get_statistics", stat_type="avg_goals",
                                  competition="brasileirao")
        assert result["avg_goals_per_match"] > 0
        assert result["total_matches"] > 0

    async def test_home_record_percentages_are_valid(self, client):
        result = await call_tool(client, "get_statistics", stat_type="home_record",
                                  competition="brasileirao")
        assert result["total_matches"] > 0
        total = result["home_wins"] + result["home_draws"] + result["home_losses"]
        assert total == result["total_matches"]
        assert 0 <= result["home_win_rate"] <= 100

    async def test_statistics_can_filter_by_season(self, client):
        result_all = await call_tool(client, "get_statistics", stat_type="avg_goals",
                                      competition="brasileirao")
        result_2022 = await call_tool(client, "get_statistics", stat_type="avg_goals",
                                       competition="brasileirao", season=2022)
        assert result_2022["total_matches"] < result_all["total_matches"]

    async def test_biggest_wins_limit_is_respected(self, client):
        result = await call_tool(client, "get_statistics", stat_type="biggest_wins", limit=5)
        assert len(result["results"]) <= 5
