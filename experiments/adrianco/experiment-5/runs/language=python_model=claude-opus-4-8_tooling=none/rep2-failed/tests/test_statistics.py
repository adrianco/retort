"""
Context
=======
Feature: Statistical Analysis  (TASK.md section 5)

Scenario: Average goals per match
Scenario: Home vs away win rates
Scenario: Biggest victories
Scenario: Best home/away records
"""

from __future__ import annotations


class TestAggregateStatistics:
    def test_average_goals_per_match_is_in_a_sane_range(self, graph):
        # WHEN I ask for Brasileirão aggregate stats
        stats = graph.competition_stats(competition="Brasileirão")
        # THEN the average goals per match is a realistic football number
        assert 2.0 <= stats["avg_goals_per_match"] <= 3.5
        # AND win/draw rates sum to ~100%
        total = stats["home_win_rate"] + stats["away_win_rate"] + stats["draw_rate"]
        assert abs(total - 100.0) < 0.5

    def test_home_advantage_exists(self, graph):
        stats = graph.competition_stats(competition="Brasileirão")
        # Home teams win more often than away teams.
        assert stats["home_win_rate"] > stats["away_win_rate"]


class TestBiggestWins:
    def test_biggest_wins_sorted_by_margin(self, graph):
        matches = graph.biggest_wins(competition="Brasileirão", limit=10)
        assert matches
        margins = [abs(m.home_goal - m.away_goal) for m in matches]
        assert margins == sorted(margins, reverse=True)
        # The very biggest Série A margin in the data is substantial.
        assert margins[0] >= 6


class TestBestRecords:
    def test_best_home_record_returns_ranked_teams(self, graph):
        # WHEN I ask which teams have the best home record in 2019
        rows = graph.best_records(season=2019, competition="Brasileirão",
                                  venue="home", metric="win_rate")
        assert rows
        rates = [r["win_rate"] for r in rows]
        assert rates == sorted(rates, reverse=True)
        # The best home team won most of its 19 home games.
        assert rows[0]["played"] >= 5
        assert rows[0]["win_rate"] >= 50.0
