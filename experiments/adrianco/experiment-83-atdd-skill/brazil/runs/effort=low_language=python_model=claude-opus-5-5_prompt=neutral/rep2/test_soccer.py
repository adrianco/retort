import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

import server
import soccer
from soccer import normalize_team, parse_date

HERE = Path(__file__).parent


@pytest.fixture(scope="session", autouse=True)
def kb():
    return soccer.KB.get()


# ---- normalization ----
@pytest.mark.parametrize("raw,key", [
    ("Palmeiras-SP", "palmeiras"), ("Palmeiras", "palmeiras"), ("São Paulo", "sao paulo"),
    ("Sao Paulo-SP", "sao paulo"), ("Grêmio", "gremio"), ("Gremio RS", "gremio"),
    ("Athletico-PR", "atletico-pr"), ("Atletico Paranaense", "atletico-pr"), ("Atlético - PR", "atletico-pr"),
    ("Atletico-MG", "atletico-mg"), ("Atletico Mineiro", "atletico-mg"),
    ("Vasco da Gama-RJ", "vasco"), ("Vasco Da Gama RJ", "vasco"), ("Red Bull Bragantino", "bragantino"),
    ("Sport Club Corinthians Paulista", "corinthians"), ("América - MG", "america"), ("América - RN", "america-rn"),
    ("Fluminense PI", "fluminense-pi"), ("Avaí - SC", "avai"),
])
def test_normalize_team(raw, key):
    assert normalize_team(raw) == key


def test_parse_dates():
    assert str(parse_date("29/03/2003")) == "2003-03-29"
    assert str(parse_date("2012-05-19 18:30:00")) == "2012-05-19"
    assert str(parse_date("2023-09-24")) == "2023-09-24"


def test_all_files_loaded(kb):
    assert set(kb.sources) == {"brasileirao", "cup", "libertadores", "extended", "historical"}
    assert len(kb.sources["historical"]) == 6886
    assert len(kb.sources["extended"]) > 10000
    assert len(kb.players) == 18207
    info = soccer.dataset_info()
    for f in ["Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv",
              "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv"]:
        assert f in info


def test_utf8_names(kb):
    assert kb.names["sao paulo"] == "São Paulo"
    assert kb.names["gremio"] == "Grêmio"


# ---- sample questions (>= 20) ----
def test_q1_flaflu():
    out = soccer.head_to_head("Flamengo", "Fluminense")
    assert "Fla-Flu" in out and "Head-to-head in dataset" in out and "wins" in out


def test_q2_palmeiras_2023():
    out = soccer.search_matches(team="Palmeiras", season=2023)
    assert "Palmeiras" in out and "2023-" in out


def test_q3_copa_do_brasil_finals():
    out = soccer.search_matches(competition="Copa do Brasil", stage="Round 8")
    assert "Copa do Brasil" in out and "No matches" not in out


def test_q4_corinthians_home_2022():
    out = soccer.team_record("Corinthians", season=2022, competition="Brasileirão", venue="home")
    import csv
    rows = [r for r in csv.DictReader(open(HERE / "data/kaggle/Brasileirao_Matches.csv", encoding="utf-8"))
            if r["home_team"] == "Corinthians-SP" and r["season"] == "2022" and r["home_goal"] not in ("", "NA")]
    wins = sum(float(r["home_goal"]) > float(r["away_goal"]) for r in rows)
    assert f"Matches: {len(rows)}" in out and f"Wins: {wins}," in out and "Win rate" in out


def test_q5_most_goals_2022():
    out = soccer.top_scoring_teams(season=2022)
    assert out.splitlines()[1].startswith("1. ")


def test_q6_palmeiras_santos():
    assert "Palmeiras vs Santos" in soccer.head_to_head("Palmeiras", "Santos")


def test_q7_brazilian_players():
    out = soccer.search_players(nationality="Brazil")
    assert "Neymar Jr" in out.splitlines()[1]


def test_q8_club_players():
    out = soccer.search_players(club="Grêmio")
    assert "20 found" in out


def test_q9_forwards_from_club():
    out = soccer.search_players(club="Santos", position="forward")
    assert "found" in out and "Santos Laguna" not in out and "Club: Santos" in out


def test_q10_2019_champion():
    assert soccer.champion(2019).startswith("Flamengo") and "90 points" in soccer.champion(2019)


def test_q11_standings_2019():
    out = soccer.standings(2019, top=3)
    assert "1. Flamengo - 90 pts (28W, 6D, 4L" in out


def test_q12_relegated_2020():
    out = soccer.relegated(2020)
    assert "Botafogo" in out and "Coritiba" in out


def test_q13_libertadores_bracket():
    out = soccer.libertadores_bracket(2018)
    assert "Final:" in out and "Semifinals:" in out


def test_q14_avg_goals():
    out = soccer.league_stats("Brasileirão")
    assert "Average goals per match: 2." in out and "Home win rate" in out


def test_q15_best_away_record():
    out = soccer.best_records(competition="Serie A", venue="away", min_matches=50)
    assert out.startswith("Best away records")


def test_q16_biggest_wins():
    out = soccer.biggest_wins(limit=5)
    assert out.count("\n") == 5


def test_q17_last_match():
    out = soccer.last_match("Flamengo", "Corinthians")
    assert "Most recent match" in out and "Score:" in out


def test_q18_who_is_player():
    out = soccer.search_players(name="Neymar")
    assert "Neymar Jr" in out and "Finishing" in out  # detailed view


def test_q19_derbies_2023():
    out = soccer.derbies(2023)
    assert "Derby matches in 2023" in out


def test_q20_team_competitions():
    out = soccer.team_competitions("Palmeiras")
    assert "Copa Libertadores" in out and "Copa do Brasil" in out and "Brasileirão Serie A" in out


def test_q21_compare_seasons():
    out = soccer.compare_seasons([2018, 2019])
    assert "2018:" in out and "2019:" in out and "champion: Flamengo" in out


def test_q22_best_home_record():
    assert "win rate" in soccer.best_records(venue="home", min_matches=100)


def test_q23_cross_file_profile():
    out = soccer.club_profile("Grêmio")
    assert "Copa Libertadores" in out and "FIFA squad (20 players" in out


def test_q24_historical_2003():
    assert soccer.champion(2003).startswith("Cruzeiro")


def test_q25_extended_stats():
    assert "corners:" in soccer.search_matches(team="Flamengo", season=2023, limit=1)


def test_name_variation_merges_sources():
    out = soccer.team_competitions("Athletico Paranaense")
    assert "novo_campeonato_brasileiro.csv" in out and "Brasileirao_Matches.csv" in out


def test_brazilian_clubs_summary():
    out = soccer.brazilian_clubs_summary()
    assert "Grêmio" in out and "Inter:" not in out and "Boavista FC" not in out


def test_performance():
    t = time.time()
    soccer.search_players(nationality="Brazil")
    soccer.head_to_head("Flamengo", "Vasco")
    assert time.time() - t < 2
    t = time.time()
    soccer.best_records()
    soccer.league_stats()
    soccer.standings(2015)
    assert time.time() - t < 5


# ---- MCP protocol ----
def test_tools_list_and_call():
    r = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {t["name"] for t in r["result"]["tools"]}
    assert {"search_matches", "head_to_head", "search_players", "standings"} <= names
    r = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                       "params": {"name": "champion", "arguments": {"season": 2019}}})
    assert r["result"]["isError"] is False and "Flamengo" in r["result"]["content"][0]["text"]
    r = server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nope"}})
    assert r["result"]["isError"] is True
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_stdio_server():
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "head_to_head", "arguments": {"team_a": "Grêmio", "team_b": "Internacional"}}},
    ]
    p = subprocess.run([sys.executable, str(HERE / "server.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                       capture_output=True, text=True, timeout=60)
    lines = [json.loads(line) for line in p.stdout.splitlines()]
    assert len(lines) == 2
    assert lines[0]["result"]["serverInfo"]["name"] == "brazilian-soccer"
    assert "Grenal" in lines[1]["result"]["content"][0]["text"]
