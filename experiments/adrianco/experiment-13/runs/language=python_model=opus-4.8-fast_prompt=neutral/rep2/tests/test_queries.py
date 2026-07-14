"""
Context
=======
Tests for bsoccer.queries.QueryEngine: exercises every required capability
category (matches, teams, players, competitions, statistics) and validates a
known-truth anchor — the 2019 Brasileirão final table — against the figures
published in the spec (Flamengo champions on 90 points, 28W-6D-4L).
"""

import pytest

from bsoccer.data import get_data
from bsoccer.queries import QueryEngine


@pytest.fixture(scope="module")
def eng():
    return QueryEngine(get_data())


# ----- team resolution ----------------------------------------------------

def test_resolve_team_variations(eng):
    assert eng.resolve_team_key("Flamengo") == eng.resolve_team_key("Flamengo-RJ")
    assert eng.resolve_team_key("São Paulo") == eng.resolve_team_key("Sao Paulo")
    assert eng.resolve_team_key("Definitely Not A Team XYZ") is None


# ----- 1. match queries ---------------------------------------------------

def test_find_matches_between_two_teams(eng):
    res = eng.find_matches(team="Flamengo", opponent="Fluminense")
    assert res["count"] > 0
    for m in res["matches"]:
        teams = {m["home_team"], m["away_team"]}
        assert any("Flamengo" in t for t in teams)
        assert any("Fluminense" in t for t in teams)


def test_find_matches_by_season_and_competition(eng):
    res = eng.find_matches(team="Palmeiras", competition="Brasileirão", season=2019)
    assert res["count"] > 0
    for m in res["matches"]:
        assert m["season"] == 2019
        assert m["competition"] == "Brasileirão"


def test_find_matches_unknown_team(eng):
    res = eng.find_matches(team="Nonexistent FC")
    assert res["count"] == 0
    assert "error" in res


def test_find_matches_limit(eng):
    res = eng.find_matches(team="Flamengo", limit=5)
    assert res["returned"] <= 5


# ----- 2. team queries ----------------------------------------------------

def test_team_record_home(eng):
    rec = eng.team_record("Corinthians", competition="Brasileirão",
                          season=2022, venue="home")
    assert rec["matches"] == rec["wins"] + rec["draws"] + rec["losses"]
    assert rec["points"] == rec["wins"] * 3 + rec["draws"]
    assert 0 <= rec["win_rate"] <= 100


def test_head_to_head_symmetry(eng):
    h = eng.head_to_head("Palmeiras", "Santos")
    assert h["total_matches"] == h["team_a_wins"] + h["team_b_wins"] + h["draws"]
    assert h["total_matches"] > 0


def test_head_to_head_unknown(eng):
    h = eng.head_to_head("Palmeiras", "Nope United")
    assert "error" in h


# ----- 3. player queries --------------------------------------------------

def test_search_players_by_name(eng):
    res = eng.search_players(name="Neymar")
    assert res["count"] >= 1
    assert any("Neymar" in p["name"] for p in res["players"])


def test_search_brazilian_players_sorted(eng):
    res = eng.search_players(nationality="Brazil", min_overall=85)
    assert res["count"] > 0
    overalls = [p["overall"] for p in res["players"]]
    assert overalls == sorted(overalls, reverse=True)
    for p in res["players"]:
        assert p["nationality"] == "Brazil"
        assert p["overall"] >= 85


def test_search_players_by_position(eng):
    res = eng.search_players(nationality="Brazil", position="GK", limit=5)
    for p in res["players"]:
        assert p["position"] == "GK"


def test_players_by_club_summary(eng):
    res = eng.players_by_club_summary("Brazil", top=5)
    assert res["total_players"] > 0
    assert len(res["clubs"]) <= 5
    assert all(c["players"] > 0 for c in res["clubs"])


# ----- 4. competition queries: 2019 Brasileirão known-truth anchor --------

def test_2019_brasileirao_champion(eng):
    champ = eng.champion("Brasileirão", 2019)
    assert champ["champion"] == "Flamengo"
    assert champ["points"] == 90
    assert champ["record"] == "28W-6D-4L"


def test_2019_standings_top_three(eng):
    table = eng.standings("Brasileirão", 2019)["table"]
    assert table[0]["team"] == "Flamengo"
    assert table[0]["points"] == 90
    # 20-team league.
    assert len([t for t in table]) == 20
    # Table is sorted by points descending.
    pts = [t["points"] for t in table]
    assert pts == sorted(pts, reverse=True)


def test_standings_unknown_season(eng):
    res = eng.standings("Brasileirão", 1800)
    assert res.get("error") or res["table"] == []


def test_list_seasons(eng):
    res = eng.seasons_available("Brasileirão")
    assert 2019 in res["seasons"]
    assert "Brasileirão" in res["competitions"]


# ----- 5. statistics ------------------------------------------------------

def test_competition_stats(eng):
    s = eng.competition_stats("Brasileirão", 2019)
    assert s["matches"] == 380
    assert s["home_wins"] + s["away_wins"] + s["draws"] == 380
    assert 0 < s["avg_goals_per_match"] < 10
    assert abs(s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"] - 100) < 0.5


def test_biggest_wins(eng):
    res = eng.biggest_wins("Brasileirão", limit=5)
    margins = [m["margin"] for m in res["matches"]]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 5


def test_top_scoring_teams(eng):
    res = eng.top_scoring_teams("Brasileirão", 2019, limit=5)
    goals = [t["goals_for"] for t in res["teams"]]
    assert goals == sorted(goals, reverse=True)
    # Flamengo were the top scorers in 2019.
    assert res["teams"][0]["team"] == "Flamengo"


# ----- performance --------------------------------------------------------

def test_query_performance(eng):
    import time
    t = time.time()
    eng.standings("Brasileirão", 2019)
    assert time.time() - t < 5.0
