"""
BDD scenarios -- Match Queries (Given / When / Then).

Feature: Match Queries
    As an analyst
    I want to find matches by team, opponent, competition, season and date
    So that I can answer questions about who played whom and what happened.
"""

import datetime


class TestFindMatchesBetweenTwoTeams:
    """Scenario: Find matches between two teams."""

    def test_returns_matches_with_date_scores_and_competition(self, kg):
        # Given the match data is loaded (kg fixture)
        # When I search for matches between Flamengo and Fluminense
        matches = kg.find_matches(team="Flamengo", opponent="Fluminense")

        # Then I should receive a non-empty list of matches
        assert len(matches) > 0
        # And each match should have a date, scores and a competition
        for m in matches:
            assert m.competition
            assert m.home_goal is not None and m.away_goal is not None
            # And exactly the two teams are involved
            sides = {m.home_team.lower(), m.away_team.lower()}
            assert any("flamengo" in s for s in sides)
            assert any("fluminense" in s for s in sides)


class TestTeamNameVariations:
    """Scenario: Team name suffix variations resolve to the same team."""

    def test_suffix_and_plain_names_match(self, kg):
        # Given the match data is loaded
        # When I search using a plain name and a state-suffixed name
        plain = kg.find_matches(team="Palmeiras")
        suffixed = kg.find_matches(team="Palmeiras-SP")

        # Then both resolve to the same (non-empty) set of matches
        assert len(plain) > 0
        assert len(plain) == len(suffixed)


class TestFilterByCompetition:
    """Scenario: Filter matches by competition."""

    def test_only_requested_competition_returned(self, kg):
        # Given the match data is loaded
        # When I search Flamengo matches in the Libertadores
        matches = kg.find_matches(team="Flamengo", competition="Libertadores")

        # Then every returned match belongs to that competition
        assert len(matches) > 0
        assert all(m.competition == "Libertadores" for m in matches)


class TestFilterBySeasonAndDateRange:
    """Scenario: Filter matches by season and by date range."""

    def test_season_filter(self, kg):
        # When I ask for Palmeiras matches in 2019
        matches = kg.find_matches(team="Palmeiras", season=2019)
        # Then all returned matches are from 2019
        assert len(matches) > 0
        assert all(m.season == 2019 for m in matches)

    def test_date_range_filter(self, kg):
        # When I bound the search by a date range
        start = datetime.date(2019, 1, 1)
        end = datetime.date(2019, 6, 30)
        matches = kg.find_matches(team="Palmeiras", start_date=start, end_date=end)
        # Then every match falls inside the range
        assert all(start <= m.date <= end for m in matches)


class TestVenueFilter:
    """Scenario: Restrict matches to a team's home games."""

    def test_home_only(self, kg):
        # When I request only Corinthians home matches in 2022 Brasileirao
        matches = kg.find_matches(
            team="Corinthians", season=2022,
            competition="Brasileirao", venue="home",
        )
        # Then the team is the home side in every returned match
        assert len(matches) > 0
        for m in matches:
            assert "corinthians" in m.home_team.lower()


class TestResultsSortedRecentFirst:
    """Scenario: Match results are ordered most-recent first."""

    def test_descending_by_date(self, kg):
        matches = kg.find_matches(team="Santos", limit=50)
        dated = [m.date for m in matches if m.date]
        assert dated == sorted(dated, reverse=True)
