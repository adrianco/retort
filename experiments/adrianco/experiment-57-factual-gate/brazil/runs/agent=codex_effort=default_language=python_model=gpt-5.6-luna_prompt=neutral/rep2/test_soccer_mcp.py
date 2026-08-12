import json
import subprocess
import sys
from pathlib import Path

from soccer_mcp import SoccerData, normalize_team, parse_date


ROOT = Path(__file__).parent


def test_normalization_and_dates():
    assert normalize_team("Palmeiras-SP") == "palmeiras"
    assert normalize_team("São Paulo Futebol Clube") == "sao paulo"
    assert parse_date("29/03/2003").year == 2003


def test_all_datasets_are_loaded():
    data = SoccerData(ROOT / "data/kaggle")
    # The supplied files contain 23,954 rows in this checkout (the task's
    # rounded descriptions sum to approximately 24k).
    assert len(data.matches) >= 23900
    assert len(data.players) > 18000
    assert {"Brasileirão", "Copa do Brasil", "Copa Libertadores"} <= {m.competition for m in data.matches}


def test_match_search_supports_team_season_and_limit():
    data = SoccerData(ROOT / "data/kaggle")
    matches = data.find_matches(team="Palmeiras", season=2023, limit=5)
    assert 0 < len(matches) <= 5
    assert all("date" in m and "home_goals" in m and "competition" in m for m in matches)


def test_team_stats_and_head_to_head():
    data = SoccerData(ROOT / "data/kaggle")
    stats = data.team_stats("Corinthians", season=2022, competition="Brasileirão", home_only=True)
    assert stats["matches"] >= stats["wins"] + stats["draws"] + stats["losses"]
    h2h = data.head_to_head("Flamengo", "Fluminense", competition="Brasileirão")
    assert h2h["summary"]["draws"] + h2h["summary"]["Flamengo"] + h2h["summary"]["Fluminense"] == len(h2h["matches"])


def test_players_standings_and_statistics():
    data = SoccerData(ROOT / "data/kaggle")
    players = data.players_search(nationality="Brazil", limit=10)
    assert len(players) == 10 and all(p["Nationality"] == "Brazil" for p in players)
    table = data.standings(2019)
    assert table and table[0]["position"] == 1
    stats = data.statistics(competition="Brasileirão", season=2019)
    assert stats["matches"] > 0 and stats["total_goals"] >= stats["matches"]


def test_2019_brasileirao_standings_use_one_source_and_keep_atletico_variants():
    data = SoccerData(ROOT / "data/kaggle")
    table = data.standings(2019)
    by_key = {normalize_team(row["team"]): row for row in table}

    assert len(table) == 20
    assert sum(row["played"] for row in table) == 20 * 38
    assert by_key["flamengo"]["played"] == 38
    assert by_key["flamengo"]["points"] == 90
    assert by_key["atletico mineiro"]["played"] == 38
    assert by_key["atletico paranaense"]["played"] == 38


def test_mcp_stdio_initialize_and_tool_list():
    payload = "\n".join([json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}), json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})]) + "\n"
    completed = subprocess.run([sys.executable, "server.py"], input=payload, text=True, capture_output=True, cwd=ROOT, check=True)
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    assert responses[0]["result"]["serverInfo"]["name"] == "brazilian-soccer"
    assert {tool["name"] for tool in responses[1]["result"]["tools"]} >= {"find_matches", "search_players", "standings"}
