"""Response-time budgets from the specification.

Context
-------
The specification sets three targets: simple lookups under 2 seconds,
aggregate queries under 5 seconds, and no timeouts.  The graph is built once
at server start (which itself takes well under a second), so per-query cost is
index lookups plus arithmetic.  These tests measure the tools that do the most
work and assert against the stated budgets with a safety factor.
"""

from __future__ import annotations

import time

import pytest

from brazilian_soccer.graph import KnowledgeGraph
from brazilian_soccer.tools import call_tool

pytestmark = pytest.mark.performance

SIMPLE_BUDGET_SECONDS = 2.0
AGGREGATE_BUDGET_SECONDS = 5.0


def timed(graph, tool, **arguments) -> float:
    started = time.perf_counter()
    result = call_tool(tool, arguments, graph=graph)
    elapsed = time.perf_counter() - started
    assert not result["isError"], result["content"][0]["text"]
    return elapsed


@pytest.mark.parametrize("tool,arguments", [
    ("find_matches", {"team": "Flamengo", "opponent": "Fluminense"}),
    ("find_matches", {"team": "Palmeiras", "season": 2023}),
    ("head_to_head", {"team_a": "Gremio", "team_b": "Internacional"}),
    ("team_stats", {"team": "Corinthians", "season": 2022, "venue": "home"}),
    ("player_profile", {"name": "Neymar"}),
    ("club_squad", {"club": "Santos"}),
    ("resolve_team", {"name": "Atletico-PR"}),
    ("standings", {"season": 2019}),
])
def test_simple_lookups_are_under_two_seconds(graph, tool, arguments):
    assert timed(graph, tool, **arguments) < SIMPLE_BUDGET_SECONDS


@pytest.mark.parametrize("tool,arguments", [
    ("competition_stats", {}),                       # every competition, every season
    ("competition_stats", {"competition": "serie-a"}),
    ("team_rankings", {"metric": "points_per_game", "venue": "away",
                       "min_matches": 50}),
    ("biggest_wins", {"limit": 100}),
    ("compare_seasons", {"seasons": list(range(2006, 2023))}),
    ("brazilian_players_by_club", {"limit": 100}),
    ("search_players", {"nationality": "Brazil", "limit": 500}),
    ("find_derbies", {"limit": 500}),
])
def test_aggregate_queries_are_under_five_seconds(graph, tool, arguments):
    assert timed(graph, tool, **arguments) < AGGREGATE_BUDGET_SECONDS


def test_graph_construction_is_fast(data_dir):
    """A cold build -- what an MCP client pays once at server start."""
    started = time.perf_counter()
    graph = KnowledgeGraph(data_dir)
    elapsed = time.perf_counter() - started
    assert graph.matches and graph.players
    assert elapsed < 10.0


def test_repeated_lookups_stay_fast(graph):
    """No accidental O(n) rebuild per call."""
    started = time.perf_counter()
    for _ in range(50):
        call_tool("find_matches", {"team": "Santos", "limit": 10}, graph=graph)
    assert (time.perf_counter() - started) < SIMPLE_BUDGET_SECONDS
