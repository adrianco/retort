"""
================================================================================
test_statistics.py - BDD scenarios for aggregate statistical analysis
================================================================================

Feature: Statistical Analysis
  Scenario: Calculate aggregated statistics
    Given the match data is loaded
    When I request league averages / biggest wins / best records
    Then I should receive correctly computed aggregates.
================================================================================
"""


class TestLeagueStatistics:
    def test_average_goals_is_plausible(self, engine):
        # When I compute Série A league-wide statistics
        s = engine.league_statistics("serie_a")
        # Then the average goals per match is in a realistic football range
        assert 2.0 <= s["avg_goals_per_match"] <= 3.5
        assert s["matches"] > 1000

    def test_outcome_rates_sum_to_100(self, engine):
        s = engine.league_statistics("serie_a", season=2019)
        total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
        assert abs(total - 100.0) < 0.5

    def test_home_advantage_exists(self, engine):
        s = engine.league_statistics("serie_a")
        # Home win rate should exceed away win rate (home advantage)
        assert s["home_win_rate"] > s["away_win_rate"]


class TestBiggestWins:
    def test_biggest_wins_are_sorted_by_margin(self, engine):
        data = engine.biggest_wins(competition="serie_a", limit=10)
        margins = [m["margin"] for m in data["matches"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5  # there is at least one big blow-out

    def test_biggest_wins_scoped_to_season(self, engine):
        data = engine.biggest_wins(competition="serie_a", season=2019, limit=5)
        assert len(data["matches"]) == 5


class TestBestRecord:
    def test_best_home_record_ranking(self, engine):
        # When I ask which team had the best home record in 2019
        data = engine.best_record(competition="serie_a", season=2019, scope="home")
        ranking = data["ranking"]
        assert ranking, "ranking should not be empty"
        # Then the ranking is ordered by win rate descending
        rates = [r["win_rate"] for r in ranking]
        assert rates == sorted(rates, reverse=True)

    def test_top_scoring_team(self, engine):
        data = engine.top_scoring_team("serie_a", season=2019)
        goals = [r["goals"] for r in data["ranking"]]
        assert goals == sorted(goals, reverse=True)
        assert goals[0] > 50  # a champion-calibre attack over a season
