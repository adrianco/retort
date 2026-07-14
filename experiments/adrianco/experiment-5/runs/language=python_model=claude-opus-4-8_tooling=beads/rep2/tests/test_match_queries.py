"""
================================================================================
test_match_queries.py - BDD scenarios for match search
================================================================================

Feature: Match Queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition.
================================================================================
"""


class TestFindMatches:
    def test_find_matches_between_two_teams(self, engine):
        # When I search for matches between Flamengo and Fluminense
        result = engine.find_matches(team="Flamengo", opponent="Fluminense")
        # Then I receive a non-empty list
        assert result["total"] > 0
        # And every match carries date, scores and competition
        for m in result["matches"]:
            assert "date" in m and m["competition"]
            assert m["home_goal"] is not None and m["away_goal"] is not None
            # And both clubs are present (in either home/away slot)
            teams = {m["home_team"], m["away_team"]}
            assert "Flamengo" in teams and "Fluminense" in teams

    def test_find_matches_by_team_and_season(self, engine):
        # When I ask what matches Palmeiras played in 2019
        result = engine.find_matches(team="Palmeiras", season=2019)
        # Then I get a full league season's worth of fixtures
        assert result["total"] >= 30
        assert all(m["season"] == 2019 for m in result["matches"])

    def test_find_matches_by_competition(self, engine):
        # When I scope a search to Copa do Brasil
        result = engine.find_matches(team="Flamengo", competition="Copa do Brasil")
        assert result["total"] > 0
        assert all(m["competition"] == "Copa do Brasil" for m in result["matches"])

    def test_team_name_variation_resolves(self, engine):
        # Given the suffixed and bare spellings of a club
        a = engine.find_matches(team="Palmeiras-SP", season=2019)
        b = engine.find_matches(team="Palmeiras", season=2019)
        # Then both return the same number of matches
        assert a["total"] == b["total"] and a["total"] > 0

    def test_limit_is_respected(self, engine):
        result = engine.find_matches(team="Corinthians", limit=5)
        assert result["returned"] <= 5
        assert result["total"] >= result["returned"]


class TestLastMatch:
    def test_last_meeting_between_two_teams(self, engine):
        # When I ask when Flamengo last played Corinthians
        result = engine.last_match("Flamengo", "Corinthians")
        # Then a dated fixture is returned
        assert result["found"]
        assert result["match"]["date"] is not None
        assert result["total_meetings"] > 1

    def test_no_meeting_returns_not_found(self, engine):
        # Given two teams that never met in the data
        result = engine.last_match("Flamengo", "Not A Real Team XYZ")
        assert result["found"] is False
