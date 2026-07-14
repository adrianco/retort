"""Feature: Match Queries (from TASK.md BDD scenarios)."""

import pandas as pd
import pytest


class TestMatchQueries:
    """
    Scenario: Find matches between two teams
      Given the match data is loaded
      When I search for matches between 'Flamengo' and 'Fluminense'
      Then I should receive a list of matches
      And each match should have date, scores, and competition
    """

    def test_find_flamengo_vs_fluminense(self, knowledge):
        df = knowledge.find_matches(team="Flamengo", opponent="Fluminense")
        assert not df.empty
        for col in ["date", "competition", "home_goal", "away_goal"]:
            assert col in df.columns

    def test_find_matches_by_season(self, knowledge):
        df = knowledge.find_matches(team="Palmeiras", season=2023)
        assert not df.empty
        assert (df["season"] == 2023).all()

    def test_find_matches_by_competition(self, knowledge):
        df = knowledge.find_matches(competition="Copa Libertadores", limit=10)
        assert not df.empty
        assert df["competition"].str.contains("Libertadores", case=False).all()

    def test_find_matches_by_date_range(self, knowledge):
        df = knowledge.find_matches(
            team="Flamengo",
            date_from="2019-01-01",
            date_to="2019-12-31",
        )
        assert not df.empty
        # All matches have a date in 2019
        dates = df["date"].dropna()
        assert (dates.dt.year == 2019).all()

    def test_home_only_filter(self, knowledge):
        df = knowledge.find_matches(team="Flamengo", home_only=True, season=2019)
        assert (df["home_team"] == "flamengo").all()

    def test_away_only_filter(self, knowledge):
        df = knowledge.find_matches(team="Flamengo", away_only=True, season=2019)
        assert (df["away_team"] == "flamengo").all()

    def test_results_sorted_by_date(self, knowledge):
        df = knowledge.find_matches(team="Palmeiras", season=2019)
        dates = df["date"].dropna().tolist()
        assert dates == sorted(dates)

    def test_limit_respected(self, knowledge):
        df = knowledge.find_matches(competition="Brasileirão", limit=15)
        assert len(df) == 15


class TestHeadToHead:
    """
    Scenario: Head-to-head Flamengo vs Fluminense
    """

    def test_h2h_returns_dict_shape(self, knowledge):
        h2h = knowledge.head_to_head("Flamengo", "Fluminense")
        assert {"matches", "a_wins", "b_wins", "draws", "a_goals", "b_goals"} <= h2h.keys()
        assert h2h["matches"] > 0

    def test_h2h_results_sum_to_total(self, knowledge):
        h2h = knowledge.head_to_head("Palmeiras", "Corinthians")
        assert h2h["matches"] == h2h["a_wins"] + h2h["b_wins"] + h2h["draws"]

    def test_h2h_unknown_teams(self, knowledge):
        h2h = knowledge.head_to_head("Definitely Not A Team", "Also Not A Team")
        assert h2h["matches"] == 0
        assert h2h["records"] == []

    def test_h2h_records_contain_match_metadata(self, knowledge):
        h2h = knowledge.head_to_head("Palmeiras", "Corinthians")
        rec = h2h["records"][0]
        for key in ("date", "competition", "season", "home", "away", "home_goal", "away_goal"):
            assert key in rec
