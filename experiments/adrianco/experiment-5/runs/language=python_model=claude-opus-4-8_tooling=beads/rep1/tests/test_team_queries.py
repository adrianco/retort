"""
================================================================================
Feature: Team Queries
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Gherkin scenario: "Get team statistics" — wins/losses/draws/goals, by season,
competition and venue; plus team comparison.
================================================================================
"""

import pytest

from knowledge_graph import TeamResolutionError
from data_loader import SERIE_A


class TestTeamRecord:
    """Scenario: I request statistics for a team in a given season."""

    def test_record_is_internally_consistent(self, graph):
        # Given the match data is loaded
        # When I request Palmeiras' 2023 Série A record
        r = graph.team_record("Palmeiras", season=2023, competition=SERIE_A)
        # Then wins+draws+losses == played, and points follow 3/1/0 scoring
        assert r["wins"] + r["draws"] + r["losses"] == r["played"]
        assert r["points"] == r["wins"] * 3 + r["draws"]
        assert r["goal_difference"] == r["goals_for"] - r["goals_against"]

    def test_corinthians_home_2022(self, graph):
        # Scenario: "What is Corinthians' home record in 2022?"
        r = graph.team_record("Corinthians", season=2022,
                              competition=SERIE_A, venue="home")
        # Then there are 19 home league games and a win rate is reported
        assert r["played"] == 19
        assert 0 <= r["win_rate"] <= 100

    def test_home_plus_away_equals_all(self, graph):
        # Then home games + away games == all games for a season
        home = graph.team_record("Santos", season=2019, competition=SERIE_A, venue="home")
        away = graph.team_record("Santos", season=2019, competition=SERIE_A, venue="away")
        allg = graph.team_record("Santos", season=2019, competition=SERIE_A, venue="all")
        assert home["played"] + away["played"] == allg["played"]
        assert home["wins"] + away["wins"] == allg["wins"]


class TestCompareTeams:
    """Scenario: Compare Palmeiras and Santos head-to-head."""

    def test_comparison_contains_h2h_and_both_records(self, graph):
        c = graph.compare_teams("Palmeiras", "Santos")
        assert c["head_to_head"]["total_matches"] > 0
        assert c["team_a_record"]["team"].lower().startswith("palmeiras")
        assert c["team_b_record"]["team"].lower().startswith("santos")


class TestResolutionErrors:
    def test_unknown_team_raises(self, graph):
        # Given a team that does not exist in the data
        # When I request its record
        # Then a clear resolution error is raised
        with pytest.raises(TeamResolutionError):
            graph.team_record("Definitely Not A Club 123")
