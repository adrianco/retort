# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : tests.test_team_queries
# Purpose : BDD scenarios for category 2 (Team Queries): win/draw/loss records,
#           goals for/against, and venue/competition filtering. Includes the
#           spec's Gherkin "Get team statistics" scenario.
# =============================================================================


class TestTeamStatistics:
    """Feature: Team statistics.

    Scenario: Get team statistics
      Given the match data is loaded
      When I request statistics for "Palmeiras" in season "2019"
      Then I should receive wins, losses, draws, and goals
    """

    def test_returns_full_record(self, graph):
        s = graph.team_stats("Palmeiras", season=2019, competition="Brasileirão")
        for key in ("wins", "draws", "losses", "goals_for", "goals_against"):
            assert key in s
        # Then the record is internally consistent
        assert s["wins"] + s["draws"] + s["losses"] == s["matches"]
        assert s["points"] == s["wins"] * 3 + s["draws"]

    def test_home_record_full_season(self, graph):
        # Given a team in a complete season (2019), When I ask for its home record
        s = graph.team_stats(
            "Flamengo", season=2019, competition="Brasileirão", venue="home"
        )
        # Then a full Brasileirão season is 19 home games
        assert s["matches"] == 19
        assert 0 <= s["win_rate"] <= 100

    def test_venue_filter_partitions_matches(self, graph):
        # The home + away match counts should sum to the all-venue count
        home = graph.team_stats("Corinthians", season=2019, competition="Brasileirão", venue="home")
        away = graph.team_stats("Corinthians", season=2019, competition="Brasileirão", venue="away")
        both = graph.team_stats("Corinthians", season=2019, competition="Brasileirão")
        assert home["matches"] + away["matches"] == both["matches"]

    def test_win_rate_calculation(self, graph):
        s = graph.team_stats("Flamengo", season=2019, competition="Brasileirão")
        if s["matches"]:
            expected = round(100 * s["wins"] / s["matches"], 1)
            assert s["win_rate"] == expected


class TestTopScoringTeams:
    """Feature: Which team scored the most goals in a season."""

    def test_ranked_descending(self, graph):
        ranked = graph.top_scoring_teams(competition="Brasileirão", season=2019)
        goals = [r["goals"] for r in ranked]
        assert goals == sorted(goals, reverse=True)
        # The 2019 champion Flamengo was also the top scorer
        assert ranked[0]["team"].lower().startswith("flamengo")
