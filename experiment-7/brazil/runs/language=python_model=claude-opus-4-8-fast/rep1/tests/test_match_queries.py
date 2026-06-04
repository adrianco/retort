"""
================================================================================
tests.test_match_queries
================================================================================

CONTEXT
-------
BDD scenarios for Required Capability #1 (Match Queries): find matches by team,
opponent, competition, season and date range, and the simple-lookup sample
questions ("When did Flamengo last play Corinthians?", "What was the score?").
================================================================================
"""


class TestMatchQueries:
    """Feature: Match Queries."""

    def test_find_matches_between_two_teams(self, kg):
        # Scenario: Find matches between two teams
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        matches = kg.find_matches(team="Flamengo", opponent="Fluminense")
        # Then I should receive a non-empty list of matches
        assert len(matches) > 0
        # And each match should have date, scores, and competition
        for m in matches:
            assert m["competition"]
            assert m["home_goal"] is not None and m["away_goal"] is not None
            # And both teams are one of the two requested
            teams = {m["home_team"], m["away_team"]}
            assert any("Flamengo" in t for t in teams)
            assert any("Fluminense" in t for t in teams)

    def test_find_matches_by_team_and_season(self, kg):
        # When I ask "What matches did Palmeiras play in 2019?"
        matches = kg.find_matches(team="Palmeiras", season=2019)
        # Then all returned matches are from 2019 and involve Palmeiras
        assert len(matches) > 0
        assert all(m["season"] == 2019 for m in matches)
        assert all("Palmeiras" in (m["home_team"] + m["away_team"]) for m in matches)

    def test_find_matches_by_competition(self, kg):
        # When I filter by the Libertadores competition
        matches = kg.find_matches(team="Flamengo", competition="Libertadores")
        # Then every match is a Libertadores match
        assert len(matches) > 0
        assert all("Libertadores" in m["competition"] for m in matches)

    def test_find_matches_by_date_range(self, kg):
        # When I search a specific date window
        matches = kg.find_matches(
            team="Corinthians", start_date="2019-01-01", end_date="2019-12-31"
        )
        # Then all matches fall inside the window
        assert len(matches) > 0
        assert all("2019-01-01" <= m["date"] <= "2019-12-31" for m in matches)

    def test_last_meeting_returns_most_recent(self, kg):
        # Scenario: "When did Flamengo last play Corinthians? What was the score?"
        m = kg.last_meeting("Flamengo", "Corinthians")
        # Then a single most-recent match with a score is returned
        assert m is not None
        assert m["date"] is not None
        assert isinstance(m["home_goal"], int) and isinstance(m["away_goal"], int)
        # And it is the latest of all their meetings
        all_meetings = kg.find_matches(team="Flamengo", opponent="Corinthians")
        latest = max(x["date"] for x in all_meetings if x["date"])
        assert m["date"] == latest

    def test_matches_are_sorted_chronologically(self, kg):
        matches = kg.find_matches(team="Santos", opponent="Palmeiras")
        dates = [m["date"] for m in matches if m["date"]]
        assert dates == sorted(dates)
