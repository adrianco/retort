"""
================================================================================
 BDD tests: Team Queries (capability category 2)
================================================================================
Feature: Team Queries
  I want win/loss/draw records, goals and head-to-head comparisons
  So that I can answer team-performance questions.
================================================================================
"""


class TestTeamRecord:
    def test_record_components_are_internally_consistent(self, engine):
        # Given the match data is loaded
        # When I request Palmeiras' 2022 Série A record
        rec = engine.team_record("Palmeiras", season=2022,
                                 competition="Brasileirão Série A")
        # Then wins/draws/losses sum to matches played
        assert rec["found"] is True
        assert rec["wins"] + rec["draws"] + rec["losses"] == rec["matches"]
        # And the win rate is consistent with the wins
        assert rec["win_rate"] == round(100.0 * rec["wins"] / rec["matches"], 1)

    def test_home_record_only_counts_home_matches(self, engine):
        # Given the match data is loaded
        # When I request Corinthians' 2021 home record (a complete season)
        rec = engine.team_record("Corinthians", season=2021,
                                 competition="Brasileirão Série A", venue="home")
        # Then it reflects a single season of home games (19 in a 20-team league)
        assert rec["found"] is True
        assert rec["matches"] == 19
        assert rec["wins"] + rec["draws"] + rec["losses"] == 19

    def test_unknown_team_reports_not_found(self, engine):
        # Given the match data is loaded
        # When I request a non-existent team
        rec = engine.team_record("Nonexistent United FC")
        # Then it is reported as not found rather than crashing
        assert rec["found"] is False


class TestHeadToHead:
    def test_palmeiras_vs_santos_totals_are_consistent(self, engine):
        # Given the match data is loaded
        # When I compare Palmeiras and Santos head-to-head
        h2h = engine.head_to_head("Palmeiras", "Santos")
        # Then wins + draws account for every meeting
        assert h2h["total_matches"] > 0
        assert (h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
                == h2h["total_matches"])

    def test_head_to_head_is_symmetric_in_total(self, engine):
        # Given the match data is loaded
        # When I swap the order of the two teams
        a = engine.head_to_head("Flamengo", "Fluminense")
        b = engine.head_to_head("Fluminense", "Flamengo")
        # Then the totals match and the wins swap sides
        assert a["total_matches"] == b["total_matches"]
        assert a["team_a_wins"] == b["team_b_wins"]
        assert a["draws"] == b["draws"]


class TestTopScoringTeam:
    def test_returns_team_with_most_goals_in_a_season(self, engine):
        # Given the match data is loaded
        # When I ask which team scored most in the 2019 Série A
        result = engine.top_scoring_team(season=2019,
                                         competition="Brasileirão Série A")
        # Then a single leading team with a positive goal tally is returned
        assert len(result["teams"]) == 1
        assert result["teams"][0]["goals_for"] > 0
