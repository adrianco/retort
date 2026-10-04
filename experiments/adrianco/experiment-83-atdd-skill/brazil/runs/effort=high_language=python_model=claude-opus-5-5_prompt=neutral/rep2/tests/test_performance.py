"""Spec targets: simple lookups < 2 s, aggregate queries < 5 s."""

import time

import pytest

from data_loader import SoccerData
from queries import SoccerQueries


def _timed(fn, *args, **kwargs):
    start = time.perf_counter()
    fn(*args, **kwargs)
    return time.perf_counter() - start


def test_cold_load_is_fast():
    start = time.perf_counter()
    SoccerQueries(SoccerData())
    assert time.perf_counter() - start < 5


@pytest.mark.parametrize("method,kwargs", [
    ("search_matches", {"team": "Flamengo", "opponent": "Corinthians", "limit": 1}),
    ("player_profile", {"name": "Neymar"}),
    ("player_profile", {"name": "Gabriel Barbosa"}),
    ("search_players", {"club": "Santos"}),
    ("team_record", {"team": "Corinthians", "season": 2022, "venue": "home"}),
])
def test_simple_lookups_under_two_seconds(q, method, kwargs):
    assert _timed(getattr(q, method), **kwargs) < 2


@pytest.mark.parametrize("method,kwargs", [
    ("standings", {"season": 2005}),
    ("team_rankings", {"metric": "win_rate", "venue": "away", "competition": None}),
    ("competition_stats", {}),
    ("biggest_wins", {}),
    ("compare_seasons", {"seasons": list(range(2003, 2024))}),
    ("team_overview", {"team": "Santos"}),
    ("player_club_summary", {"nationality": None}),
    ("derby_matches", {}),
])
def test_aggregate_queries_under_five_seconds(method, kwargs):
    fresh = SoccerQueries()  # no warm standings cache
    assert _timed(getattr(fresh, method), **kwargs) < 5
