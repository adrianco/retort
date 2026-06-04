"""
================================================================================
tests.test_statistics
================================================================================

CONTEXT
-------
BDD scenarios for Required Capability #5 (Statistical Analysis): average goals
per match, home/away win rates, biggest wins and best home/away records.
Covers the sample questions "What's the average goals per match?", "Which team
has the best home record?", "Show me the biggest wins in the dataset".
================================================================================
"""


class TestStatistics:
    """Feature: Statistical Analysis."""

    def test_average_goals_is_plausible(self, kg):
        # Scenario: "What's the average goals per match in the Brasileirão?"
        stats = kg.average_goals(competition="Brasileirão Série A")
        # Then the average is in a realistic football range
        assert 2.0 <= stats["avg_goals"] <= 3.5
        assert stats["matches"] > 1000

    def test_win_rates_sum_to_one_hundred(self, kg):
        stats = kg.average_goals(competition="Brasileirão Série A", season=2019)
        total = stats["home_win_rate"] + stats["away_win_rate"] + stats["draw_rate"]
        # Then home/away/draw percentages account for all matches (±rounding)
        assert abs(total - 100.0) < 0.5
        # And home advantage exists
        assert stats["home_win_rate"] > stats["away_win_rate"]

    def test_biggest_wins_sorted_by_margin(self, kg):
        # Scenario: "Show me the biggest wins in the dataset"
        wins = kg.biggest_wins(competition="Brasileirão Série A", limit=10)
        assert len(wins) == 10
        margins = [w["margin"] for w in wins]
        assert margins == sorted(margins, reverse=True)
        # And the biggest margin is a real blowout
        assert margins[0] >= 5

    def test_best_home_record(self, kg):
        # Scenario: "Which team has the best home record?"
        records = kg.best_record(
            competition="Brasileirão Série A", season=2019, venue="home"
        )
        assert len(records) > 0
        # Then results are ordered by win rate descending
        rates = [r["win_rate"] for r in records]
        assert rates == sorted(rates, reverse=True)
        # And the best home team in 2019 is the champion, Flamengo
        assert records[0]["team"] == "Flamengo"

    def test_best_away_record_differs_from_home(self, kg):
        home = kg.best_record(competition="Brasileirão Série A", season=2019,
                              venue="home")
        away = kg.best_record(competition="Brasileirão Série A", season=2019,
                              venue="away")
        # Both produce ranked lists
        assert home and away
        assert all(r["venue"] == "home" for r in home)
        assert all(r["venue"] == "away" for r in away)

    def test_compare_two_seasons(self, kg):
        # Scenario: "Compare the 2018 and 2019 seasons"
        s2018 = kg.average_goals(competition="Brasileirão Série A", season=2018)
        s2019 = kg.average_goals(competition="Brasileirão Série A", season=2019)
        assert s2018["matches"] == 380
        assert s2019["matches"] == 380
