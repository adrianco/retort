"""BDD-style tests for match-level queries.

Feature: Match Queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition.
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as Q


class TestFindMatches:
    def test_find_matches_between_flamengo_and_fluminense(self, store):
        # Given the match data is loaded
        # When I search for matches between two teams
        results = Q.find_matches(store, team="Flamengo", opponent="Fluminense", limit=500)
        # Then I get a non-trivial list of matches
        assert len(results) > 10
        # And each match has date, scores, and competition
        for match in results:
            assert "date" in match
            assert "home_team" in match and "away_team" in match
            assert isinstance(match["home_goals"], int)
            assert isinstance(match["away_goals"], int)
            assert match["competition"]

    def test_filter_by_competition_and_season(self, store):
        # When I filter by season + competition
        results = Q.find_matches(
            store, team="Palmeiras", competition="Brasileirão", season=2019, limit=200
        )
        # Then every returned match is from the right season and competition
        assert results, "expected at least one match"
        assert all(m["season"] == 2019 for m in results)
        assert all(m["competition"] == "Brasileirão" for m in results)

    def test_filter_by_date_range(self, store):
        # When I filter by a date range
        results = Q.find_matches(
            store, team="Flamengo",
            date_from="2019-01-01", date_to="2019-12-31", limit=200,
        )
        # Then every match falls inside the range
        assert results
        for m in results:
            assert "2019" in m["date"]


class TestHeadToHead:
    def test_head_to_head_aggregates_wins_and_goals(self, store):
        # Given a request for a classic Brazilian derby
        h2h = Q.head_to_head(store, "Flamengo", "Fluminense")
        # Then the totals add up
        assert h2h["matches"] == h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
        assert h2h["team_a_goals"] >= 0
        assert h2h["team_b_goals"] >= 0
        assert len(h2h["match_list"]) == h2h["matches"]

    def test_head_to_head_distinguishes_atletico_mg_from_athletico_pr(self, store):
        # Given two different "Atletico" clubs in different states
        h2h = Q.head_to_head(store, "Atletico-MG", "Athletico-PR")
        # Then we still get real head-to-head matches (these clubs DO play each
        # other; just not in dozens — and crucially not in HUNDREDS, which is
        # what a name-collision bug would produce).
        assert h2h["matches"] > 0
        assert h2h["matches"] < 100
