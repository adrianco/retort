"""Tests for match query functions."""
import pytest
import pandas as pd
from data_loader import DataLoader
from match_queries import (
    search_matches_by_team,
    search_matches_head_to_head,
    search_matches_by_season,
    search_matches_by_competition,
    search_matches_by_date_range,
    format_match_result,
    head_to_head_summary,
)

DATA_DIR = "data/kaggle"


@pytest.fixture(scope="module")
def loader():
    return DataLoader(DATA_DIR)


class TestSearchMatchesByTeam:
    def test_finds_flamengo_matches(self, loader):
        results = search_matches_by_team(loader.all_matches, "Flamengo")
        assert len(results) > 0

    def test_finds_team_as_home_or_away(self, loader):
        results = search_matches_by_team(loader.all_matches, "Palmeiras")
        home = results[results["home_team"].str.contains("Palmeiras", case=False, na=False)]
        away = results[results["away_team"].str.contains("Palmeiras", case=False, na=False)]
        assert len(home) > 0
        assert len(away) > 0

    def test_case_insensitive(self, loader):
        r1 = search_matches_by_team(loader.all_matches, "flamengo")
        r2 = search_matches_by_team(loader.all_matches, "Flamengo")
        assert len(r1) == len(r2)

    def test_home_only_filter(self, loader):
        results = search_matches_by_team(loader.all_matches, "Flamengo", home_only=True)
        assert all(results["home_team"].str.contains("Flamengo", case=False, na=False))

    def test_away_only_filter(self, loader):
        results = search_matches_by_team(loader.all_matches, "Flamengo", away_only=True)
        assert all(results["away_team"].str.contains("Flamengo", case=False, na=False))

    def test_returns_dataframe(self, loader):
        results = search_matches_by_team(loader.all_matches, "Santos")
        assert isinstance(results, pd.DataFrame)

    def test_no_results_for_unknown_team(self, loader):
        results = search_matches_by_team(loader.all_matches, "TeamXYZDoesNotExist")
        assert len(results) == 0


class TestSearchMatchesHeadToHead:
    def test_finds_flamengo_vs_fluminense(self, loader):
        results = search_matches_head_to_head(loader.all_matches, "Flamengo", "Fluminense")
        assert len(results) > 0

    def test_bidirectional(self, loader):
        r1 = search_matches_head_to_head(loader.all_matches, "Flamengo", "Fluminense")
        r2 = search_matches_head_to_head(loader.all_matches, "Fluminense", "Flamengo")
        assert len(r1) == len(r2)

    def test_each_match_contains_both_teams(self, loader):
        results = search_matches_head_to_head(loader.all_matches, "Palmeiras", "Santos")
        for _, row in results.iterrows():
            teams = {row["home_team"], row["away_team"]}
            assert any("Palmeiras" in t for t in teams)
            assert any("Santos" in t for t in teams)


class TestSearchMatchesBySeason:
    def test_finds_matches_in_2019(self, loader):
        results = search_matches_by_season(loader.brasileirao, 2019)
        assert len(results) > 0

    def test_all_results_have_correct_season(self, loader):
        results = search_matches_by_season(loader.brasileirao, 2019)
        assert (results["season"] == 2019).all()

    def test_no_results_for_future_season(self, loader):
        results = search_matches_by_season(loader.brasileirao, 2099)
        assert len(results) == 0


class TestSearchMatchesByCompetition:
    def test_finds_brasileirao(self, loader):
        results = search_matches_by_competition(loader.all_matches, "Brasileirão")
        assert len(results) > 0

    def test_finds_copa_brasil(self, loader):
        results = search_matches_by_competition(loader.all_matches, "Copa do Brasil")
        assert len(results) > 0

    def test_finds_libertadores(self, loader):
        results = search_matches_by_competition(loader.all_matches, "Libertadores")
        assert len(results) > 0

    def test_case_insensitive(self, loader):
        r1 = search_matches_by_competition(loader.all_matches, "brasileirão")
        r2 = search_matches_by_competition(loader.all_matches, "Brasileirão")
        assert len(r1) == len(r2)


class TestSearchMatchesByDateRange:
    def test_finds_matches_in_range(self, loader):
        results = search_matches_by_date_range(loader.all_matches, "2019-01-01", "2019-12-31")
        assert len(results) > 0

    def test_respects_start_date(self, loader):
        results = search_matches_by_date_range(loader.all_matches, "2020-01-01", "2020-12-31")
        assert (results["date"] >= pd.Timestamp("2020-01-01")).all()

    def test_respects_end_date(self, loader):
        results = search_matches_by_date_range(loader.all_matches, "2020-01-01", "2020-12-31")
        assert (results["date"] <= pd.Timestamp("2020-12-31")).all()


class TestFormatMatchResult:
    def test_basic_format(self):
        row = pd.Series({
            "date": pd.Timestamp("2023-09-03"),
            "home_team": "Flamengo",
            "away_team": "Fluminense",
            "home_goal": 2,
            "away_goal": 1,
            "competition": "Brasileirão Serie A",
        })
        result = format_match_result(row)
        assert "Flamengo" in result
        assert "Fluminense" in result
        assert "2" in result
        assert "1" in result
        assert "2023" in result

    def test_includes_competition(self):
        row = pd.Series({
            "date": pd.Timestamp("2023-09-03"),
            "home_team": "Flamengo",
            "away_team": "Fluminense",
            "home_goal": 2,
            "away_goal": 1,
            "competition": "Brasileirão Serie A",
        })
        result = format_match_result(row)
        assert "Brasileirão" in result or "Serie A" in result


class TestHeadToHeadSummary:
    def test_returns_dict(self, loader):
        matches = search_matches_head_to_head(loader.all_matches, "Flamengo", "Fluminense")
        summary = head_to_head_summary(matches, "Flamengo", "Fluminense")
        assert isinstance(summary, dict)

    def test_has_win_counts(self, loader):
        matches = search_matches_head_to_head(loader.all_matches, "Flamengo", "Fluminense")
        summary = head_to_head_summary(matches, "Flamengo", "Fluminense")
        assert "team1_wins" in summary
        assert "team2_wins" in summary
        assert "draws" in summary

    def test_totals_add_up(self, loader):
        matches = search_matches_head_to_head(loader.all_matches, "Flamengo", "Fluminense")
        summary = head_to_head_summary(matches, "Flamengo", "Fluminense")
        total = summary["team1_wins"] + summary["team2_wins"] + summary["draws"]
        assert total == summary["total_matches"]
