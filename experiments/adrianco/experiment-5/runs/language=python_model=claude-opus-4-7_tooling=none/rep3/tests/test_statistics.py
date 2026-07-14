"""BDD: aggregate statistical analysis.

Feature: League-wide stats
  Average goals per match, home/away/draw rates.

Feature: Biggest wins
  Matches ranked by absolute margin.

Feature: Home/away records
  Teams ranked by venue-specific win rate.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    best_away_record,
    best_home_record,
    biggest_wins,
    overall_stats,
    top_scoring_teams,
)


def test_overall_brasileirao_stats(dataset):
    # Given the Brasileirão data
    # When  we compute aggregate stats
    s = overall_stats(dataset, "Brasileirão")
    # Then  averages and rates are within sensible ranges
    assert s["matches"] > 3000
    assert 2.0 < s["avg_goals_per_match"] < 3.5
    assert 0.4 < s["home_win_rate"] < 0.6
    # And rates sum to ~1
    total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
    assert abs(total - 1.0) < 0.005


def test_biggest_wins_are_sorted_by_margin(dataset):
    # Given the data is loaded
    # When  we ask for the 10 biggest wins
    rows = biggest_wins(dataset, limit=10)
    # Then  margins are non-increasing and >= 5
    assert len(rows) == 10
    margins = [r["margin"] for r in rows]
    assert margins == sorted(margins, reverse=True)
    assert min(margins) >= 5


def test_best_home_record_is_sorted_and_filtered(dataset):
    # Given the 2019 Brasileirão data
    # When  we ask for top home records
    rows = best_home_record(dataset, "Brasileirão", 2019, min_matches=5, limit=5)
    # Then  results are sorted by win rate desc and Flamengo leads
    assert rows
    rates = [r["win_rate"] for r in rows]
    assert rates == sorted(rates, reverse=True)
    assert rows[0]["team"] == "flamengo"


def test_best_away_record_returns_data(dataset):
    # Given the 2019 Brasileirão data
    # When  we ask for top away records
    rows = best_away_record(dataset, "Brasileirão", 2019, min_matches=5, limit=5)
    # Then  results are sorted and non-empty
    assert rows
    rates = [r["win_rate"] for r in rows]
    assert rates == sorted(rates, reverse=True)


def test_top_scoring_teams(dataset):
    # Given the 2019 Brasileirão data
    # When  we ask for top scoring teams
    rows = top_scoring_teams(dataset, "Brasileirão", 2019, limit=5)
    # Then  Flamengo leads (scored 86 in their title-winning season)
    assert rows
    goals = [r["goals"] for r in rows]
    assert goals == sorted(goals, reverse=True)
    assert rows[0]["team"] == "flamengo"
