# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : tests.test_match_queries
# Purpose : BDD scenarios for category 1 (Match Queries) of the spec: finding
#           matches by team, opponent, competition, season and date range, and
#           head-to-head aggregation. Mirrors the Gherkin feature in the spec.
# =============================================================================


class TestFindMatchesBetweenTeams:
    """Feature: Find matches between two teams.

    Scenario: Find matches between two teams
      Given the match data is loaded
      When I search for matches between "Flamengo" and "Fluminense"
      Then I should receive a list of matches
      And each match should have date, scores, and competition
    """

    def test_returns_matches_with_required_fields(self, graph):
        matches = graph.find_matches(team="Flamengo", opponent="Fluminense")
        assert len(matches) > 0
        for m in matches:
            assert m.competition
            assert m.home_goal is not None and m.away_goal is not None
            # the two teams are the only sides of the match
            sides = {m.home_team_norm, m.away_team_norm}
            assert "flamengo" in sides and "fluminense" in sides

    def test_results_sorted_recent_first(self, graph):
        matches = graph.find_matches(team="Flamengo", opponent="Fluminense")
        dates = [m.date for m in matches if m.date]
        assert dates == sorted(dates, reverse=True)


class TestFindMatchesByCriteria:
    """Feature: Find matches by team / season / competition / venue."""

    def test_by_team_and_season(self, graph):
        # When I ask what matches Palmeiras played in 2019
        matches = graph.find_matches(team="Palmeiras", season=2019)
        assert len(matches) > 0
        assert all(m.season == 2019 for m in matches)

    def test_by_competition(self, graph):
        # When I filter to the Copa do Brasil
        matches = graph.find_matches(team="Flamengo", competition="Copa do Brasil")
        assert all(m.competition == "Copa do Brasil" for m in matches)

    def test_by_venue_home_only(self, graph):
        # When I restrict to home matches
        matches = graph.find_matches(team="Corinthians", season=2022, venue="home")
        assert all(m.home_team_norm == "corinthians" for m in matches)

    def test_by_date_range(self, graph):
        matches = graph.find_matches(
            team="Santos", start_date="2019-01-01", end_date="2019-12-31"
        )
        assert all("2019-01-01" <= m.date <= "2019-12-31" for m in matches if m.date)

    def test_limit_is_respected(self, graph):
        assert len(graph.find_matches(team="Flamengo", limit=5)) == 5


class TestHeadToHead:
    """Feature: Head-to-head record between two teams."""

    def test_totals_are_consistent(self, graph):
        # When I request the Fla-Flu head-to-head
        h2h = graph.head_to_head("Flamengo", "Fluminense")
        # Then wins + draws + losses equals the number of matches
        assert h2h["matches"] > 0
        assert h2h["team1_wins"] + h2h["team2_wins"] + h2h["draws"] == h2h["matches"]
        # And goal tallies are non-negative
        assert h2h["team1_goals"] >= 0 and h2h["team2_goals"] >= 0

    def test_symmetry(self, graph):
        # The matchup count is the same regardless of argument order
        a = graph.head_to_head("Palmeiras", "Santos")
        b = graph.head_to_head("Santos", "Palmeiras")
        assert a["matches"] == b["matches"]
        assert a["team1_wins"] == b["team2_wins"]
