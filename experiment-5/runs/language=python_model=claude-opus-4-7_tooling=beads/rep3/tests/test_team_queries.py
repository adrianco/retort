"""BDD-style tests for team statistics.

Feature: Team Queries
  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2019"
    Then I should receive wins, losses, draws, and goals
    And the row counts must add up correctly.
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as Q


class TestTeamStats:
    def test_palmeiras_2019_brasileirao_record_is_consistent(self, store):
        # When I request stats for Palmeiras in 2019 Brasileirão
        stats = Q.team_stats(store, "Palmeiras", season=2019, competition="Brasileirão")
        # Then wins+draws+losses == matches
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
        # And points == 3*W + D
        assert stats["points"] == 3 * stats["wins"] + stats["draws"]
        # And the team played a full season (38 rounds)
        assert stats["matches"] == 38

    def test_corinthians_2022_home_record_matches_expected(self, store):
        # Corinthians' 2022 home performance pooled across all competitions in
        # the dataset should still be coherent: numbers add up and home goals
        # exceed away conceded for a top side.
        stats = Q.team_stats(store, "Corinthians", season=2022, venue="home")
        assert stats["matches"] > 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
        assert stats["goals_for"] >= stats["goals_against"]

    def test_team_competitions_returns_brasileirao(self, store):
        comps = Q.team_competitions(store, "Flamengo")
        assert any(c["competition"] == "Brasileirão" and c["matches"] > 100 for c in comps)
