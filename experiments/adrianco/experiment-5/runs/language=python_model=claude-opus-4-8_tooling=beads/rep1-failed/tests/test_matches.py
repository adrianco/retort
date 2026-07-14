"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
File      : tests/test_matches.py
Purpose   : BDD tests for match queries (brazilian_soccer.queries.matches).

Mirrors the Gherkin "Feature: Match Queries" scenarios from the spec:
finding matches between two teams, filtering by season/competition, and
computing head-to-head records.
================================================================================
"""

from brazilian_soccer.queries import matches


class TestFindMatchesBetweenTeams:
    def test_returns_matches_with_required_fields(self, kg):
        # Given the match data is loaded (kg fixture)
        # When I search for matches between Flamengo and Fluminense
        result = matches.find_matches(kg, team="Flamengo", opponent="Fluminense")
        # Then I receive a non-empty list
        assert len(result) > 0
        # And each match has a date, scores and a competition
        for m in result:
            assert "date" in m
            assert "home_goal" in m and "away_goal" in m
            assert m["competition"]
            # And both teams are present in the fixture
            teams = {m["home_team"], m["away_team"]}
            assert any("Flamengo" in t for t in teams)
            assert any("Fluminense" in t for t in teams)

    def test_results_are_sorted_newest_first(self, kg):
        # When I list a team's matches
        result = matches.find_matches(kg, team="Palmeiras", limit=50)
        dated = [m["date"] for m in result if m["date"]]
        # Then they are in descending date order
        assert dated == sorted(dated, reverse=True)

    def test_filter_by_season(self, kg):
        # When I search Palmeiras matches in 2019
        result = matches.find_matches(kg, team="Palmeiras", season=2019)
        # Then every returned match is from 2019
        assert result
        assert all(m["season"] == 2019 for m in result)

    def test_filter_by_competition(self, kg):
        # When I search for Libertadores matches only
        result = matches.find_matches(kg, competition="Libertadores", limit=20)
        assert result
        assert all(m["competition"] == "Libertadores" for m in result)

    def test_home_only_restricts_role(self, kg):
        # When I ask for Corinthians home matches
        result = matches.find_matches(kg, team="Corinthians", home_only=True, limit=30)
        # Then Corinthians is the home team in every result
        assert result
        assert all("Corinthians" in m["home_team"] for m in result)


class TestHeadToHead:
    def test_totals_are_consistent(self, kg):
        # When I request the Fla-Flu head-to-head
        h2h = matches.head_to_head(kg, "Flamengo", "Fluminense")
        # Then wins + draws never exceed the number of matches
        assert h2h["total_matches"] > 0
        played = h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
        assert played <= h2h["total_matches"]

    def test_is_symmetric(self, kg):
        # Given the rivalry queried in both orders
        ab = matches.head_to_head(kg, "Santos", "Palmeiras")
        ba = matches.head_to_head(kg, "Palmeiras", "Santos")
        # Then the totals agree and the wins swap
        assert ab["total_matches"] == ba["total_matches"]
        assert ab["team_a_wins"] == ba["team_b_wins"]
        assert ab["draws"] == ba["draws"]


class TestLastMatch:
    def test_returns_most_recent(self, kg):
        # When I ask when two teams last met
        last = matches.last_match(kg, "Flamengo", "Corinthians")
        # Then a single dated match is returned
        assert last is not None
        assert last["date"]
