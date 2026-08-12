import soccer_mcp
import json
import subprocess
import sys


def test_real_datasets_are_loaded():
    db = soccer_mcp.SoccerDatabase()
    assert len(db.matches) > 20_000
    assert len(db.players) > 18_000


def test_team_suffix_and_head_to_head_normalization():
    db = soccer_mcp.SoccerDatabase()
    rows = db.matches_query(team="Palmeiras", opponent="Portuguesa", season=2012)
    assert rows and all("Palmeiras" in (r["home_team"] + r["away_team"]) or "Portuguesa" in (r["home_team"] + r["away_team"]) for r in rows)


def test_team_statistics_are_consistent():
    db = soccer_mcp.SoccerDatabase()
    stats = db.team_stats("Palmeiras", season=2012, competition="Brasileirão")
    assert stats["matches"] > 0
    assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
    assert 0 <= stats["win_rate"] <= 100


def test_player_filters_and_rating_sort():
    db = soccer_mcp.SoccerDatabase()
    players = db.players_query(nationality="Brazil", min_overall=85, limit=10)
    assert players
    assert all(p["Nationality"] == "Brazil" and int(p["Overall"]) >= 85 for p in players)
    assert [int(p["Overall"]) for p in players] == sorted((int(p["Overall"]) for p in players), reverse=True)


def test_standings_and_aggregates():
    db = soccer_mcp.SoccerDatabase()
    table = db.standings(2012)
    assert table and table[0]["points"] >= table[-1]["points"]
    aggregate = db.aggregate_stats(season=2012)
    assert aggregate["matches"] > 0 and aggregate["average_goals"] >= 0


def test_overlapping_brasileirao_sources_are_not_double_counted():
    db = soccer_mcp.SoccerDatabase()
    stats = db.team_stats("Flamengo", season=2019, competition="Brasileirao")
    assert stats["matches"] == 38
    table = db.standings(2019, "Brasileirao")
    assert table[0]["team"] == "Flamengo"
    assert table[0]["points"] == 90


def test_mcp_tools_are_callable(monkeypatch, capsys):
    # Exercise the protocol's public dispatch without starting a subprocess.
    db = soccer_mcp.SoccerDatabase()
    result = soccer_mcp._call(db, "statistics", {"season": 2012})
    assert result["matches"] > 0


def test_stdio_entrypoint_serves_tools_and_standings():
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "standings", "arguments": {"season": 2019, "competition": "Brasileirao"}}},
    ]
    proc = subprocess.run([sys.executable, "soccer_mcp.py"], input="\n".join(json.dumps(r) for r in requests) + "\n", text=True, capture_output=True, check=True)
    responses = [json.loads(line) for line in proc.stdout.splitlines()]
    assert responses[0]["result"]["serverInfo"]["name"] == "brazilian-soccer"
    assert any(tool["name"] == "standings" for tool in responses[1]["result"]["tools"])
    payload = json.loads(responses[2]["result"]["content"][0]["text"])
    assert payload[0]["team"] == "Flamengo"
