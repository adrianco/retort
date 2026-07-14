"""
================================================================================
Context
================================================================================
Test module: test_team_queries.py
Project:     Brazilian Soccer MCP Server
Feature:     Team Queries (capability category 2).
Style:       BDD Given-When-Then.
================================================================================
"""


class TestTeamStatistics:
    def test_team_statistics_for_a_season(self, kg):
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season 2019
        stats = kg.team_stats("Palmeiras", season=2019, competition="brasileirao")
        # Then I receive wins, losses, draws and goals
        for field in ("wins", "losses", "draws", "goals_for", "goals_against"):
            assert field in stats
        # And a full Série A season is 38 matches
        assert stats["matches"] == 38
        assert stats["wins"] + stats["draws"] + stats["losses"] == 38
        # And points are internally consistent
        assert stats["points"] == stats["wins"] * 3 + stats["draws"]

    def test_home_record_matches_spec_shape(self, kg):
        # When I ask for a team's home record
        stats = kg.team_stats("Corinthians", season=2019,
                              competition="brasileirao", venue="home")
        # Then win rate is a sensible percentage
        assert 0.0 <= stats["win_rate"] <= 100.0
        assert stats["venue"] == "home"

    def test_goal_difference_is_consistent(self, kg):
        stats = kg.team_stats("Flamengo", season=2019, competition="brasileirao")
        assert stats["goal_difference"] == stats["goals_for"] - stats["goals_against"]


class TestHeadToHeadAndCompare:
    def test_head_to_head_record(self, kg):
        # When I compare two rivals head-to-head
        h2h = kg.head_to_head("Flamengo", "Fluminense")
        # Then wins/draws sum to the match total
        total = h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
        # (draws/wins only counted for matches with scores)
        assert total <= h2h["total_matches"]
        assert h2h["total_matches"] > 0

    def test_head_to_head_perspective_is_symmetric(self, kg):
        # Given A-vs-B and B-vs-A
        ab = kg.head_to_head("Palmeiras", "Santos")
        ba = kg.head_to_head("Santos", "Palmeiras")
        # Then the same total and mirrored wins are reported
        assert ab["total_matches"] == ba["total_matches"]
        assert ab["team_a_wins"] == ba["team_b_wins"]
        assert ab["draws"] == ba["draws"]

    def test_compare_teams_bundles_everything(self, kg):
        cmp = kg.compare_teams("Palmeiras", "Santos", season=2019)
        assert "head_to_head" in cmp
        assert cmp["team_a_stats"]["team"]
        assert cmp["team_b_stats"]["team"]
