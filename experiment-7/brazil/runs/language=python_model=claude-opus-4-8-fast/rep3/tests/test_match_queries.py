"""
================================================================================
Context
================================================================================
Test module: test_match_queries.py
Project:     Brazilian Soccer MCP Server
Feature:     Match Queries (capability category 1).
Style:       BDD Given-When-Then, mirroring the Gherkin scenarios in TASK.md.
================================================================================
"""

from datetime import date


class TestFindMatchesBetweenTeams:
    def test_find_matches_between_two_teams(self, kg):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        matches = kg.match_between("Flamengo", "Fluminense")
        # Then I should receive a list of matches
        assert len(matches) > 0
        # And each match should have scores and a competition
        for m in matches:
            assert m.competition
            assert m.home_goal is not None and m.away_goal is not None
            # And each match actually involves both teams
            keys = {m.home_key, m.away_key}
            assert "flamengo" in keys and "fluminense" in keys

    def test_results_are_sorted_most_recent_first(self, kg):
        # Given matches between two teams
        # When listed
        # Then dated matches descend by date
        matches = [m for m in kg.match_between("Palmeiras", "Santos") if m.date]
        dates = [m.date for m in matches]
        assert dates == sorted(dates, reverse=True)


class TestFindMatchesByCriteria:
    def test_filter_by_season_and_team(self, kg):
        # When I ask what matches Palmeiras played in 2019
        matches = kg.find_matches(team="Palmeiras", season=2019,
                                  competition="brasileirao", dedup=True)
        # Then all returned matches are from 2019 and involve Palmeiras
        assert len(matches) == 38
        assert all(m.season == 2019 for m in matches)
        assert all(m.involves("palmeiras") for m in matches)

    def test_filter_by_venue_home(self, kg):
        # When I request only home matches for a team in a season
        home = kg.find_matches(team="Corinthians", season=2019,
                               competition="brasileirao", venue="home", dedup=True)
        # Then every match has that team at home
        assert all(m.home_key == "corinthians" for m in home)
        assert len(home) == 19

    def test_filter_by_date_range(self, kg):
        # When I restrict to a date window
        start, end = date(2019, 1, 1), date(2019, 12, 31)
        matches = kg.find_matches(team="Flamengo", start_date=start, end_date=end)
        # Then all matches fall within the window
        assert matches
        assert all(start <= m.date <= end for m in matches)

    def test_filter_by_competition(self, kg):
        # When I request Libertadores matches for a Brazilian club
        matches = kg.find_matches(team="Flamengo", competition="libertadores")
        # Then they are all Copa Libertadores fixtures
        assert matches
        assert all(m.competition == "Copa Libertadores" for m in matches)
