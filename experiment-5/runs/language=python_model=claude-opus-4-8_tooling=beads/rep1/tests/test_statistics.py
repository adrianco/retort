"""
================================================================================
Feature: Statistical Analysis
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Gherkin scenarios: average goals per match, home/away win rates, biggest wins,
and best home/away records.
================================================================================
"""

from data_loader import SERIE_A


class TestAverageGoals:
    """Scenario: What's the average goals per match in the Brasileirão?"""

    def test_average_and_rates_are_plausible(self, graph):
        # Given the Série A 2019 matches
        s = graph.average_goals(SERIE_A, 2019)
        # Then the average goals per match is in a realistic football range
        assert s["matches"] == 380
        assert 2.0 <= s["avg_goals_per_match"] <= 3.5
        # And the outcome rates add up to ~100%
        total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
        assert abs(total - 100.0) < 0.5

    def test_home_advantage_exists(self, graph):
        # Then home teams win more often than away teams (home advantage)
        s = graph.average_goals(SERIE_A, 2019)
        assert s["home_win_rate"] > s["away_win_rate"]


class TestBiggestWins:
    """Scenario: Show me the biggest wins in the dataset."""

    def test_sorted_by_margin(self, graph):
        wins = graph.biggest_wins(SERIE_A, 2019, limit=10)
        margins = [abs(m.home_goal - m.away_goal) for m in wins]
        # Then results are ordered by goal margin, largest first
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 4


class TestBestRecord:
    """Scenario: Which team has the best home record?"""

    def test_best_home_record_2019(self, graph):
        recs = graph.best_record(venue="home", competition=SERIE_A,
                                 season=2019, min_matches=10, limit=5)
        assert recs
        # Then the list is ordered by win rate, highest first
        rates = [r["win_rate"] for r in recs]
        assert rates == sorted(rates, reverse=True)
        # And in 2019 the champion Flamengo had an excellent home record
        assert recs[0]["win_rate"] >= 70

    def test_min_matches_filter(self, graph):
        recs = graph.best_record(venue="all", competition=SERIE_A,
                                 season=2019, min_matches=30)
        assert all(r["played"] >= 30 for r in recs)
