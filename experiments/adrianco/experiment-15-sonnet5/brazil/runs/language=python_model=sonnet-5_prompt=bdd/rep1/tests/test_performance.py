"""BDD specs for the "Query Performance" success criteria in TASK.md:
simple lookups under 2 seconds, aggregate queries under 5 seconds, once
the dataset is loaded (loading happens once at server startup, not per
query, so it is measured separately and isn't part of these budgets).
"""

import time


class TestSimpleLookupPerformance:
    def test_given_a_loaded_graph_when_a_team_is_resolved_then_it_responds_in_under_two_seconds(self, graph):
        # Given the knowledge graph is already built (as it would be at
        # server startup)
        start = time.perf_counter()
        # When a simple team lookup is performed
        graph.resolve_team("Flamengo")
        elapsed = time.perf_counter() - start
        # Then it responds well within the 2 second budget for simple lookups
        assert elapsed < 2.0

    def test_given_a_loaded_engine_when_matches_are_searched_then_it_responds_in_under_two_seconds(self, engine):
        # Given "When did Flamengo last play Corinthians?" - a simple lookup
        start = time.perf_counter()
        engine.search_matches(team="Flamengo", opponent="Corinthians")
        elapsed = time.perf_counter() - start
        # Then it responds within the 2 second budget
        assert elapsed < 2.0


class TestAggregateQueryPerformance:
    def test_given_a_loaded_engine_when_standings_are_calculated_then_it_responds_in_under_five_seconds(self, engine):
        # Given "Who won the 2019 Brasileirao?" - an aggregate calculation
        # across a full season of match results
        start = time.perf_counter()
        engine.standings("Brasileirao", 2019)
        elapsed = time.perf_counter() - start
        # Then it responds within the 5 second budget for aggregate queries
        assert elapsed < 5.0

    def test_given_a_loaded_engine_when_brazilian_players_by_club_is_computed_then_it_responds_in_under_five_seconds(
        self, engine
    ):
        # Given a cross-file aggregate: Brazilian players grouped by club
        # across both the match and player datasets
        start = time.perf_counter()
        engine.brazilian_players_by_club()
        elapsed = time.perf_counter() - start
        # Then it responds within the 5 second budget
        assert elapsed < 5.0

    def test_given_a_loaded_engine_when_head_to_head_is_computed_repeatedly_then_average_latency_is_low(self, engine):
        # Given repeated head-to-head lookups, as a busy MCP server would see
        start = time.perf_counter()
        for _ in range(20):
            engine.head_to_head("Flamengo", "Fluminense")
        elapsed = time.perf_counter() - start
        # Then the average per-call latency stays well under the aggregate budget
        assert (elapsed / 20) < 1.0
