"""BDD: statistical analysis.

Feature: Statistical Analysis
  As an LLM
  I want aggregate statistics over the match data
  So that I can answer "What's the average goals per match in the Brasileirão?"
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as q
from brazilian_soccer_mcp.data_loader import DataStore


class TestAverageGoals:
    """Scenario: compute average goals across all matches in the slice."""

    def test_brasileirao_average_in_normal_range(self, store: DataStore) -> None:
        result = q.average_goals_per_match(store, competition="Serie A")
        # When I read the average
        # Then it falls in the historical 2.0–3.0 range for the Brasileirão
        assert 2.0 <= result["average_goals"] <= 3.0
        assert (
            abs(
                result["average_goals"]
                - (result["average_home_goals"] + result["average_away_goals"])
            )
            < 0.01
        )


class TestHomeAwaySplit:
    """Scenario: home wins / away wins / draws sum to the match count."""

    def test_rates_sum_to_one(self, store: DataStore) -> None:
        result = q.home_away_split(store, competition="Serie A")
        total = (
            result["home_win_rate"] + result["away_win_rate"] + result["draw_rate"]
        )
        assert abs(total - 1.0) < 0.001
        assert (
            result["home_wins"] + result["away_wins"] + result["draws"]
            == result["matches"]
        )

    def test_home_advantage_holds(self, store: DataStore) -> None:
        # Brazilian football has a well-documented home advantage; the rate
        # should comfortably exceed the away rate.
        result = q.home_away_split(store, competition="Serie A")
        assert result["home_win_rate"] > result["away_win_rate"]


class TestBiggestWins:
    """Scenario: surface the largest winning margins."""

    def test_returned_matches_have_margin(self, store: DataStore) -> None:
        result = q.biggest_wins(store, limit=10)
        margins = [m["margin"] for m in result["matches"]]
        # When I read the margins
        # Then they're descending and large
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5


class TestBestHomeRecord:
    """Scenario: rank teams by home win rate."""

    def test_2019_top_home_team(self, store: DataStore) -> None:
        result = q.best_home_records(
            store, competition="Serie A", season=2019, min_matches=10, limit=5
        )
        # In 2019 Flamengo lost only one home game; they should top the list
        # (or be very close to it).
        names = [t["team"] for t in result["teams"]]
        assert "Flamengo" in names
        # Rates are descending.
        rates = [t["win_rate"] for t in result["teams"]]
        assert rates == sorted(rates, reverse=True)
