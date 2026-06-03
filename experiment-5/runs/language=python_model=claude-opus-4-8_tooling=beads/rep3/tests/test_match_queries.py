"""
==============================================================================
File: tests/test_match_queries.py
==============================================================================
CONTEXT
-------
BDD (Given-When-Then) tests for the MATCH query category (spec section 1) and
the Gherkin scenarios in the specification:

    Scenario: Find matches between two teams
    Scenario: Most recent meeting / head-to-head
==============================================================================
"""

from brazilian_soccer import queries as q


class TestFindMatches:
    def test_find_matches_between_two_teams(self, graph):
        # Given the match data is loaded
        # When I search for matches between Flamengo and Fluminense
        result = q.find_matches(graph, team="Flamengo", opponent="Fluminense")
        # Then I receive a non-empty list
        assert result["count"] > 0
        # And each match has date, scores and competition
        for m in result["matches"]:
            assert "date" in m and "competition" in m
            assert m["home_goal"] is not None and m["away_goal"] is not None

    def test_find_matches_by_team_and_season(self, graph):
        # Given the data / When I ask for Palmeiras matches in 2019
        result = q.find_matches(graph, team="Palmeiras", season=2019)
        # Then all returned matches are from 2019 and involve Palmeiras
        assert result["count"] > 0
        for m in result["matches"]:
            assert m["season"] == 2019
            assert "Palmeiras" in (m["home"] + m["away"])

    def test_find_matches_home_only(self, graph):
        # Given the data / When I ask for Corinthians HOME matches in 2022
        result = q.find_matches(
            graph, team="Corinthians", season=2022,
            competition="Brasileirão", home_only=True,
        )
        # Then every returned match has Corinthians as the home side
        assert result["count"] > 0
        for m in result["matches"]:
            assert "Corinthians" in m["home"]

    def test_find_matches_by_competition(self, graph):
        # Given the data / When I filter by Libertadores
        result = q.find_matches(graph, team="Flamengo", competition="Libertadores")
        # Then all matches are Libertadores matches
        assert result["count"] > 0
        assert all(m["competition"] == "Libertadores" for m in result["matches"])


class TestHeadToHead:
    def test_fla_flu_head_to_head_totals_are_consistent(self, graph):
        # Given the data / When I compute the Fla-Flu head-to-head
        h = q.head_to_head(graph, "Flamengo", "Fluminense")
        # Then wins + draws account for every scored match
        assert h["total_matches"] > 0
        assert (
            h["team_a_wins"] + h["team_b_wins"] + h["draws"]
            <= h["total_matches"]
        )
        assert "wins" in h["summary"]

    def test_last_meeting_returns_most_recent(self, graph):
        # Given the data / When I ask when Flamengo last played Corinthians
        result = q.last_meeting(graph, "Flamengo", "Corinthians")
        # Then a single most-recent match is returned with a score
        assert result["found"] is True
        assert result["match"]["home_goal"] is not None

    def test_head_to_head_symmetry(self, graph):
        # Given the data / When swapping the team order
        ab = q.head_to_head(graph, "Palmeiras", "Santos")
        ba = q.head_to_head(graph, "Santos", "Palmeiras")
        # Then totals are identical and wins mirror
        assert ab["total_matches"] == ba["total_matches"]
        assert ab["team_a_wins"] == ba["team_b_wins"]
        assert ab["draws"] == ba["draws"]
