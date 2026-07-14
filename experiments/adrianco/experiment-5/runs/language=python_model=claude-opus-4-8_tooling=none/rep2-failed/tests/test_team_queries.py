"""
Context
=======
Feature: Team Queries  (TASK.md section 2)

Scenario: Get team statistics for a season
Scenario: Home vs away record
Scenario: Distinguish clubs that differ only by state (Atlético-MG vs -PR)
"""

from __future__ import annotations


class TestTeamStatistics:
    def test_team_record_fields_present_and_consistent(self, graph):
        # WHEN I request statistics for Palmeiras in 2019
        stats = graph.team_stats("Palmeiras", season=2019, competition="Brasileirão")
        # THEN I receive wins, draws, losses and goals that reconcile
        assert stats is not None
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["played"]
        assert stats["points"] == stats["wins"] * 3 + stats["draws"]
        assert stats["goal_difference"] == stats["goals_for"] - stats["goals_against"]

    def test_corinthians_2019_home_record_is_a_full_half_season(self, graph):
        # A 20-team league plays 19 home games per season.
        stats = graph.team_stats("Corinthians", season=2019, venue="home",
                                 competition="Brasileirão")
        assert stats["played"] == 19

    def test_home_and_away_split_sums_to_overall(self, graph):
        overall = graph.team_stats("Flamengo", season=2019, competition="Brasileirão")
        home = graph.team_stats("Flamengo", season=2019, venue="home",
                                competition="Brasileirão")
        away = graph.team_stats("Flamengo", season=2019, venue="away",
                                competition="Brasileirão")
        assert home["played"] + away["played"] == overall["played"]
        assert home["wins"] + away["wins"] == overall["wins"]

    def test_unknown_team_returns_none(self, graph):
        assert graph.team_stats("Definitely Not A Club") is None


class TestStateDisambiguation:
    def test_atletico_mg_and_pr_are_distinct_teams(self, graph):
        # GIVEN two clubs distinguished only by state
        mg = graph.resolve_team("Atletico-MG")
        pr = graph.resolve_team("Atletico-PR")
        # THEN they resolve to different canonical ids
        assert mg is not None and pr is not None
        assert mg != pr

    def test_atletico_mg_plays_a_full_season_not_a_merged_one(self, graph):
        # WHEN we count Atlético-MG's 2019 Série A games
        stats = graph.team_stats("Atletico-MG", season=2019, competition="Brasileirão")
        # THEN it is a single 38-game season, not an inflated merge
        assert stats["played"] == 38
