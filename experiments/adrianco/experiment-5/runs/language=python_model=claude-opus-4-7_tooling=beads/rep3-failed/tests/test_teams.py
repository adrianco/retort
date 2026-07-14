"""Feature: Team Queries."""

import pytest


class TestTeamStats:
    """
    Scenario: Get team statistics
      Given the match data is loaded
      When I request statistics for 'Palmeiras' in season '2023'
      Then I should receive wins, losses, draws, and goals
    """

    def test_palmeiras_2023_stats(self, knowledge):
        stats = knowledge.team_stats("Palmeiras", season=2023, competition="Brasileirão Série A")
        for key in ("matches", "wins", "draws", "losses", "goals_for", "goals_against", "win_rate", "points"):
            assert key in stats
        assert stats["matches"] > 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]

    def test_win_rate_within_range(self, knowledge):
        stats = knowledge.team_stats("Flamengo", season=2019, competition="Brasileirão Série A")
        assert 0.0 <= stats["win_rate"] <= 1.0

    def test_home_only_stats(self, knowledge):
        stats = knowledge.team_stats(
            "Corinthians", season=2022, competition="Brasileirão Série A", home_only=True
        )
        assert stats["matches"] > 0
        assert stats["matches"] <= 19  # league has 19 home matches max

    def test_unknown_team_returns_zero(self, knowledge):
        stats = knowledge.team_stats("Not A Team")
        assert stats["matches"] == 0
        assert stats["wins"] == 0

    def test_points_calculation(self, knowledge):
        stats = knowledge.team_stats("Flamengo", season=2019, competition="Brasileirão Série A")
        assert stats["points"] == stats["wins"] * 3 + stats["draws"]


class TestTeamMetadata:
    def test_team_seasons(self, knowledge):
        seasons = knowledge.team_seasons("Flamengo")
        assert 2019 in seasons
        assert sorted(seasons) == seasons

    def test_team_competitions(self, knowledge):
        comps = knowledge.team_competitions("Flamengo")
        assert any("Brasileirão" in c for c in comps)
        assert any("Libertadores" in c or "Copa do Brasil" in c for c in comps)
