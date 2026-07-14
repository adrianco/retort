"""
================================================================================
tests.test_team_queries
================================================================================

CONTEXT
-------
BDD scenarios for Required Capability #2 (Team Queries) and head-to-head
comparison: win/loss/draw records, goals for/against, home/away splits and the
"Compare Palmeiras and Santos head-to-head" sample question.
================================================================================
"""


class TestTeamQueries:
    """Feature: Team Queries."""

    def test_team_record_has_consistent_totals(self, kg):
        # Scenario: Get team statistics
        # When I request statistics for "Palmeiras" in season "2019"
        rec = kg.team_record("Palmeiras", season=2019, competition="Brasileirão")
        # Then I receive wins, losses, draws and goals that add up
        assert rec["played"] == rec["wins"] + rec["draws"] + rec["losses"]
        assert rec["played"] > 0
        assert rec["points"] == rec["wins"] * 3 + rec["draws"]
        assert rec["goal_difference"] == rec["goals_for"] - rec["goals_against"]

    def test_home_record_is_subset_of_overall(self, kg):
        overall = kg.team_record("Corinthians", season=2019, competition="Brasileirão")
        home = kg.team_record("Corinthians", season=2019, competition="Brasileirão",
                              venue="home")
        away = kg.team_record("Corinthians", season=2019, competition="Brasileirão",
                              venue="away")
        # Then home + away games equal the total games played
        assert home["played"] + away["played"] == overall["played"]
        assert home["played"] == 19  # a 20-team league = 19 home games

    def test_win_rate_is_a_percentage(self, kg):
        rec = kg.team_record("Flamengo", season=2019, competition="Brasileirão")
        assert 0.0 <= rec["win_rate"] <= 100.0

    def test_compare_palmeiras_and_santos_head_to_head(self, kg):
        # Scenario: "Compare Palmeiras and Santos head-to-head"
        h = kg.head_to_head("Palmeiras", "Santos")
        # Then the result is internally consistent
        assert h["total"] == len(h["matches"])
        assert h["total"] == h["team1_wins"] + h["team2_wins"] + h["draws"]
        assert h["total"] > 0

    def test_head_to_head_is_symmetric(self, kg):
        a = kg.head_to_head("Flamengo", "Fluminense")
        b = kg.head_to_head("Fluminense", "Flamengo")
        # Then swapping the teams swaps the win counts but keeps totals/draws
        assert a["total"] == b["total"]
        assert a["draws"] == b["draws"]
        assert a["team1_wins"] == b["team2_wins"]
        assert a["team2_wins"] == b["team1_wins"]

    def test_unknown_team_returns_empty_record(self, kg):
        rec = kg.team_record("Nonexistent United")
        assert rec["played"] == 0
        assert rec["win_rate"] == 0.0
