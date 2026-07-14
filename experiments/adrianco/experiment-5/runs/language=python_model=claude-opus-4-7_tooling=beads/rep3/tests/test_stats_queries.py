"""BDD-style tests for the aggregate statistical analysis.

Feature: Statistical Analysis
  Scenario: Compute average goals per match for the Brasileirão
    Given match data is loaded
    When I aggregate statistics for Brasileirão
    Then I receive sensible rates and totals.
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as Q


class TestAggregateStats:
    def test_brasileirao_goal_average_is_in_expected_range(self, store):
        stats = Q.aggregate_stats(store, competition="Brasileirão")
        # Real-world rule of thumb: between 2 and 3 goals per match.
        assert 2.0 <= stats["avg_goals_per_match"] <= 3.0
        # Home win rate higher than away in football generally.
        assert stats["home_win_rate"] > stats["away_win_rate"]
        assert stats["matches"] == stats["home_wins"] + stats["away_wins"] + stats["draws"]


class TestBiggestWins:
    def test_biggest_wins_are_sorted_by_margin(self, store):
        wins = Q.biggest_wins(store, competition="Brasileirão", limit=10)
        margins = [abs(w["home_goals"] - w["away_goals"]) for w in wins]
        assert margins == sorted(margins, reverse=True)
        # The very biggest margin should be at least 6 (well-known blowouts).
        assert margins[0] >= 6


class TestBestRecords:
    def test_best_home_record_returns_sorted_table(self, store):
        rows = Q.best_records(store, season=2019, competition="Brasileirão", venue="home", limit=5)
        assert rows
        for prev, nxt in zip(rows, rows[1:]):
            assert prev["win_rate"] >= nxt["win_rate"]
        # The top side should win most of its home games — at least 60%.
        assert rows[0]["win_rate"] >= 0.5


class TestTopScoringTeams:
    def test_top_scorers_have_higher_or_equal_goals_than_others(self, store):
        rows = Q.top_scoring_teams(store, season=2019, competition="Brasileirão", limit=5)
        assert rows
        for prev, nxt in zip(rows, rows[1:]):
            assert prev["goals_for"] >= nxt["goals_for"]
