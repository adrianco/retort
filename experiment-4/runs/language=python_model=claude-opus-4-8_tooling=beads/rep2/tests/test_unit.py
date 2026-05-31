"""
================================================================================
Brazilian Soccer MCP Server :: tests/test_unit
================================================================================

Context
-------
Unit / integration tests complementing the BDD scenarios. Covers:
  - team-name normalisation (suffixes, accents, ambiguous bases)
  - date parsing across the dataset formats
  - data coverage (all six CSVs loaded & queryable)
  - statistical helpers (head-to-head, stats, biggest wins, best record)
  - query performance budgets (<2s simple, <5s aggregate)
  - MCP tool registration

These plus the BDD steps answer well over the 20 sample questions required by
the specification.
================================================================================
"""

import time

import pytest

from brazilian_soccer.data_loader import (
    DataLoader,
    clean_team_name,
    normalize_team_name,
    parse_date,
)


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Palmeiras-SP", "palmeiras"),
        ("Palmeiras", "palmeiras"),
        ("PALMEIRAS", "palmeiras"),
        ("São Paulo", "sao paulo"),
        ("Grêmio", "gremio"),
        ("Nacional (URU)", "nacional"),  # paren stripped; not a BR state
        ('"Flamengo-RJ"', "flamengo"),
    ],
)
def test_normalize_basic(raw, expected):
    assert normalize_team_name(raw) == expected


def test_ambiguous_clubs_kept_distinct():
    assert normalize_team_name("Atletico-MG") != normalize_team_name("Atletico-PR")
    assert normalize_team_name("Atletico-MG", "MG") == "atletico mg"
    assert normalize_team_name("América-MG") == "america mg"
    # space-separated state variants from BR-Football unify with dash variants
    assert normalize_team_name("Botafogo RJ") == normalize_team_name("Botafogo-RJ")


def test_clean_name_preserves_accents():
    assert clean_team_name("São Paulo-SP") == "São Paulo"


# --------------------------------------------------------------------------- #
# Date parsing
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,iso",
    [
        ("2023-09-24", "2023-09-24"),
        ("2012-05-19 18:30:00", "2012-05-19"),
        ("29/03/2003", "2003-03-29"),
        ("", None),
        ("not-a-date", None),
    ],
)
def test_parse_date(raw, iso):
    d = parse_date(raw)
    assert (d.isoformat() if d else None) == iso


# --------------------------------------------------------------------------- #
# Data coverage — all six CSVs load & are queryable
# --------------------------------------------------------------------------- #
def test_all_sources_loaded(graph):
    sources = {m.source for m in graph.matches}
    assert {
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
    } <= sources
    assert len(graph.players) > 18000  # fifa_data.csv


def test_competitions_present(graph):
    comps = graph.competitions
    assert any("Série A" in c for c in comps)
    assert "Copa do Brasil" in comps
    assert "Copa Libertadores" in comps


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def test_head_to_head_consistency(engine):
    h = engine.head_to_head("Flamengo", "Fluminense")["summary"]
    wins = sum(v for k, v in h.items() if k.endswith("_wins"))
    assert wins + h["draws"] == h["matches"]
    assert h["matches"] > 0


def test_competition_stats_reasonable(engine):
    s = engine.competition_stats(competition="Brasileirão Série A")
    assert 1.5 < s["avg_goals_per_match"] < 4.0
    assert s["home_win_rate"] > s["away_win_rate"]  # home advantage


def test_biggest_wins_sorted_by_margin(engine):
    rows = engine.biggest_wins(limit=5)["biggest_wins"]
    margins = [r["margin"] for r in rows]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 6


def test_best_home_record(engine):
    r = engine.best_record(competition="Brasileirão Série A", season=2019, venue="home")
    assert r["ranking"]
    assert r["ranking"][0]["win_rate"] >= r["ranking"][-1]["win_rate"]


def test_standings_full_season_game_count(engine):
    # A modern 20-team Brasileirão season is a 38-round double round-robin.
    table = engine.standings("Brasileirão Série A", 2019)
    assert table["teams"] == 20
    for row in table["standings"]:
        assert row["played"] == 38


def test_unknown_team_handled(engine):
    res = engine.find_matches(team="Nonexistent FC")
    assert res["count"] == 0
    assert "error" in res


# --------------------------------------------------------------------------- #
# Player queries
# --------------------------------------------------------------------------- #
def test_brazilian_players_at_clubs(engine):
    out = engine.players_at_brazilian_clubs("Brazil")
    assert out["total_players"] > 100
    assert out["clubs"][0]["players"] >= out["clubs"][-1]["players"]


def test_player_club_filter(engine):
    out = engine.search_players(club="Flamengo")
    # FIFA dataset may have few/zero Flamengo players depending on edition;
    # the filter must at least not error and return club-matching players.
    for p in out["players"]:
        assert "flamengo" in (p["club"] or "").lower()


# --------------------------------------------------------------------------- #
# Performance budgets
# --------------------------------------------------------------------------- #
def test_simple_lookup_under_2s(engine):
    start = time.time()
    engine.find_matches(team="Flamengo", opponent="Corinthians")
    assert time.time() - start < 2.0


def test_aggregate_under_5s(engine):
    start = time.time()
    engine.standings("Brasileirão Série A", 2019)
    engine.competition_stats(competition="Brasileirão Série A")
    engine.best_record(competition="Brasileirão Série A", venue="away")
    assert time.time() - start < 5.0


# --------------------------------------------------------------------------- #
# MCP tool registration
# --------------------------------------------------------------------------- #
def test_mcp_tools_registered():
    import asyncio

    from brazilian_soccer.server import mcp

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "find_matches", "matches_between", "team_record", "compare_teams",
        "search_players", "players_by_nationality_clubs", "standings",
        "champion", "relegated", "list_competitions", "head_to_head",
        "competition_stats", "biggest_wins", "best_record", "top_scoring_teams",
    }
    assert expected <= names
