"""
================================================================================
Context
================================================================================
Test module: test_statistics.py
Project:     Brazilian Soccer MCP Server
Feature:     Statistical Analysis (capability category 5).
Style:       BDD Given-When-Then.
================================================================================
"""


class TestAggregateStatistics:
    def test_average_goals_per_match(self, kg):
        # Given the match data is loaded
        # When I ask for average goals in the Brasileirão
        stats = kg.average_goals("brasileirao")
        # Then the average is a realistic football figure
        assert 2.0 <= stats["avg_goals_per_match"] <= 3.5
        assert stats["matches"] > 1000

    def test_win_rates_sum_to_one_hundred(self, kg):
        # When I read home/away/draw rates
        s = kg.average_goals("brasileirao", season=2019)
        total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
        # Then they sum to ~100% (allowing rounding)
        assert abs(total - 100.0) < 0.5
        # And home advantage is visible
        assert s["home_win_rate"] > s["away_win_rate"]

    def test_biggest_wins_are_sorted_by_margin(self, kg):
        # When I ask for the biggest victories
        wins = kg.biggest_wins(limit=10)
        margins = [abs(m.home_goal - m.away_goal) for m in wins]
        # Then they are ordered by margin, largest first
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 6

    def test_best_home_record_ranking(self, kg):
        # When I rank teams by home win rate in a season
        records = kg.best_record("home", competition="brasileirao",
                                 season=2019, min_matches=10, limit=5)
        # Then win rates are non-increasing and Flamengo leads in 2019
        rates = [r["win_rate"] for r in records]
        assert rates == sorted(rates, reverse=True)
        assert records[0]["team"] == "Flamengo"

    def test_best_away_record_uses_away_games(self, kg):
        records = kg.best_record("away", competition="brasileirao",
                                 season=2019, min_matches=10, limit=5)
        assert records
        assert all(r["venue"] == "away" for r in records)
