"""Tests for the MCP server tool handlers."""
import pytest
import json
from server import (
    handle_search_matches,
    handle_head_to_head,
    handle_team_stats,
    handle_search_players,
    handle_top_players,
    handle_standings,
    handle_biggest_wins,
    handle_season_summary,
    handle_team_record,
)

DATA_DIR = "data/kaggle"


class TestHandleSearchMatches:
    def test_returns_string(self):
        result = handle_search_matches(team="Flamengo", data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_finds_flamengo(self):
        result = handle_search_matches(team="Flamengo", data_dir=DATA_DIR)
        assert "Flamengo" in result

    def test_finds_by_season(self):
        result = handle_search_matches(team="Palmeiras", season=2023, data_dir=DATA_DIR)
        assert "Palmeiras" in result

    def test_finds_by_competition(self):
        result = handle_search_matches(competition="Libertadores", data_dir=DATA_DIR)
        assert len(result) > 0

    def test_no_matches_returns_message(self):
        result = handle_search_matches(team="TeamXYZUnknown999", data_dir=DATA_DIR)
        assert "no matches" in result.lower() or "not found" in result.lower() or "0" in result

    def test_limit_parameter(self):
        result = handle_search_matches(team="Flamengo", limit=5, data_dir=DATA_DIR)
        assert isinstance(result, str)
        assert "Flamengo" in result


class TestHandleHeadToHead:
    def test_returns_string(self):
        result = handle_head_to_head(team1="Flamengo", team2="Fluminense", data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_contains_both_teams(self):
        result = handle_head_to_head(team1="Flamengo", team2="Fluminense", data_dir=DATA_DIR)
        assert "Flamengo" in result
        assert "Fluminense" in result

    def test_contains_win_counts(self):
        result = handle_head_to_head(team1="Flamengo", team2="Fluminense", data_dir=DATA_DIR)
        assert "win" in result.lower() or "W:" in result or "wins" in result.lower()

    def test_no_matches_returns_message(self):
        result = handle_head_to_head(team1="TeamAAA", team2="TeamBBB", data_dir=DATA_DIR)
        assert isinstance(result, str)


class TestHandleTeamStats:
    def test_returns_string(self):
        result = handle_team_stats(team="Flamengo", data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_contains_team_name(self):
        result = handle_team_stats(team="Flamengo", data_dir=DATA_DIR)
        assert "Flamengo" in result

    def test_contains_record_info(self):
        result = handle_team_stats(team="Corinthians", data_dir=DATA_DIR)
        assert any(kw in result.lower() for kw in ["win", "draw", "loss", "match"])

    def test_season_filter(self):
        result = handle_team_stats(team="Flamengo", season=2019, data_dir=DATA_DIR)
        assert isinstance(result, str)
        assert "Flamengo" in result


class TestHandleSearchPlayers:
    def test_returns_string(self):
        result = handle_search_players(name="Neymar", data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_finds_neymar(self):
        result = handle_search_players(name="Neymar", data_dir=DATA_DIR)
        assert "Neymar" in result

    def test_finds_by_nationality(self):
        result = handle_search_players(nationality="Brazil", data_dir=DATA_DIR)
        assert "Brazil" in result

    def test_finds_by_club(self):
        result = handle_search_players(club="Fluminense", data_dir=DATA_DIR)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_results_message(self):
        result = handle_search_players(name="XYZUnknownPlayer999", data_dir=DATA_DIR)
        assert isinstance(result, str)


class TestHandleTopPlayers:
    def test_returns_string(self):
        result = handle_top_players(data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_contains_player_info(self):
        result = handle_top_players(data_dir=DATA_DIR)
        assert "Overall" in result or "overall" in result.lower()

    def test_nationality_filter(self):
        result = handle_top_players(nationality="Brazil", data_dir=DATA_DIR)
        assert "Brazil" in result

    def test_limit(self):
        result = handle_top_players(limit=3, data_dir=DATA_DIR)
        assert isinstance(result, str)


class TestHandleStandings:
    def test_returns_string(self):
        result = handle_standings(season=2019, data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_contains_flamengo(self):
        result = handle_standings(season=2019, data_dir=DATA_DIR)
        assert "Flamengo" in result

    def test_contains_points(self):
        result = handle_standings(season=2019, data_dir=DATA_DIR)
        assert "pts" in result.lower() or "points" in result.lower() or "Pts" in result

    def test_historico_season(self):
        result = handle_standings(season=2003, competition="historico", data_dir=DATA_DIR)
        assert isinstance(result, str)
        assert len(result) > 0


class TestHandleBiggestWins:
    def test_returns_string(self):
        result = handle_biggest_wins(data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_contains_match_info(self):
        result = handle_biggest_wins(data_dir=DATA_DIR)
        assert "-" in result or "vs" in result.lower()

    def test_season_filter(self):
        result = handle_biggest_wins(season=2019, data_dir=DATA_DIR)
        assert isinstance(result, str)


class TestHandleSeasonSummary:
    def test_returns_string(self):
        result = handle_season_summary(season=2019, data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_contains_stats(self):
        result = handle_season_summary(season=2019, data_dir=DATA_DIR)
        assert any(kw in result.lower() for kw in ["goals", "matches", "average"])

    def test_contains_season(self):
        result = handle_season_summary(season=2019, data_dir=DATA_DIR)
        assert "2019" in result


class TestHandleTeamRecord:
    def test_returns_string(self):
        result = handle_team_record(team="Flamengo", data_dir=DATA_DIR)
        assert isinstance(result, str)

    def test_contains_team_name(self):
        result = handle_team_record(team="Flamengo", data_dir=DATA_DIR)
        assert "Flamengo" in result

    def test_season_filter(self):
        result = handle_team_record(team="Corinthians", season=2022, data_dir=DATA_DIR)
        assert isinstance(result, str)
        assert "Corinthians" in result
