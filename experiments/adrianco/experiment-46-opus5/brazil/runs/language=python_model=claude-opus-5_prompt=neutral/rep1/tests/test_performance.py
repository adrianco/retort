"""Feature: Query performance targets from the specification.

  Scenario: Simple lookups respond in under two seconds
  Scenario: Aggregate queries respond in under five seconds
  Scenario: No timeouts

Timings exclude the one-off CSV load, which the server performs at start-up and
which the ``graph`` fixture performs once per session.
"""

from __future__ import annotations

import time

import pytest

from brazilian_soccer import queries as q
from brazilian_soccer.graph import load_graph

SIMPLE_LOOKUP_BUDGET = 2.0
AGGREGATE_BUDGET = 5.0


class TestSimpleLookups:

    @pytest.mark.parametrize(
        "call",
        [
            lambda g: q.search_matches(g, team="Flamengo", opponent="Fluminense"),
            lambda g: q.last_meeting(g, "Flamengo", "Corinthians"),
            lambda g: q.team_stats(g, "Palmeiras", season=2023),
            lambda g: q.player_profile(g, "Neymar"),
            lambda g: q.search_players(g, club="Grêmio"),
            lambda g: q.standings(g, "Brasileirão", 2019),
            lambda g: q.list_teams(g, "atletico"),
        ],
    )
    def test_lookup_is_under_two_seconds(self, graph, fastest, call):
        """
        Given a loaded knowledge graph
        When a simple lookup runs
        Then it completes well inside the two second budget
        """
        _, elapsed = fastest(call, graph)

        assert elapsed < SIMPLE_LOOKUP_BUDGET


class TestAggregateQueries:

    @pytest.mark.parametrize(
        "call",
        [
            lambda g: q.overall_statistics(g),
            lambda g: q.competition_summary(g, "Brasileirão"),
            lambda g: q.team_rankings(g, metric="win_rate", venue="home",
                                      competition="Brasileirão", min_matches=100),
            lambda g: q.biggest_wins(g, limit=25),
            lambda g: q.players_by_club_summary(g, nationality="Brazil"),
            lambda g: q.compare_seasons(g, "Brasileirão", list(range(2010, 2020))),
            lambda g: q.derbies(g),
        ],
    )
    def test_aggregate_is_under_five_seconds(self, graph, fastest, call):
        """
        Given a loaded knowledge graph
        When an aggregate query scans every match
        Then it completes inside the five second budget
        """
        _, elapsed = fastest(call, graph)

        assert elapsed < AGGREGATE_BUDGET


class TestStartup:

    def test_loading_all_six_files_is_quick(self, fastest):
        """
        Given the server loads the CSVs once at start-up
        When the graph is built from scratch
        Then it takes a few seconds at most

        ``refresh`` bypasses the per-directory cache, so this really does parse
        all six files again rather than measuring a dictionary lookup.
        """
        from brazilian_soccer.loader import DEFAULT_DATA_DIR

        _, elapsed = fastest(load_graph, DEFAULT_DATA_DIR, attempts=2,
                             refresh=True)

        assert elapsed < 15.0

    def test_repeated_queries_do_not_degrade(self, graph):
        """
        Given a client asking many questions in a session
        When the same query runs a hundred times
        Then the total time stays small (results come from indexes)
        """
        started = time.perf_counter()
        for _ in range(100):
            q.search_matches(graph, team="Santos", season=2019)
        elapsed = time.perf_counter() - started

        assert elapsed < AGGREGATE_BUDGET
