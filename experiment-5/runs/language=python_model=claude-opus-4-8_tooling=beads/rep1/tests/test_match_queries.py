"""
================================================================================
Feature: Match Queries
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Implements the spec's Gherkin scenarios for finding matches between teams, by
season, by competition, and computing head-to-head records.
================================================================================
"""

from data_loader import SERIE_A, COPA_BRASIL


class TestFindMatchesBetweenTeams:
    """Scenario: Find matches between two teams."""

    def test_returns_matches_with_required_fields(self, graph):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        matches = graph.find_matches(team="Flamengo", team2="Fluminense")
        # Then I receive a non-empty list
        assert matches
        # And each match has date, scores and a competition
        for m in matches:
            assert m.competition
            assert {m.home_key, m.away_key} == {"flamengo", "fluminense"}

    def test_results_sorted_recent_first(self, graph):
        # Then results are ordered most-recent first
        matches = graph.find_matches(team="Flamengo", team2="Fluminense")
        dates = [m.date for m in matches if m.date]
        assert dates == sorted(dates, reverse=True)


class TestFindMatchesBySeason:
    """Scenario: What matches did Palmeiras play in 2023?"""

    def test_palmeiras_2023(self, graph):
        # Given the data is loaded
        # When I ask for Palmeiras matches in 2023
        matches = graph.find_matches(team="Palmeiras", season=2023)
        # Then every returned match is in 2023 and involves Palmeiras
        assert matches
        for m in matches:
            assert m.season == 2023
            assert "palmeiras" in (m.home_key, m.away_key)


class TestFindMatchesByCompetition:
    def test_filter_by_competition(self, graph):
        # When I scope a team's matches to the Copa do Brasil
        matches = graph.find_matches(team="Flamengo", competition=COPA_BRASIL)
        # Then only Copa do Brasil matches are returned
        assert matches
        assert all(m.competition == COPA_BRASIL for m in matches)


class TestVenueFilter:
    def test_home_only(self, graph):
        # When I ask for Corinthians home matches in 2022 Série A
        matches = graph.find_matches(team="Corinthians", season=2022,
                                     competition=SERIE_A, venue="home")
        # Then Corinthians is the home team in every result (19 league home games)
        assert len(matches) == 19
        assert all(m.home_key == "corinthians" for m in matches)


class TestHeadToHead:
    """Scenario: Head-to-head record between two teams."""

    def test_h2h_totals_are_consistent(self, graph):
        # Given the data is loaded
        # When I request the Fla-Flu head-to-head
        h = graph.head_to_head("Flamengo", "Fluminense")
        # Then wins + draws account for every match
        assert h["total_matches"] > 0
        assert h["team_a_wins"] + h["team_b_wins"] + h["draws"] == h["total_matches"]
        # And the recent-meetings list is bounded by the total
        assert len(h["matches"]) <= h["total_matches"]

    def test_h2h_is_symmetric(self, graph):
        # Then swapping the argument order swaps the win columns
        a = graph.head_to_head("Flamengo", "Fluminense")
        b = graph.head_to_head("Fluminense", "Flamengo")
        assert a["team_a_wins"] == b["team_b_wins"]
        assert a["draws"] == b["draws"]
        assert a["total_matches"] == b["total_matches"]


class TestLastMeeting:
    """Scenario: When did Flamengo last play Corinthians?"""

    def test_most_recent_match_is_first(self, graph):
        matches = graph.find_matches(team="Flamengo", team2="Corinthians")
        assert matches
        most_recent = matches[0]
        assert most_recent.date == max(m.date for m in matches if m.date)
