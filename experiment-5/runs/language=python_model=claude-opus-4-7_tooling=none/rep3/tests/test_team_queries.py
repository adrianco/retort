"""BDD: team queries.

Feature: Team statistics
  Calculate W/D/L, goals, win rate for a team.

Feature: Team comparison
  Side-by-side stats plus head-to-head.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import team_stats, compare_teams


def test_team_stats_flamengo_2019_brasileirao(dataset):
    # Given a known champion season (Flamengo 2019)
    # When  we compute their stats
    s = team_stats(dataset, "Flamengo", season=2019, competition="Brasileirão")
    # Then  the historical record matches: 38 matches, 28W 6D 4L, 90 pts
    assert s["matches"] == 38
    assert s["wins"] == 28
    assert s["draws"] == 6
    assert s["losses"] == 4
    assert s["points"] == 90
    assert s["goal_difference"] > 0


def test_team_stats_home_venue_filter(dataset):
    # Given the match data is loaded
    # When  we compute Corinthians' home record in the 2019 Brasileirão
    s = team_stats(
        dataset, "Corinthians", season=2019, competition="Brasileirão", venue="home"
    )
    # Then  the matches counted are home matches only
    assert s["home_matches"] > 0
    assert s["away_matches"] == 0
    assert s["matches"] == s["home_matches"]


def test_team_stats_invariants(dataset):
    # Given any team's all-time stats
    # When  we aggregate them
    s = team_stats(dataset, "Palmeiras")
    # Then  W + D + L equals the match count
    assert s["wins"] + s["draws"] + s["losses"] == s["matches"]
    # And  points = 3*W + D
    assert s["points"] == 3 * s["wins"] + s["draws"]
    # And  goal_difference = GF - GA
    assert s["goal_difference"] == s["goals_for"] - s["goals_against"]


def test_compare_teams_includes_head_to_head(dataset):
    # Given two clubs
    # When  we request a comparison
    r = compare_teams(dataset, "Palmeiras", "Santos")
    # Then  we receive each side's stats plus their direct record
    assert r["team_a"]["matches"] > 0
    assert r["team_b"]["matches"] > 0
    assert "total_matches" in r["head_to_head"]
