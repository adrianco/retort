"""Tests for server.py MCP tool handlers."""
import os
import json
import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "kaggle")


@pytest.fixture(scope="module")
def tools():
    """Return the dict of tool handler functions from server.py."""
    import server
    return server.get_tool_handlers(DATA_DIR)


# ─── Cycle 1: Tool registration ──────────────────────────────────────────────

def test_all_tools_registered(tools):
    expected = {
        "find_matches", "team_stats", "head_to_head",
        "find_players", "season_standings",
        "biggest_wins", "average_goals", "home_win_rate", "top_scoring_teams",
    }
    assert expected.issubset(set(tools.keys()))


# ─── Cycle 2: find_matches tool ──────────────────────────────────────────────

def test_find_matches_tool_returns_text(tools):
    result = tools["find_matches"](team="Flamengo", limit=5)
    assert isinstance(result, str)
    assert len(result) > 0


def test_find_matches_tool_contains_team_name(tools):
    result = tools["find_matches"](team="Palmeiras", limit=5)
    assert "Palmeiras" in result


def test_find_matches_tool_with_both_teams(tools):
    result = tools["find_matches"](team="Flamengo", team2="Fluminense", limit=5)
    assert "Flamengo" in result or "Fluminense" in result


def test_find_matches_tool_no_results(tools):
    result = tools["find_matches"](team="NonExistentTeamXYZ")
    assert "no matches" in result.lower() or "0" in result


# ─── Cycle 3: team_stats tool ────────────────────────────────────────────────

def test_team_stats_tool_returns_text(tools):
    result = tools["team_stats"](team="Corinthians")
    assert isinstance(result, str)
    assert len(result) > 0


def test_team_stats_tool_contains_win_draw_loss(tools):
    result = tools["team_stats"](team="Flamengo")
    assert "wins" in result.lower() or "win" in result.lower()


def test_team_stats_tool_contains_goals(tools):
    result = tools["team_stats"](team="Flamengo")
    assert "goal" in result.lower()


# ─── Cycle 4: head_to_head tool ──────────────────────────────────────────────

def test_head_to_head_tool_returns_text(tools):
    result = tools["head_to_head"](team1="Flamengo", team2="Fluminense")
    assert isinstance(result, str)
    assert len(result) > 0


def test_head_to_head_tool_mentions_both_teams(tools):
    result = tools["head_to_head"](team1="Flamengo", team2="Fluminense")
    assert "Flamengo" in result and "Fluminense" in result


# ─── Cycle 5: find_players tool ──────────────────────────────────────────────

def test_find_players_tool_returns_text(tools):
    result = tools["find_players"](name="Neymar")
    assert isinstance(result, str)
    assert len(result) > 0


def test_find_players_tool_by_nationality(tools):
    result = tools["find_players"](nationality="Brazil", limit=5)
    assert "Brazil" in result


def test_find_players_tool_no_results(tools):
    result = tools["find_players"](name="ZZZ_NoSuchPlayer_999")
    assert "no players" in result.lower() or "0" in result


# ─── Cycle 6: season_standings tool ─────────────────────────────────────────

def test_season_standings_tool_returns_text(tools):
    result = tools["season_standings"](season=2019, competition="Brasileirão")
    assert isinstance(result, str)
    assert len(result) > 0


def test_season_standings_tool_contains_flamengo_2019(tools):
    result = tools["season_standings"](season=2019, competition="Brasileirão")
    assert "Flamengo" in result


# ─── Cycle 7: stats tools ────────────────────────────────────────────────────

def test_biggest_wins_tool_returns_text(tools):
    result = tools["biggest_wins"](competition="Brasileirão", limit=5)
    assert isinstance(result, str)
    assert len(result) > 0


def test_average_goals_tool_returns_text(tools):
    result = tools["average_goals"](competition="Brasileirão")
    assert isinstance(result, str)
    assert "2." in result or "1." in result or "3." in result


def test_home_win_rate_tool_returns_text(tools):
    result = tools["home_win_rate"](competition="Brasileirão")
    assert isinstance(result, str)
    assert "%" in result


def test_top_scoring_teams_tool_returns_text(tools):
    result = tools["top_scoring_teams"](competition="Brasileirão", season=2022, limit=5)
    assert isinstance(result, str)
    assert len(result) > 0
