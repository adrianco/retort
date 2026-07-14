"""Tests for team query and statistics functions."""
import pytest
import pandas as pd
from data_loader import DataLoader
from team_queries import (
    get_team_record,
    get_team_goals,
    get_home_record,
    get_away_record,
    get_top_scoring_teams,
    get_best_home_records,
    get_best_away_records,
)

DATA_DIR = "data/kaggle"


@pytest.fixture(scope="module")
def loader():
    return DataLoader(DATA_DIR)


class TestGetTeamRecord:
    def test_returns_dict(self, loader):
        record = get_team_record(loader.brasileirao, "Flamengo")
        assert isinstance(record, dict)

    def test_has_expected_keys(self, loader):
        record = get_team_record(loader.brasileirao, "Flamengo")
        for key in ["wins", "draws", "losses", "matches"]:
            assert key in record

    def test_totals_add_up(self, loader):
        record = get_team_record(loader.brasileirao, "Flamengo")
        assert record["wins"] + record["draws"] + record["losses"] == record["matches"]

    def test_flamengo_has_matches(self, loader):
        record = get_team_record(loader.brasileirao, "Flamengo")
        assert record["matches"] > 0

    def test_unknown_team_returns_zeros(self, loader):
        record = get_team_record(loader.brasileirao, "TeamXYZUnknown")
        assert record["matches"] == 0

    def test_season_filter(self, loader):
        r_all = get_team_record(loader.brasileirao, "Flamengo")
        r_2019 = get_team_record(loader.brasileirao, "Flamengo", season=2019)
        assert r_2019["matches"] <= r_all["matches"]
        assert r_2019["matches"] > 0


class TestGetTeamGoals:
    def test_returns_dict(self, loader):
        goals = get_team_goals(loader.brasileirao, "Palmeiras")
        assert isinstance(goals, dict)

    def test_has_scored_and_conceded(self, loader):
        goals = get_team_goals(loader.brasileirao, "Palmeiras")
        assert "scored" in goals
        assert "conceded" in goals

    def test_scored_is_positive(self, loader):
        goals = get_team_goals(loader.brasileirao, "Palmeiras")
        assert goals["scored"] > 0

    def test_unknown_team_returns_zeros(self, loader):
        goals = get_team_goals(loader.brasileirao, "TeamXYZUnknown")
        assert goals["scored"] == 0
        assert goals["conceded"] == 0


class TestGetHomeRecord:
    def test_returns_dict(self, loader):
        record = get_home_record(loader.brasileirao, "Corinthians")
        assert isinstance(record, dict)

    def test_only_home_matches(self, loader):
        record = get_home_record(loader.brasileirao, "Corinthians")
        assert record["matches"] > 0

    def test_has_win_rate(self, loader):
        record = get_home_record(loader.brasileirao, "Corinthians")
        assert "win_rate" in record
        assert 0 <= record["win_rate"] <= 1

    def test_season_filter(self, loader):
        r_all = get_home_record(loader.brasileirao, "Corinthians")
        r_2022 = get_home_record(loader.brasileirao, "Corinthians", season=2022)
        assert r_2022["matches"] <= r_all["matches"]


class TestGetAwayRecord:
    def test_returns_dict(self, loader):
        record = get_away_record(loader.brasileirao, "Flamengo")
        assert isinstance(record, dict)

    def test_has_expected_keys(self, loader):
        record = get_away_record(loader.brasileirao, "Flamengo")
        for key in ["wins", "draws", "losses", "matches", "win_rate"]:
            assert key in record


class TestGetTopScoringTeams:
    def test_returns_list(self, loader):
        result = get_top_scoring_teams(loader.brasileirao, season=2019, limit=5)
        assert isinstance(result, list)

    def test_returns_correct_number(self, loader):
        result = get_top_scoring_teams(loader.brasileirao, season=2019, limit=5)
        assert len(result) <= 5

    def test_sorted_by_goals(self, loader):
        result = get_top_scoring_teams(loader.brasileirao, season=2019, limit=5)
        goals = [r["goals_scored"] for r in result]
        assert goals == sorted(goals, reverse=True)

    def test_has_team_name(self, loader):
        result = get_top_scoring_teams(loader.brasileirao, season=2019, limit=3)
        for r in result:
            assert "team" in r
            assert "goals_scored" in r


class TestGetBestHomeRecords:
    def test_returns_list(self, loader):
        result = get_best_home_records(loader.brasileirao, season=2019, limit=5)
        assert isinstance(result, list)

    def test_sorted_by_win_rate(self, loader):
        result = get_best_home_records(loader.brasileirao, season=2019, limit=10)
        rates = [r["win_rate"] for r in result]
        assert rates == sorted(rates, reverse=True)

    def test_has_expected_keys(self, loader):
        result = get_best_home_records(loader.brasileirao, season=2019, limit=3)
        for r in result:
            assert "team" in r
            assert "win_rate" in r
            assert "wins" in r
            assert "matches" in r


class TestGetBestAwayRecords:
    def test_returns_list(self, loader):
        result = get_best_away_records(loader.brasileirao, season=2019, limit=5)
        assert isinstance(result, list)

    def test_sorted_by_win_rate(self, loader):
        result = get_best_away_records(loader.brasileirao, season=2019, limit=10)
        rates = [r["win_rate"] for r in result]
        assert rates == sorted(rates, reverse=True)
