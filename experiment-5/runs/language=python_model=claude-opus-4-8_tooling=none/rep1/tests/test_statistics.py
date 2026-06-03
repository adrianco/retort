"""
================================================================================
 BDD tests: Statistical Analysis (capability category 5)
================================================================================
Feature: Statistical Analysis
  I want aggregated statistics: goals-per-match, win rates, biggest wins and
  home/away records
  So that I can answer analytical questions.
================================================================================
"""


class TestAverageGoals:
    def test_average_goals_is_in_a_plausible_range(self, engine):
        # Given the match data is loaded
        # When I compute average goals for the 2019 Série A
        s = engine.average_goals("Brasileirão Série A", 2019)
        # Then it is a realistic football figure
        assert s["matches"] == 380
        assert 2.0 <= s["average_goals"] <= 3.5
        # And the three outcome rates sum to ~100%
        total = s["home_win_rate"] + s["draw_rate"] + s["away_win_rate"]
        assert abs(total - 100.0) < 0.5

    def test_home_advantage_exists(self, engine):
        # Given the match data is loaded
        # When I compute outcome rates for the whole Brasileirão
        s = engine.average_goals("Brasileirão Série A")
        # Then home teams win more often than away teams
        assert s["home_win_rate"] > s["away_win_rate"]


class TestBiggestWins:
    def test_results_sorted_by_margin_descending(self, engine):
        # Given the match data is loaded
        # When I request the biggest wins in the Série A
        result = engine.biggest_wins("Brasileirão Série A", limit=10)
        margins = [abs(m["home_goal"] - m["away_goal"]) for m in result["matches"]]
        # Then they are sorted by goal margin (largest first) and are lopsided
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5


class TestHomeAwayRecords:
    def test_best_home_record_is_sorted_by_win_rate(self, engine):
        # Given the match data is loaded
        # When I ask for the best home records in 2019
        result = engine.best_home_record(season=2019,
                                         competition="Brasileirão Série A")
        rates = [r["win_rate"] for r in result["teams"]]
        # Then teams are ordered by descending home win-rate
        assert rates == sorted(rates, reverse=True)
        assert result["teams"][0]["win_rate"] > 50

    def test_best_away_record_respects_minimum_matches(self, engine):
        # Given the match data is loaded
        # When I ask for the best away records in 2019
        result = engine.best_away_record(season=2019,
                                         competition="Brasileirão Série A",
                                         min_matches=5)
        # Then every listed team has at least the minimum number of away games
        assert all(r["matches"] >= 5 for r in result["teams"])


class TestSeasonComparison:
    def test_compare_two_seasons_returns_both(self, engine):
        # Given the match data is loaded
        # When I compare the 2018 and 2019 seasons
        cmp = engine.compare_seasons(2018, 2019, "Brasileirão Série A")
        # Then statistics for both seasons are returned
        assert cmp["season_a"]["matches"] == 380
        assert cmp["season_b"]["matches"] == 380
