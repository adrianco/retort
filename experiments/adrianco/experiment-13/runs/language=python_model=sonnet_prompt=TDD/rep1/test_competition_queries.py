"""Tests for competition standings and statistical analysis."""
import pytest
import pandas as pd
from data_loader import DataLoader
from competition_queries import (
    calculate_standings,
    get_biggest_wins,
    get_average_goals_per_match,
    get_home_win_rate,
    get_season_summary,
)

DATA_DIR = "data/kaggle"


@pytest.fixture(scope="module")
def loader():
    return DataLoader(DATA_DIR)


class TestCalculateStandings:
    def test_returns_list(self, loader):
        result = calculate_standings(loader.brasileirao, season=2019)
        assert isinstance(result, list)

    def test_not_empty(self, loader):
        result = calculate_standings(loader.brasileirao, season=2019)
        assert len(result) > 0

    def test_has_expected_keys(self, loader):
        result = calculate_standings(loader.brasileirao, season=2019)
        for row in result:
            for key in ["team", "points", "wins", "draws", "losses", "matches"]:
                assert key in row

    def test_sorted_by_points(self, loader):
        result = calculate_standings(loader.brasileirao, season=2019)
        points = [r["points"] for r in result]
        assert points == sorted(points, reverse=True)

    def test_points_formula(self, loader):
        result = calculate_standings(loader.brasileirao, season=2019)
        for row in result:
            expected_pts = row["wins"] * 3 + row["draws"]
            assert row["points"] == expected_pts

    def test_2019_flamengo_champion(self, loader):
        result = calculate_standings(loader.brasileirao, season=2019)
        if result:
            # Flamengo won the 2019 Brasileirao with 90 points
            assert "Flamengo" in result[0]["team"] or result[0]["points"] >= 85

    def test_historico_standings(self, loader):
        result = calculate_standings(loader.historico, season=2003)
        assert len(result) > 0

    def test_no_season_returns_all(self, loader):
        result = calculate_standings(loader.brasileirao)
        assert len(result) > 0


class TestGetBiggestWins:
    def test_returns_list(self, loader):
        result = get_biggest_wins(loader.brasileirao, limit=5)
        assert isinstance(result, list)

    def test_correct_number(self, loader):
        result = get_biggest_wins(loader.brasileirao, limit=5)
        assert len(result) <= 5

    def test_sorted_by_goal_difference(self, loader):
        result = get_biggest_wins(loader.brasileirao, limit=10)
        diffs = [r["goal_diff"] for r in result]
        assert diffs == sorted(diffs, reverse=True)

    def test_has_expected_keys(self, loader):
        result = get_biggest_wins(loader.brasileirao, limit=3)
        for r in result:
            assert "home_team" in r
            assert "away_team" in r
            assert "home_goal" in r
            assert "away_goal" in r
            assert "goal_diff" in r

    def test_goal_diff_correct(self, loader):
        result = get_biggest_wins(loader.brasileirao, limit=5)
        for r in result:
            assert r["goal_diff"] == abs(int(r["home_goal"]) - int(r["away_goal"]))


class TestGetAverageGoalsPerMatch:
    def test_returns_float(self, loader):
        result = get_average_goals_per_match(loader.brasileirao)
        assert isinstance(result, float)

    def test_positive_value(self, loader):
        result = get_average_goals_per_match(loader.brasileirao)
        assert result > 0

    def test_reasonable_range(self, loader):
        result = get_average_goals_per_match(loader.brasileirao)
        assert 1.0 < result < 10.0

    def test_season_filter(self, loader):
        r_all = get_average_goals_per_match(loader.brasileirao)
        r_2019 = get_average_goals_per_match(loader.brasileirao, season=2019)
        assert r_2019 > 0


class TestGetHomeWinRate:
    def test_returns_float(self, loader):
        result = get_home_win_rate(loader.brasileirao)
        assert isinstance(result, float)

    def test_between_zero_and_one(self, loader):
        result = get_home_win_rate(loader.brasileirao)
        assert 0 <= result <= 1

    def test_season_filter(self, loader):
        result = get_home_win_rate(loader.brasileirao, season=2019)
        assert 0 <= result <= 1


class TestGetSeasonSummary:
    def test_returns_dict(self, loader):
        result = get_season_summary(loader.brasileirao, season=2019)
        assert isinstance(result, dict)

    def test_has_expected_keys(self, loader):
        result = get_season_summary(loader.brasileirao, season=2019)
        for key in ["season", "total_matches", "total_goals", "avg_goals_per_match", "home_win_rate"]:
            assert key in result

    def test_total_goals_positive(self, loader):
        result = get_season_summary(loader.brasileirao, season=2019)
        assert result["total_goals"] > 0

    def test_season_matches_input(self, loader):
        result = get_season_summary(loader.brasileirao, season=2019)
        assert result["season"] == 2019
