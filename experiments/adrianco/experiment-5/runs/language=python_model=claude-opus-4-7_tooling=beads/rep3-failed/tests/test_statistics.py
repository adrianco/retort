"""Feature: Statistical Analysis."""

import pytest


class TestAverageGoals:
    """
    Scenario: Aggregate statistics for a competition
    """

    def test_average_goals_brasileirao(self, knowledge):
        stats = knowledge.average_goals(competition="Brasileirão Série A")
        assert stats["matches"] > 0
        assert 0.0 < stats["avg_goals_per_match"] < 10.0
        # Home win rate is historically higher than away in Brazilian league
        assert stats["home_win_rate"] > stats["away_win_rate"]

    def test_rates_sum_to_one(self, knowledge):
        stats = knowledge.average_goals(competition="Brasileirão Série A", season=2019)
        s = stats["home_win_rate"] + stats["away_win_rate"] + stats["draw_rate"]
        assert abs(s - 1.0) < 0.01

    def test_empty_filter(self, knowledge):
        stats = knowledge.average_goals(season=1700)
        assert stats["matches"] == 0


class TestBiggestWins:
    def test_biggest_wins_sorted_by_margin(self, knowledge):
        df = knowledge.biggest_wins(limit=10)
        margins = (df["home_goal"].astype(int) - df["away_goal"].astype(int)).abs().tolist()
        assert margins == sorted(margins, reverse=True)

    def test_biggest_wins_competition_filter(self, knowledge):
        df = knowledge.biggest_wins(competition="Copa Libertadores", limit=5)
        assert df["competition"].str.contains("Libertadores", case=False).all()


class TestHomeAwayRecords:
    def test_best_home_record_returns_rows(self, knowledge):
        df = knowledge.best_home_record(season=2019, limit=5)
        assert len(df) <= 5
        assert not df.empty
        assert df["win_rate"].tolist() == sorted(df["win_rate"], reverse=True)

    def test_best_away_record_returns_rows(self, knowledge):
        df = knowledge.best_away_record(season=2019, limit=5)
        assert not df.empty
        assert (df["away_matches"] >= 5).all()


class TestTopScoringTeams:
    def test_top_scorers_2019(self, knowledge):
        df = knowledge.top_scorers_by_team(season=2019, limit=5)
        assert not df.empty
        # Flamengo scored 86 goals in 2019 - should be at or near the top
        assert df.iloc[0]["team"].lower() == "flamengo"
        assert df["goals"].tolist() == sorted(df["goals"], reverse=True)
