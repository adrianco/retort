import json
import subprocess
import sys
import time

import pytest

import server
from soccer_data import display_team, get_db, normalize_team, parse_date


@pytest.fixture(scope="module")
def db():
    return get_db()


# ---------------- normalization / parsing
@pytest.mark.parametrize("raw,key", [
    ("Palmeiras-SP", "palmeiras"), ("Palmeiras", "palmeiras"), ("São Paulo - SP", "sao paulo"),
    ("Sao Paulo", "sao paulo"), ("Sport Club Corinthians Paulista", "corinthians"),
    ("Grêmio", "gremio"), ("Gremio-RS", "gremio"), ("Atletico-MG", "atletico-mg"),
    ("Atlético Mineiro", "atletico-mg"), ("Athletico-PR", "atletico-pr"),
    ("Athletico Paranaense", "atletico-pr"), ("Atlético - PR", "atletico-pr"),
    ("Atletico Goianiense", "atletico-go"), ("Botafogo RJ", "botafogo-rj"), ("Botafogo", "botafogo-rj"),
    ("Botafogo SP", "botafogo-sp"), ("Vasco Da Gama RJ", "vasco"), ("Vasco", "vasco"),
    ("América FC (Minas Gerais)", "america-mg"), ("America MG", "america-mg"),
    ("Red Bull Bragantino-SP", "bragantino"), ("EC Bahia", "bahia"), ("Fortaleza FC", "fortaleza"),
    ("Barcelona-EQU", "barcelona-equ"),
])
def test_normalize_team(raw, key):
    assert normalize_team(raw) == key


def test_display():
    assert display_team("sao paulo") == "São Paulo"
    assert display_team("colo-colo") == "Colo-colo"


@pytest.mark.parametrize("s,iso", [("2023-09-24", "2023-09-24"), ("29/03/2003", "2003-03-29"),
                                   ("2012-05-19 18:30:00", "2012-05-19")])
def test_parse_date(s, iso):
    assert parse_date(s).isoformat() == iso


# ---------------- data coverage
def test_all_files_loaded(db):
    expected = {"Brasileirao_Matches.csv": 4000, "Brazilian_Cup_Matches.csv": 1300,
                "Libertadores_Matches.csv": 1250, "BR-Football-Dataset.csv": 10000,
                "novo_campeonato_brasileiro.csv": 6800}
    for f, n in expected.items():
        assert len(db.by_source[f]) >= n
    assert len(db.players) == 18207


def test_utf8(db):
    assert any(m.extra.get("arena") == "Maracanã" for m in db.by_source["novo_campeonato_brasileiro.csv"])


def test_dedup_overlapping_sources(db):
    r = db.team_record("Corinthians", 2022, "Brasileirão", "home")
    assert r["matches"] == 19


# ---------------- 20+ sample questions via MCP tools
def test_q01_fla_flu():
    out = server.search_matches("Flamengo", "Fluminense")
    assert "Head-to-head" in out and "Flamengo" in out and "Fluminense" in out


def test_q02_palmeiras_2023(db):
    ms = db.find_matches("Palmeiras", season=2023)
    assert len(ms) >= 38 and all(m.involves("palmeiras") for m in ms)


def test_q03_copa_finals():
    out = server.cup_finals("Copa do Brasil")
    assert "2015" in out and "Santos" in out


def test_q04_corinthians_home():
    out = server.team_record("Corinthians", 2022, "Brasileirão", "home")
    assert "Matches: 19" in out and "Win rate" in out


def test_q05_most_goals_2023():
    assert "1. " in server.top_scoring_teams(2023)


def test_q06_h2h(db):
    h = db.head_to_head("Palmeiras", "Santos")
    assert h["a_wins"] + h["b_wins"] + h["draws"] == len(h["matches"]) > 20


def test_q07_brazilian_players():
    out = server.search_players(nationality="Brazilian", limit=3)
    assert out.splitlines()[1].startswith("1. Neymar Jr - Overall: 92")


def test_q08_club_players_empty_note():
    assert "Flamengo" in server.search_players(club="Flamengo")


def test_q09_forwards(db):
    ps = db.search_players(club="Atletico Mineiro", position="forward", limit=None)
    assert ps and all(p["Position"] in {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"} for p in ps)


def test_q10_champion_2019(db):
    t = db.standings(2019)
    assert (t[0]["team"], t[0]["points"], t[0]["wins"]) == ("Flamengo", 90, 28)
    assert "Flamengo won" in server.champion(2019)


def test_q11_libertadores_bracket():
    out = server.bracket(2018, "Libertadores")
    assert "Final" in out and "River Plate" in out


def test_q12_relegated_2020():
    out = server.relegated(2020)
    assert "Botafogo" in out and "Coritiba" in out


def test_q13_avg_goals(db):
    s = db.stats("Brasileirão")
    assert 2.0 < s["avg_goals"] < 3.0


def test_q14_best_away():
    assert "1. " in server.best_records("away")


def test_q15_biggest_wins(db):
    ms = db.biggest_wins(limit=5)
    margins = [abs(m.home_goal - m.away_goal) for m in ms]
    assert margins == sorted(margins, reverse=True) and margins[0] >= 7


def test_q16_last_flamengo_corinthians():
    out = server.last_match("Flamengo", "Corinthians")
    assert out.startswith("Most recent match:") and "Corinthians" in out


def test_q17_player_lookup():
    assert "Neymar" in server.search_players(name="neymar")


def test_q18_derbies_2023():
    out = server.derbies(2023)
    assert "Fla-Flu" in out


def test_q19_palmeiras_competitions(db):
    c = db.competitions_for_team("Palmeiras")
    assert {"Brasileirão", "Copa do Brasil", "Libertadores"} <= set(c)


def test_q20_best_home_record():
    assert "%" in server.best_records("home")


def test_q21_compare_seasons():
    out = server.compare_seasons(2018, 2019)
    assert "2018" in out and "2019" in out and "Flamengo" in out


def test_q22_cross_file_profile():
    out = server.team_profile("Grêmio")
    assert "FIFA squad" in out and "Libertadores" in out


def test_q23_date_range(db):
    ms = db.find_matches("Santos", date_from="01/01/2019", date_to="2019-12-31")
    assert ms and all(m.date.year == 2019 for m in ms)


def test_q24_extended_stats_serie_b(db):
    assert db.find_matches(competition="Serie B", season=2022)


def test_q25_historical_2003(db):
    assert db.standings(2003)[0]["team"] == "Cruzeiro"


# ---------------- performance
def test_performance():
    t = time.time()
    server.search_players(name="Gabriel")
    server.last_match("Flamengo")
    assert time.time() - t < 2
    t = time.time()
    server.best_records("away")
    server.standings(2019)
    server.biggest_wins()
    assert time.time() - t < 5


# ---------------- MCP protocol over stdio
def test_mcp_stdio():
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "champion", "arguments": {"season": 2019}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 5, "method": "bogus"},
    ]
    p = subprocess.run([sys.executable, "server.py"], input="\n".join(map(json.dumps, msgs)) + "\n",
                       capture_output=True, text=True, timeout=60)
    resp = {r["id"]: r for r in map(json.loads, p.stdout.splitlines())}
    assert resp[1]["result"]["serverInfo"]["name"] == "brazilian-soccer"
    assert len(resp[2]["result"]["tools"]) >= 15
    assert "Flamengo" in resp[3]["result"]["content"][0]["text"]
    assert resp[4]["result"]["isError"] is True
    assert resp[5]["error"]["code"] == -32601
    assert len(resp) == 5
