"""
================================================================================
BDD Feature: Team Queries
================================================================================

CONTEXT
-------
Covers specification capability #2: team match history and statistics
(W/D/L, goals for/against, win-rate), venue splits (home/away) and team
comparison. Exact assertions use ``synthetic_kg``.
================================================================================
"""


class TestTeamStatistics:
    """Feature: Get team statistics."""

    def test_overall_season_record(self, synthetic_kg):
        # Given the match data is loaded
        # When I request statistics for Flamengo in season 2023
        stats = synthetic_kg.team_stats("Flamengo", season=2023)
        # Then I receive wins, losses, draws and goals
        assert stats["matches"] == 4
        assert stats["wins"] == 2
        assert stats["draws"] == 2
        assert stats["losses"] == 0
        assert stats["goals_for"] == 6
        assert stats["goals_against"] == 2
        assert stats["goal_difference"] == 4
        assert stats["points"] == 8
        assert stats["win_rate"] == 50.0

    def test_home_only_record(self, synthetic_kg):
        # When I restrict to home matches
        stats = synthetic_kg.team_stats("Flamengo", season=2023, venue="home")
        # Then only the two home wins are counted
        assert stats["matches"] == 2
        assert stats["wins"] == 2
        assert stats["win_rate"] == 100.0

    def test_away_only_record(self, synthetic_kg):
        # When I restrict to away matches
        stats = synthetic_kg.team_stats("Flamengo", season=2023, venue="away")
        # Then the two away draws are counted
        assert stats["matches"] == 2
        assert stats["draws"] == 2
        assert stats["wins"] == 0

    def test_bottom_team_record(self, synthetic_kg):
        # Then Santos' poor season is reflected
        stats = synthetic_kg.team_stats("Santos", season=2023)
        assert stats["wins"] == 0
        assert stats["losses"] == 3
        assert stats["points"] == 1


class TestCompareTeams:
    """Feature: Compare two teams."""

    def test_compare_includes_both_and_h2h(self, synthetic_kg):
        # When I compare Flamengo and Palmeiras
        cmp = synthetic_kg.compare_teams("Flamengo", "Palmeiras", season=2023)
        # Then I get both teams' stats and their head-to-head
        assert cmp["team_a"]["team"] == "Flamengo"
        assert cmp["team_b"]["team"] == "Palmeiras"
        assert cmp["head_to_head"]["total"] == 2


class TestRealTeamQueries:
    """Feature: Team stats against the real dataset."""

    def test_real_team_stats_are_consistent(self, kg):
        # Then W + D + L equals matches played
        stats = kg.team_stats("Palmeiras", competition="Serie A")
        assert stats["matches"] == (
            stats["wins"] + stats["draws"] + stats["losses"]
        )
        assert stats["matches"] > 0

    def test_real_home_record_subset_of_total(self, kg):
        total = kg.team_stats("Corinthians", competition="Serie A")
        home = kg.team_stats("Corinthians", competition="Serie A", venue="home")
        assert home["matches"] <= total["matches"]
        assert 0.0 <= home["win_rate"] <= 100.0
