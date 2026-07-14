"""
=============================================================================
 Brazilian Soccer MCP Server -- Test Suite
=============================================================================
 Purpose
 -------
 Demonstrates that the implementation meets the specification. Tests are
 grouped to mirror the spec's required capabilities:

   * Data loading & coverage (all 6 CSV files)
   * Name / date normalization (the documented data-quality cases)
   * Match queries        (find, last, head-to-head)
   * Team queries         (records, comparisons)
   * Player queries       (search, by club, by nationality, top)
   * Competition queries  (standings computed from results)
   * Statistical analysis (averages, biggest wins, best records)
   * Performance budgets   (simple < 2s, aggregate < 5s)
   * 20+ sample questions  (parametrized end-to-end smoke test)
   * MCP server wiring     (tools registered & callable)

 Many assertions are anchored to historically verifiable facts (e.g. Flamengo
 won the 2019 Brasileirão with 90 points) so the tests double as a
 correctness check on the data pipeline, not just a smoke test.

 Run with:  pytest -q
=============================================================================
"""

from __future__ import annotations

import time

import pytest

from soccer_data import (
    SoccerDatabase,
    canonical_key,
    normalize_team_name,
    parse_date,
    split_team,
    team_matches,
)
from soccer_queries import SoccerQueryEngine


# --------------------------------------------------------------------------
# Shared fixtures (load the data once for the whole session -- it's not cheap)
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db() -> SoccerDatabase:
    return SoccerDatabase.load()


@pytest.fixture(scope="session")
def engine(db) -> SoccerQueryEngine:
    return SoccerQueryEngine(db)


# ==========================================================================
# Data loading & coverage
# ==========================================================================


def test_all_six_files_loaded(db):
    sources = {m.source for m in db.matches}
    assert sources == {
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
    }
    # the 6th file is the player database
    assert len(db.players) > 18000


def test_expected_competitions_present(db):
    comps = set(db.competitions())
    for needed in ("Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"):
        assert needed in comps


def test_season_range(db):
    seasons = db.seasons()
    assert min(seasons) <= 2003
    assert max(seasons) >= 2023


def test_no_match_loses_both_teams(db):
    # Every loaded match should at least have two non-empty team names.
    assert all(m.home_team and m.away_team for m in db.matches)


# ==========================================================================
# Normalization (the documented data-quality cases)
# ==========================================================================


@pytest.mark.parametrize(
    "raw,expected_display",
    [
        ("Palmeiras-SP", "Palmeiras"),
        ("Flamengo-RJ", "Flamengo"),
        ("São Paulo-SP", "São Paulo"),
        ("Atlético-MG", "Atlético-MG"),      # ambiguous base keeps its state
        ("Atletico Mineiro", "Atlético-MG"),  # full name resolves to same club
        ("Nacional (URU)", "Nacional-URU"),   # ambiguous base disambiguated by country
    ],
)
def test_team_display_normalization(raw, expected_display):
    assert normalize_team_name(raw) == expected_display


@pytest.mark.parametrize(
    "a,b",
    [
        ("Palmeiras-SP", "Palmeiras"),
        ("São Paulo", "Sao Paulo"),
        ("Vasco da Gama", "Vasco"),
        ("Atlético-MG", "Atletico Mineiro"),
        ("Atlético-PR", "Athletico Paranaense"),
        ("Grêmio", "Gremio"),
    ],
)
def test_same_club_same_canonical_key(a, b):
    assert canonical_key(a) == canonical_key(b)


@pytest.mark.parametrize(
    "a,b",
    [
        ("Grêmio", "Grêmio Prudente"),     # different clubs sharing a word
        ("Atlético-MG", "Atlético-PR"),    # the three Atléticos stay distinct
        ("Atlético-MG", "Atlético-GO"),
        ("América-MG", "América-RN"),
    ],
)
def test_distinct_clubs_distinct_keys(a, b):
    assert canonical_key(a) != canonical_key(b)


def test_split_team_extracts_state():
    assert split_team("Palmeiras-SP") == ("Palmeiras", "SP")
    assert split_team("América - MG") == ("América", "MG")
    assert split_team("Nacional (URU)") == ("Nacional", "URU")
    assert split_team("Flamengo")[1] == ""


def test_team_matches_is_fuzzy():
    assert team_matches("flamengo", "Flamengo-RJ")
    assert team_matches("Sao Paulo", "São Paulo")
    assert team_matches("vasco", "Vasco da Gama")
    assert not team_matches("Flamengo", "Fluminense")


@pytest.mark.parametrize(
    "raw,iso",
    [
        ("2023-09-24", "2023-09-24"),
        ("2012-05-19 18:30:00", "2012-05-19"),
        ("29/03/2003", "2003-03-29"),
    ],
)
def test_date_parsing_multiple_formats(raw, iso):
    assert parse_date(raw).isoformat() == iso


def test_date_parsing_handles_garbage():
    assert parse_date("") is None
    assert parse_date("not-a-date") is None


# ==========================================================================
# Match queries
# ==========================================================================


def test_find_matches_by_team(engine):
    res = engine.find_matches(team="Flamengo")
    assert res["count"] > 100
    assert all(
        team_matches("Flamengo", m["home_team"]) or team_matches("Flamengo", m["away_team"])
        for m in res["matches"]
    )


def test_find_matches_by_team_and_season(engine):
    res = engine.find_matches(team="Palmeiras", season=2019, competition="Brasileirão")
    assert res["count"] == 38  # full league season
    assert all(m["season"] == 2019 for m in res["matches"])


def test_find_matches_between_two_teams(engine):
    res = engine.find_matches(
        team="Flamengo", opponent="Fluminense", competition="Brasileirão", season=2019
    )
    assert res["count"] == 2  # one home, one away in a league season
    for m in res["matches"]:
        assert team_matches("Flamengo", m["home_team"]) or team_matches(
            "Flamengo", m["away_team"]
        )
        assert team_matches("Fluminense", m["home_team"]) or team_matches(
            "Fluminense", m["away_team"]
        )


def test_find_matches_date_range(engine):
    res = engine.find_matches(date_from="2019-01-01", date_to="2019-12-31")
    assert res["count"] > 0
    assert all("2019" in (m["date"] or "") for m in res["matches"])


def test_last_match(engine):
    res = engine.last_match("Flamengo", "Corinthians")
    assert res["found"]
    assert team_matches("Flamengo", res["match"]["home_team"]) or team_matches(
        "Flamengo", res["match"]["away_team"]
    )


def test_head_to_head_consistency(engine):
    h = engine.head_to_head("Flamengo", "Fluminense")
    a = h["Flamengo_wins"]
    b = h["Fluminense_wins"]
    d = h["draws"]
    # wins + draws must reconcile with the number of *scored* matches
    scored = sum(
        1 for m in h["matches"] if m["home_goal"] is not None and m["away_goal"] is not None
    )
    assert a + b + d == scored
    assert h["total_matches"] >= scored


# ==========================================================================
# Team queries
# ==========================================================================


def test_corinthians_home_record_brasileirao(engine):
    # Spec example. (Uses 2021 -- the 2022 season is only partially present in
    # the provided CSV, so it isn't a complete 19-home-game season.)
    rec = engine.team_record(
        "Corinthians", season=2021, competition="Brasileirão", venue="home"
    )
    # A Série A team plays 19 home league games in a 20-team season.
    assert rec["played"] == 19
    assert rec["wins"] + rec["draws"] + rec["losses"] == 19
    assert rec["points"] == rec["wins"] * 3 + rec["draws"]


def test_team_record_venue_split_adds_up(engine):
    allr = engine.team_record("Palmeiras", season=2019, competition="Brasileirão")
    home = engine.team_record(
        "Palmeiras", season=2019, competition="Brasileirão", venue="home"
    )
    away = engine.team_record(
        "Palmeiras", season=2019, competition="Brasileirão", venue="away"
    )
    assert home["played"] + away["played"] == allr["played"] == 38
    assert home["wins"] + away["wins"] == allr["wins"]
    assert home["goals_for"] + away["goals_for"] == allr["goals_for"]


def test_compare_teams(engine):
    cmp = engine.compare_teams("Palmeiras", "Santos")
    assert cmp["team_a_record"]["played"] > 0
    assert cmp["team_b_record"]["played"] > 0
    assert cmp["head_to_head"]["total_matches"] > 0


# ==========================================================================
# Player queries
# ==========================================================================


def test_search_players_by_name(engine):
    res = engine.search_players("Neymar")
    assert res["count"] >= 1
    top = res["players"][0]
    assert top["nationality"] == "Brazil"
    assert top["overall"] >= 90


def test_players_by_nationality_brazil(engine):
    res = engine.players_by_nationality("Brazil")
    assert res["count"] > 500
    assert all(p["nationality"] == "Brazil" for p in res["players"])
    # returned list is sorted by overall descending
    overalls = [p["overall"] for p in res["players"]]
    assert overalls == sorted(overalls, reverse=True)


def test_players_by_club(engine):
    res = engine.players_by_club("Santos")
    assert res["count"] > 0
    assert all("santos" in p["club"].lower() for p in res["players"])
    assert res["avg_overall"] > 0


def test_top_brazilian_players(engine):
    res = engine.top_players(nationality="Brazil", limit=5)
    names = [p["name"] for p in res["players"]]
    assert "Neymar Jr" in names
    overalls = [p["overall"] for p in res["players"]]
    assert overalls == sorted(overalls, reverse=True)


def test_top_players_by_position(engine):
    res = engine.top_players(nationality="Brazil", position="GK", limit=5)
    assert res["count"] >= 1
    assert all("GK" in p["position"] for p in res["players"])


# ==========================================================================
# Competition queries -- standings computed from match results
# ==========================================================================


def test_2019_brasileirao_champion_is_flamengo(engine):
    """The spec's worked example: 2019 Brasileirão, Flamengo 90 pts."""
    st = engine.standings(2019, competition="Brasileirão Série A")
    assert st["teams"] == 20
    champ = st["standings"][0]
    assert champ["team"] == "Flamengo"
    assert champ["points"] == 90
    assert (champ["wins"], champ["draws"], champ["losses"]) == (28, 6, 4)
    assert champ["played"] == 38


@pytest.mark.parametrize(
    "season,champion,points",
    [
        (2009, "Flamengo", 67),
        (2017, "Corinthians", 72),
        (2018, "Palmeiras", 80),
        (2019, "Flamengo", 90),
        (2020, "Flamengo", 71),
        (2021, "Atlético-MG", 84),
    ],
)
def test_known_brasileirao_champions(engine, season, champion, points):
    st = engine.standings(season)
    assert st["champion"] == champion
    assert st["standings"][0]["points"] == points


def test_standings_are_internally_consistent(engine):
    st = engine.standings(2015)
    for row in st["standings"]:
        assert row["played"] == row["wins"] + row["draws"] + row["losses"]
        assert row["points"] == row["wins"] * 3 + row["draws"]
        assert row["goal_difference"] == row["goals_for"] - row["goals_against"]
    # sorted by points descending
    pts = [r["points"] for r in st["standings"]]
    assert pts == sorted(pts, reverse=True)


def test_list_seasons_and_competitions(engine):
    comps = engine.list_competitions()["competitions"]
    assert "Copa Libertadores" in comps
    seasons = engine.list_seasons(competition="Brasileirão")["seasons"]
    assert 2019 in seasons


# ==========================================================================
# Statistical analysis
# ==========================================================================


def test_competition_stats_brasileirao(engine):
    stats = engine.competition_stats(competition="Brasileirão")
    assert stats["matches"] > 1000
    assert 2.0 < stats["avg_goals_per_match"] < 3.5
    # rates should sum to ~100%
    total = (
        stats["home_win_rate_pct"] + stats["away_win_rate_pct"] + stats["draw_rate_pct"]
    )
    assert abs(total - 100.0) < 0.5
    # home advantage is real
    assert stats["home_win_rate_pct"] > stats["away_win_rate_pct"]


def test_biggest_wins_sorted_by_margin(engine):
    res = engine.biggest_wins(competition="Libertadores", limit=10)
    margins = [m["margin"] for m in res["matches"]]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 6


def test_best_home_record(engine):
    res = engine.best_record(
        venue="home", competition="Brasileirão", season=2019, min_games=10, limit=5
    )
    # Flamengo had a dominant home season in 2019.
    assert res["teams"][0]["team"] == "Flamengo"
    assert res["teams"][0]["win_rate_pct"] > 80


def test_best_record_respects_min_games(engine):
    res = engine.best_record(venue="all", season=2019, min_games=30)
    assert all(t["played"] >= 30 for t in res["teams"])


# ==========================================================================
# Performance budgets
# ==========================================================================


def test_simple_lookup_under_2s(engine):
    t = time.time()
    engine.last_match("Flamengo", "Corinthians")
    engine.search_players("Coutinho")
    assert time.time() - t < 2.0


def test_aggregate_query_under_5s(engine):
    t = time.time()
    engine.standings(2019)
    engine.best_record(venue="away", competition="Brasileirão")
    engine.competition_stats()
    assert time.time() - t < 5.0


# ==========================================================================
# 20+ sample questions -- end-to-end smoke test
# ==========================================================================

# Each entry: (description, callable -> result, predicate(result) -> bool)
SAMPLE_QUESTIONS = [
    ("All Flamengo vs Fluminense matches",
     lambda e: e.find_matches(team="Flamengo", opponent="Fluminense"),
     lambda r: r["count"] > 10),
    ("What matches did Palmeiras play in 2019?",
     lambda e: e.find_matches(team="Palmeiras", season=2019, competition="Brasileirão"),
     lambda r: r["count"] == 38),
    ("Find Copa do Brasil matches",
     lambda e: e.find_matches(competition="Copa do Brasil"),
     lambda r: r["count"] > 100),
    ("Corinthians home record in 2021 Brasileirão",
     lambda e: e.team_record("Corinthians", season=2021, competition="Brasileirão", venue="home"),
     lambda r: r["played"] == 19),
    ("Which team scored most goals in Serie A 2019?",
     lambda e: e.standings(2019),
     lambda r: max(r["standings"], key=lambda x: x["goals_for"])["goals_for"] > 50),
    ("Compare Palmeiras and Santos head-to-head",
     lambda e: e.head_to_head("Palmeiras", "Santos"),
     lambda r: r["total_matches"] > 0),
    ("Find all Brazilian players",
     lambda e: e.players_by_nationality("Brazil"),
     lambda r: r["count"] > 500),
    ("Highest-rated players at Santos",
     lambda e: e.players_by_club("Santos"),
     lambda r: r["count"] > 0),
    ("Top Brazilian players",
     lambda e: e.top_players(nationality="Brazil", limit=10),
     lambda r: r["players"][0]["name"] == "Neymar Jr"),
    ("Who won the 2019 Brasileirão?",
     lambda e: e.standings(2019),
     lambda r: r["champion"] == "Flamengo"),
    ("Who won the 2018 Brasileirão?",
     lambda e: e.standings(2018),
     lambda r: r["champion"] == "Palmeiras"),
    ("Average goals per match in the Brasileirão",
     lambda e: e.competition_stats(competition="Brasileirão"),
     lambda r: 2.0 < r["avg_goals_per_match"] < 3.5),
    ("Which team has the best home record (2019)?",
     lambda e: e.best_record(venue="home", competition="Brasileirão", season=2019, min_games=10),
     lambda r: r["teams"][0]["team"] == "Flamengo"),
    ("Biggest wins in the Libertadores",
     lambda e: e.biggest_wins(competition="Libertadores"),
     lambda r: r["matches"][0]["margin"] >= 6),
    ("When did Flamengo last play Corinthians?",
     lambda e: e.last_match("Flamengo", "Corinthians"),
     lambda r: r["found"]),
    ("Who is Neymar?",
     lambda e: e.search_players("Neymar"),
     lambda r: r["count"] >= 1),
    ("Which players play for Cruzeiro?",
     lambda e: e.players_by_club("Cruzeiro"),
     lambda r: r["count"] >= 0),
    ("What competitions has Palmeiras played in?",
     lambda e: {c: e.find_matches(team="Palmeiras", competition=c)["count"]
                for c in ["Brasileirão", "Copa do Brasil", "Libertadores"]},
     lambda r: sum(r.values()) > 0),
    ("Compare the 2018 and 2019 seasons",
     lambda e: (e.competition_stats(competition="Brasileirão", season=2018),
                e.competition_stats(competition="Brasileirão", season=2019)),
     lambda r: r[0]["matches"] > 0 and r[1]["matches"] > 0),
    ("Show the 2018 Libertadores knockout matches",
     lambda e: e.find_matches(competition="Libertadores", season=2018),
     lambda r: r["count"] > 0),
    ("Forwards from Brazil (top GKs as a position filter)",
     lambda e: e.top_players(nationality="Brazil", position="ST", limit=5),
     lambda r: r["count"] >= 1),
    ("Database overview",
     lambda e: e.database_summary(),
     lambda r: r["total_matches"] > 15000 and r["total_players"] > 18000),
]


@pytest.mark.parametrize(
    "desc,query,check", SAMPLE_QUESTIONS, ids=[q[0] for q in SAMPLE_QUESTIONS]
)
def test_sample_questions(engine, desc, query, check):
    result = query(engine)
    assert check(result), f"Sample question failed: {desc} -> {result}"


def test_at_least_20_sample_questions():
    assert len(SAMPLE_QUESTIONS) >= 20


# ==========================================================================
# MCP server wiring
# ==========================================================================


def test_mcp_server_imports_and_registers_tools():
    import asyncio

    import server

    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "find_matches", "last_match", "head_to_head",
        "team_record", "compare_teams",
        "search_players", "players_by_club", "players_by_nationality", "top_players",
        "standings", "list_competitions", "list_seasons",
        "competition_stats", "biggest_wins", "best_record", "database_summary",
    }
    assert expected <= names


def test_mcp_tool_callable_end_to_end():
    import server

    out = server.standings(2019)
    assert out["champion"] == "Flamengo"
