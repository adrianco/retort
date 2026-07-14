"""
================================================================================
 BDD tests: Match Queries (capability category 1)
================================================================================
Feature: Match Queries
  As an LLM client of the Brazilian Soccer MCP server
  I want to find matches by team, opponent, competition, season and date
  So that I can answer match-related questions.
================================================================================
"""


class TestFindMatchesBetweenTwoTeams:
    def test_returns_matches_with_date_score_and_competition(self, engine):
        # Given the match data is loaded
        # When I search for matches between Flamengo and Fluminense
        result = engine.find_matches(team="Flamengo", opponent="Fluminense")
        # Then I receive a non-empty list of matches
        assert result["count"] > 0
        # And each match has date, scores and competition
        for m in result["matches"]:
            assert "date" in m and "competition" in m
            assert isinstance(m["home_goal"], int)
            assert isinstance(m["away_goal"], int)
        # And a head-to-head summary is included
        h2h = result["head_to_head"]
        assert h2h["total_matches"] == result["count"]
        assert (h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
                == result["count"])


class TestFindMatchesByTeamAndSeason:
    def test_palmeiras_in_2022_returns_only_2022_matches(self, engine):
        # Given the match data is loaded
        # When I ask for Palmeiras matches in 2022
        result = engine.find_matches(team="Palmeiras", season=2022)
        # Then there are matches and all are from 2022
        assert result["count"] > 0
        assert all(m["season"] == 2022 for m in result["matches"])


class TestFindMatchesByCompetition:
    def test_filtering_by_competition_restricts_results(self, engine):
        # Given the match data is loaded
        # When I ask for Libertadores matches
        result = engine.find_matches(competition="Libertadores", limit=50)
        # Then every returned match is from the Copa Libertadores
        assert result["count"] > 0
        assert all("Libertadores" in m["competition"] for m in result["matches"])


class TestFindMatchesByDateRange:
    def test_date_range_filters_matches(self, engine):
        # Given the match data is loaded
        # When I ask for matches in a specific window
        result = engine.find_matches(date_from="2019-01-01", date_to="2019-12-31",
                                     competition="Brasileirão Série A")
        # Then all matches fall within that window
        assert result["count"] > 0
        assert all("2019-01-01" <= m["date"] <= "2019-12-31"
                   for m in result["matches"])


class TestLastMatchBetween:
    def test_returns_single_most_recent_match(self, engine):
        # Given the match data is loaded
        # When I ask when Flamengo last played Corinthians
        m = engine.last_match_between("Flamengo", "Corinthians")
        # Then I get one match involving both teams with a score
        assert m is not None
        teams = {m["home_team"].lower(), m["away_team"].lower()}
        assert any("flamengo" in t for t in teams)
        assert any("corinthians" in t for t in teams)
        assert isinstance(m["home_goal"], int)
