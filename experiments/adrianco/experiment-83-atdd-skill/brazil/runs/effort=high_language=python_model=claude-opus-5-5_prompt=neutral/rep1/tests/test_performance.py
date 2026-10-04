"""Query performance requirements: simple lookups < 2 s, aggregates < 5 s, cold load included."""

import time

from brsoccer import queries as q
from brsoccer.data import SoccerDB


def timed(fn, *args, **kwargs):
    start = time.perf_counter()
    fn(*args, **kwargs)
    return time.perf_counter() - start


def test_cold_load_is_fast():
    assert timed(SoccerDB.load) < 5.0


def test_simple_lookups_under_2s(db):
    for fn, args in [(q.search_matches, {"team": "Flamengo", "opponent": "Fluminense"}),
                     (q.player_profile, {"name": "Neymar"}),
                     (q.team_record, {"team": "Corinthians", "season": 2022}),
                     (q.find_team, {"name": "Sao Paulo"})]:
        assert timed(fn, db=db, **args) < 2.0, fn.__name__


def test_aggregate_queries_under_5s(db):
    for fn, args in [(q.competition_stats, {}),
                     (q.team_rankings, {"metric": "win_rate", "venue": "away", "competition": "all"}),
                     (q.biggest_wins, {}),
                     (q.team_profile, {"team": "Palmeiras"}),
                     (q.brazilian_players_overview, {}),
                     (q.derbies, {}),
                     (q.search_players, {"name": "Silva"})]:
        assert timed(fn, db=db, **args) < 5.0, fn.__name__
