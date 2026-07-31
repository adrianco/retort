"""Feature: Query performance.

Context
-------
The spec's budget: simple lookups under 2 seconds, aggregate queries under 5,
no timeouts.  The graph is loaded once per process (the MCP server does this at
import time), so these tests measure query time against an already-loaded
graph -- which is what a client experiences.

Thresholds are the spec's, not the observed times; the queries actually run in
single-digit milliseconds, leaving a wide margin on slower machines.
"""

from __future__ import annotations

import time

import pytest

from brazilian_soccer.models import BRASILEIRAO, LIBERTADORES
from brazilian_soccer.queries import SoccerQueries

SIMPLE_BUDGET_SECONDS = 2.0
AGGREGATE_BUDGET_SECONDS = 5.0


def timed(callable_, *args, **kwargs) -> tuple[float, object]:
    started = time.perf_counter()
    result = callable_(*args, **kwargs)
    return time.perf_counter() - started, result


class TestSimpleLookups:
    @pytest.mark.parametrize(
        "label,call",
        [
            ("team resolution", lambda q: q.resolve_team("Flamengo")),
            ("team matches", lambda q: q.search_matches(team="Palmeiras", limit=25)),
            ("last meeting", lambda q: q.last_meeting("Flamengo", "Corinthians")),
            ("head to head", lambda q: q.head_to_head("Palmeiras", "Santos")),
            ("player by name", lambda q: q.get_player("Neymar")),
            ("club squad", lambda q: q.club_squad("Gremio")),
            ("team record", lambda q: q.team_record("Corinthians", season=2022)),
        ],
    )
    def test_simple_lookup_is_under_two_seconds(
        self, queries: SoccerQueries, label: str, call
    ) -> None:
        elapsed, result = timed(call, queries)
        assert result is not None
        assert elapsed < SIMPLE_BUDGET_SECONDS, f"{label} took {elapsed:.3f}s"


class TestAggregateQueries:
    @pytest.mark.parametrize(
        "label,call",
        [
            ("standings", lambda q: q.standings(BRASILEIRAO, 2019)),
            ("all-time competition stats", lambda q: q.competition_stats()),
            ("best away records", lambda q: q.best_records(venue="away", limit=10)),
            ("biggest wins", lambda q: q.biggest_wins(limit=20)),
            ("team profile", lambda q: q.team_profile("Flamengo")),
            ("season trend", lambda q: q.team_season_trend("Flamengo")),
            ("all derbies", lambda q: q.derbies()),
            (
                "all seasons compared",
                lambda q: q.compare_seasons(list(range(2003, 2024)), BRASILEIRAO),
            ),
            ("players grouped by club", lambda q: q.players_by_nationality_at_clubs()),
            ("bracket", lambda q: q.season_bracket(LIBERTADORES, 2019)),
        ],
    )
    def test_aggregate_query_is_under_five_seconds(
        self, queries: SoccerQueries, label: str, call
    ) -> None:
        elapsed, result = timed(call, queries)
        assert result is not None
        assert elapsed < AGGREGATE_BUDGET_SECONDS, f"{label} took {elapsed:.3f}s"


class TestBulkBehaviour:
    def test_a_hundred_lookups_stay_within_the_simple_budget_each(
        self, queries: SoccerQueries
    ) -> None:
        # Given a burst of queries such as an LLM conversation would produce
        clubs = ["Flamengo", "Palmeiras", "Santos", "Gremio", "Cruzeiro"]
        started = time.perf_counter()
        for _ in range(20):
            for club in clubs:
                queries.team_record(club, season=2019)
        elapsed = time.perf_counter() - started
        # Then the average stays far inside the per-query budget
        assert elapsed / 100 < SIMPLE_BUDGET_SECONDS
        assert elapsed < AGGREGATE_BUDGET_SECONDS

    def test_full_dataset_scan_completes(self, queries: SoccerQueries) -> None:
        elapsed, matches = timed(queries.search_matches, limit=None)
        assert len(matches) > 17000
        assert elapsed < AGGREGATE_BUDGET_SECONDS

    def test_graph_loads_once(self, queries: SoccerQueries) -> None:
        # Given the module-level cache used by the MCP server
        from brazilian_soccer.graph import load_default_graph

        elapsed, graph = timed(load_default_graph)
        # Then a second request is served from cache, not re-read from disk
        assert elapsed < 0.05
        assert graph is queries.graph
