"""
================================================================================
BDD Feature: Statistical Analysis
================================================================================

CONTEXT
-------
Covers specification capability #5: aggregate statistics - average goals per
match, biggest victories, and best home / away records. Exact assertions use
``synthetic_kg``; integration checks validate ranges on the real data and the
< 5 second aggregate-query performance target.
================================================================================
"""

import time

from brazilian_soccer_mcp.normalize import COMP_BRASILEIRAO


class TestAverageGoals:
    """Feature: Average goals per match."""

    def test_average_goals_synthetic(self, synthetic_kg):
        # Given the 2023 mini-season (14 goals over 6 matches)
        avg = synthetic_kg.average_goals_per_match(
            competition=COMP_BRASILEIRAO, season=2023
        )
        # Then the average is 2.33
        assert avg == round(14 / 6, 2)


class TestBiggestWins:
    """Feature: Biggest victories."""

    def test_biggest_win_is_largest_margin(self, synthetic_kg):
        # When I ask for the biggest wins
        wins = synthetic_kg.biggest_wins(season=2023, limit=3)
        # Then the top result is the 3-1 (margin 2, more goals than 2-0)
        top = wins[0]
        assert abs(top.home_goal - top.away_goal) == 2
        assert top.home_team == "Flamengo"
        assert top.away_team == "Santos"

    def test_biggest_wins_sorted_descending(self, synthetic_kg):
        wins = synthetic_kg.biggest_wins(season=2023, limit=10)
        margins = [abs(m.home_goal - m.away_goal) for m in wins]
        assert margins == sorted(margins, reverse=True)


class TestVenueRecords:
    """Feature: Best home / away records."""

    def test_best_home_record(self, synthetic_kg):
        # When I rank home records (min 2 matches)
        rows = synthetic_kg.best_home_record(season=2023, min_matches=2)
        # Then Flamengo (2 home wins) tops the list
        assert rows[0]["team"] == "Flamengo"
        assert rows[0]["win_rate"] == 100.0

    def test_best_away_record(self, synthetic_kg):
        # When I rank away records (min 2 matches)
        rows = synthetic_kg.best_away_record(season=2023, min_matches=2)
        # Then Palmeiras (1 win in 2 away games) tops the list
        assert rows[0]["team"] == "Palmeiras"
        assert rows[0]["win_rate"] == 50.0


class TestRealStatistics:
    """Feature: Aggregate statistics on the real dataset."""

    def test_real_average_goals_in_range(self, kg):
        avg = kg.average_goals_per_match(competition="Serie A")
        # Football averages sit roughly between 1.5 and 4 goals/match.
        assert 1.5 <= avg <= 4.0

    def test_real_biggest_wins_have_large_margins(self, kg):
        wins = kg.biggest_wins(limit=5)
        assert wins
        assert abs(wins[0].home_goal - wins[0].away_goal) >= 4

    def test_aggregate_query_under_five_seconds(self, kg):
        # Then a heavy aggregate query meets the performance target
        start = time.time()
        kg.best_home_record(competition="Serie A")
        kg.average_goals_per_match(competition="Serie A")
        assert time.time() - start < 5.0
