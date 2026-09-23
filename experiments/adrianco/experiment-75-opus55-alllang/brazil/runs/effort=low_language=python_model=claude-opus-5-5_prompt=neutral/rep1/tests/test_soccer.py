"""BDD-style scenarios (Given/When/Then) for the Brazilian Soccer MCP server."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mcp_server import call_tool, handle, list_tools
from soccer_data import get_db, normalize_team, parse_date

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def db():
    # Given the match and player data is loaded
    return get_db()


# ---- Feature: data loading & normalization ----
def test_all_six_files_load(db):
    counts = {k: len(v) for k, v in db.sources.items()}
    assert counts["Brasileirao_Matches.csv"] == 4180 - 82  # 82 rows have NA scores (not played)
    assert counts["Brazilian_Cup_Matches.csv"] >= 1320  # a few NA-score rows skipped
    assert counts["Libertadores_Matches.csv"] >= 1250
    assert counts["BR-Football-Dataset.csv"] >= 10000
    assert counts["novo_campeonato_brasileiro.csv"] == 6886
    assert len(db.players) == 18207


@pytest.mark.parametrize("variants", [
    ["Palmeiras-SP", "Palmeiras", "SE Palmeiras", "Palmeiras - SP"],
    ["Sport Club Corinthians Paulista", "Corinthians-SP", "Corinthians"],
    ["São Paulo", "Sao Paulo-SP", "Sao Paulo", "São Paulo - SP"],
    ["Atletico-MG", "Atlético - MG", "Atletico Mineiro", "Atlético Mineiro"],
    ["Athletico-PR", "Atletico-PR", "Athletico Paranaense", "Atlético Paranaense - PR"],
    ["Grêmio", "Gremio-RS", "Gremio"],
    ["Vasco da Gama-RJ", "Vasco"],
])
def test_team_name_variations(variants):
    assert len({normalize_team(v) for v in variants}) == 1


def test_state_disambiguation():
    assert normalize_team("Atletico-GO") != normalize_team("Atletico-MG")
    assert normalize_team("America - RN") != normalize_team("America-MG")


def test_date_formats():
    assert str(parse_date("29/03/2003")) == "2003-03-29"
    assert str(parse_date("2012-05-19 18:30:00")) == "2012-05-19"
    assert str(parse_date("2023-09-24")) == "2023-09-24"


# ---- Feature: Match Queries ----
def test_matches_between_two_teams(db):
    # When I search for matches between "Flamengo" and "Fluminense"
    ms = db.find_matches(team="Flamengo", opponent="Fluminense")
    # Then I should receive a list of matches, each with date, scores and competition
    assert len(ms) > 20
    for m in ms:
        assert {m.home, m.away} == {"flamengo", "fluminense"}
        assert m.date and m.competition and m.home_goals >= 0 and m.away_goals >= 0
    text = call_tool("head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"})
    assert "Fla-Flu" in text and "Head-to-head in dataset" in text


def test_matches_by_season_and_competition(db):
    ms = db.find_matches(team="Palmeiras", season=2023)
    assert ms and all(m.season == 2023 for m in ms)
    cup = db.find_matches(competition="Copa do Brasil", round_contains="8")
    assert cup and all(m.competition == "Copa do Brasil" for m in cup)
    finals = db.find_matches(competition="Libertadores", round_contains="final")
    assert finals and all(m.round == "final" for m in finals)


def test_date_range(db):
    ms = db.find_matches(team="Santos", date_from="2019-01-01", date_to="2019-12-31")
    assert ms and all(m.date.year == 2019 for m in ms)


def test_last_meeting(db):
    ms = db.find_matches(team="Flamengo", opponent="Corinthians")
    assert ms[0].date >= ms[-1].date


# ---- Feature: Team Queries ----
def test_team_stats(db):
    # When I request statistics for "Palmeiras" in season "2023"
    s = db.team_stats("Palmeiras", season=2023)
    # Then I should receive wins, losses, draws, and goals
    assert s["matches"] == s["wins"] + s["draws"] + s["losses"] > 0
    assert s["goals_for"] > 0 and s["goals_against"] > 0


def test_home_record_no_duplicates(db):
    s = db.team_stats("Corinthians", season=2022, competition="Brasileirão", venue="home")
    assert s["matches"] == 19


def test_competitions_for_team(db):
    comps = db.competitions_for("Palmeiras")
    assert {"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"} <= set(comps)


# ---- Feature: Competition Queries ----
def test_2019_champion(db):
    table = db.standings(2019)
    assert len(table) == 20
    assert table[0]["team"] == "Flamengo" and table[0]["points"] == 90
    assert "Champion" in call_tool("league_standings", {"season": 2019})


def test_historical_standings(db):
    table = db.standings(2005)
    assert table and table[0]["team"] == "Corinthians"


def test_relegated_2020():
    text = call_tool("league_standings", {"season": 2020})
    assert "Botafogo" in text.split("\n")[-1] and "Relegation" in text


# ---- Feature: Statistical Analysis ----
def test_aggregates(db):
    a = db.aggregate(competition="Brasileirão")
    assert 2.0 < a["avg_goals"] < 3.0
    assert a["home_win_rate"] > a["away_win_rate"]


def test_biggest_wins(db):
    ms = db.biggest_wins(limit=5)
    margins = [abs(m.home_goals - m.away_goals) for m in ms]
    assert margins == sorted(margins, reverse=True) and margins[0] >= 7


def test_rankings(db):
    rows = db.rankings("away_win_rate", competition="Brasileirão", limit=5)
    assert len(rows) == 5 and rows[0]["win_rate"] >= rows[-1]["win_rate"]
    assert db.rankings("goals_for", season=2019, limit=1)[0]["team"] == "Flamengo"


def test_derbies(db):
    ms = db.derbies(season=2019)
    assert ms and all(m.competition for m in ms)


# ---- Feature: Player Queries ----
def test_brazilian_players(db):
    ps = db.search_players(nationality="Brazil", limit=3)
    assert ps[0]["Name"] == "Neymar Jr" and all(p["Nationality"] == "Brazil" for p in ps)


def test_player_by_name_and_club(db):
    assert db.search_players(name="Gabriel Jesus")[0]["Club"] == "Manchester City"
    fw = db.search_players(club="Santos", position="forward")
    assert fw and all(p["Position"] in {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"} for p in fw)
    assert db.search_players(name="zzzz") == []


def test_brazilian_clubs_and_cross_file(db):
    rows = db.brazilian_club_players()
    assert rows and any(r["club"] == "Grêmio" for r in rows)
    prof = db.club_profile("Gremio")
    assert prof["players"] and prof["record"]["matches"] > 100


# ---- Feature: MCP protocol ----
def test_protocol_handlers():
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "brazilian-soccer"
    tools = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    assert len(tools) == len(list_tools()) >= 10
    r = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "nope", "arguments": {}}})
    assert r["result"]["isError"]
    assert "error" in handle({"jsonrpc": "2.0", "id": 4, "method": "bogus"})
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_stdio_server_end_to_end():
    reqs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "team_stats", "arguments": {"team": "Grêmio", "season": 2019}}}]
    out = subprocess.run([sys.executable, str(ROOT / "mcp_server.py")], input="\n".join(map(json.dumps, reqs)),
                         capture_output=True, text=True, timeout=60, cwd=ROOT).stdout.strip().split("\n")
    assert len(out) == 2
    assert "Grêmio" in json.loads(out[1])["result"]["content"][0]["text"]


# ---- 20+ sample questions, with performance limits ----
SAMPLES = [
    ("search_matches", {"team": "Flamengo", "opponent": "Fluminense"}),
    ("search_matches", {"team": "Palmeiras", "season": 2023}),
    ("search_matches", {"competition": "Copa do Brasil", "round_contains": "8"}),
    ("search_matches", {"team": "Flamengo", "opponent": "Corinthians", "limit": 1}),
    ("team_stats", {"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"}),
    ("team_rankings", {"metric": "goals_for", "season": 2019, "competition": "Brasileirão"}),
    ("head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"}),
    ("search_players", {"nationality": "Brazil"}),
    ("search_players", {"club": "Grêmio"}),
    ("search_players", {"club": "Santos", "position": "forward"}),
    ("search_players", {"name": "Neymar"}),
    ("league_standings", {"season": 2019}),
    ("search_matches", {"competition": "Libertadores", "season": 2018, "round_contains": "final"}),
    ("league_standings", {"season": 2020}),
    ("competition_stats", {"competition": "Brasileirão"}),
    ("team_rankings", {"metric": "away_win_rate"}),
    ("team_rankings", {"metric": "home_win_rate"}),
    ("biggest_wins", {}),
    ("derbies", {"season": 2019}),
    ("team_competitions", {"team": "Palmeiras"}),
    ("competition_stats", {"competition": "Brasileirão", "season": 2018}),
    ("brazilian_club_players", {}),
    ("club_profile", {"team": "Internacional"}),
]


@pytest.mark.parametrize("tool,args", SAMPLES)
def test_sample_questions(db, tool, args):
    t = time.perf_counter()
    text = call_tool(tool, args)
    assert time.perf_counter() - t < 2
    assert text and "No matches found" not in text and "No players found" not in text
