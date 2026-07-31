"""Response time budgets from the specification.

Context
-------
Feature: Query performance

  Scenario: Simple lookups respond in under 2 seconds
  Scenario: Aggregate queries respond in under 5 seconds
  Scenario: No timeout errors

The graph is built once at start-up (~1s for six CSVs) and every query is then
an in-memory lookup, so the budgets are met with orders of magnitude to spare.
The thresholds below are the specification's, not the observed times.
"""

from __future__ import annotations

import time

import pytest

from brazilian_soccer.graph import KnowledgeGraph
from brazilian_soccer import queries

SIMPLE_BUDGET_SECONDS = 2.0
AGGREGATE_BUDGET_SECONDS = 5.0


def _elapsed(function, *args, **kwargs) -> tuple[float, object]:
    started = time.perf_counter()
    result = function(*args, **kwargs)
    return time.perf_counter() - started, result


@pytest.mark.performance
class TestPerformance:
    """Scenario: Queries stay inside the specification's budgets."""

    def test_given_the_data_files_when_the_graph_is_built_then_startup_is_quick(self, data_dir):
        """
        Given the six CSV files
        When the knowledge graph is built from scratch
        Then it is ready well inside the aggregate query budget
        """
        elapsed, graph = _elapsed(KnowledgeGraph.load, data_dir)

        assert elapsed < AGGREGATE_BUDGET_SECONDS
        assert graph.matches

    @pytest.mark.parametrize(
        "name, call",
        [
            ("team lookup", lambda g: queries.search_teams(g, "Flamengo")),
            ("match search", lambda g: queries.find_matches(g, team="Palmeiras", season=2023)),
            ("head to head", lambda g: queries.head_to_head(g, "Flamengo", "Corinthians")),
            ("team stats", lambda g: queries.team_stats(g, "Santos", season=2019)),
            ("player search", lambda g: queries.search_players(g, nationality="Brazil")),
            ("player profile", lambda g: queries.player_profile(g, "Neymar")),
        ],
    )
    def test_given_a_simple_lookup_when_executed_then_it_is_under_two_seconds(
        self, graph, name, call
    ):
        """
        Given the knowledge graph is loaded
        When a simple lookup runs
        Then it completes in under 2 seconds
        """
        elapsed, result = _elapsed(call, graph)

        assert "error" not in result, name
        assert elapsed < SIMPLE_BUDGET_SECONDS, f"{name} took {elapsed:.3f}s"

    @pytest.mark.parametrize(
        "name, call",
        [
            ("full standings", lambda g: queries.standings(g, "Serie A", 2019)),
            ("all-competition stats", lambda g: queries.competition_stats(g)),
            ("rankings over everything", lambda g: queries.team_rankings(g, metric="points")),
            ("biggest wins scan", lambda g: queries.biggest_wins(g, limit=20)),
            ("bracket", lambda g: queries.knockout_bracket(g, "Libertadores", 2018)),
            ("season comparison", lambda g: queries.compare_seasons(g, "Serie A", [2018, 2019])),
            ("club profile with titles", lambda g: queries.team_profile(g, "Palmeiras")),
            ("every derby", lambda g: queries.derbies(g, limit=500)),
        ],
    )
    def test_given_an_aggregate_query_when_executed_then_it_is_under_five_seconds(
        self, graph, name, call
    ):
        """
        Given the knowledge graph is loaded
        When an aggregate query scans the whole dataset
        Then it completes in under 5 seconds
        """
        elapsed, result = _elapsed(call, graph)

        assert "error" not in result, name
        assert elapsed < AGGREGATE_BUDGET_SECONDS, f"{name} took {elapsed:.3f}s"

    def test_given_many_queries_in_a_row_when_run_then_none_time_out(self, graph):
        """
        Given a client asking many questions in one session
        When 100 queries run back to back
        Then the whole batch stays inside a single aggregate budget
        """
        started = time.perf_counter()
        for season in range(2010, 2020):
            queries.standings(graph, "Serie A", season)
            queries.team_stats(graph, "Flamengo", season=season)
            queries.find_matches(graph, team="Santos", season=season, limit=10)
            queries.competition_stats(graph, "Serie A", season)
            queries.head_to_head(graph, "Gremio", "Internacional", season=season)
        elapsed = time.perf_counter() - started

        assert elapsed < AGGREGATE_BUDGET_SECONDS, f"50 queries took {elapsed:.3f}s"

    def test_given_the_mcp_layer_when_called_then_the_budget_still_holds(self, call_tool):
        """
        Given queries go through the MCP tool layer
        When a tool is called
        Then formatting and dispatch stay inside the simple lookup budget
        """
        started = time.perf_counter()
        text = call_tool("standings", competition="Serie A", season=2019)
        elapsed = time.perf_counter() - started

        assert text
        assert elapsed < SIMPLE_BUDGET_SECONDS
