"""Feature: MCP protocol and formatted answers to the specification's sample questions."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from brazilian_soccer_mcp.server import TOOLS, call_tool, handle

ROOT = Path(__file__).resolve().parent.parent

# (question from the specification, tool, arguments, text expected in the answer)
SAMPLE_QUESTIONS = [
    ("Show me all Flamengo vs Fluminense matches", "head_to_head",
     {"team_a": "Flamengo", "team_b": "Fluminense"}, "Head-to-head in dataset"),
    ("What matches did Palmeiras play in 2023?", "search_matches",
     {"team": "Palmeiras", "season": 2023}, "match(es) found for Palmeiras"),
    ("Find all Copa do Brasil finals", "search_matches",
     {"competition": "Copa do Brasil", "stage": "final", "limit": 50}, "Athletico-PR 1-0 Internacional"),
    ("What is Corinthians' home record in 2022?", "team_stats",
     {"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"},
     "Wins: 12, Draws: 4, Losses: 3"),
    ("Which team scored the most goals in Serie A 2023?", "rank_teams",
     {"metric": "goals_for", "competition": "Serie A", "season": 2023, "limit": 1}, "1. "),
    ("Compare Palmeiras and Santos head-to-head", "head_to_head",
     {"team_a": "Palmeiras", "team_b": "Santos"}, "Clássico da Saudade"),
    ("Find all Brazilian players in the dataset", "search_players",
     {"nationality": "Brazil"}, "1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"),
    ("Who are the highest-rated players at Flamengo?", "search_players",
     {"club": "Flamengo"}, "No players found"),
    ("Who are the highest-rated players at Grêmio?", "search_players",
     {"club": "Gremio", "limit": 5}, "Club: Grêmio"),
    ("Show me all forwards from Santos", "search_players",
     {"club": "Santos", "position": "forward"}, "Position: ST"),
    ("Who won the 2019 Brasileirão?", "standings",
     {"season": 2019}, "1. Flamengo - 90 pts (28W, 6D, 4L"),
    ("Show the 2018 Copa Libertadores bracket", "competition_bracket",
     {"season": 2018, "competition": "Libertadores"}, "River Plate 3-1 Boca Juniors"),
    ("Which teams were relegated in 2020?", "standings",
     {"season": 2020, "competition": "Brasileirão"}, "Relegated"),
    ("What's the average goals per match in the Brasileirão?", "competition_stats",
     {"competition": "Brasileirão"}, "Average goals per match: 2."),
    ("Which team has the best away record?", "rank_teams",
     {"venue": "away", "competition": "Serie A", "min_matches": 100}, "win rate"),
    ("Which team has the best home record?", "rank_teams",
     {"venue": "home", "competition": "Serie A", "min_matches": 100}, "win rate"),
    ("Show me the biggest wins in the dataset", "biggest_wins", {}, "1. "),
    ("When did Flamengo last play Corinthians?", "search_matches",
     {"team": "Flamengo", "opponent": "Corinthians", "limit": 1}, "2023-10-08: Corinthians 1-1 Flamengo"),
    ("Who is Neymar?", "player_details", {"player": "Neymar"}, "Overall: 92, Potential: 93"),
    ("Who is Gabriel Barbosa?", "search_players", {"name": "Gabriel Barbosa"}, "Gabriel"),
    ("Which players play for Santos?", "team_profile", {"team": "Santos"}, "FIFA squad"),
    ("Show me all derbies in 2023", "derbies", {"season": 2023}, "[Fla-Flu]"),
    ("What competitions has Palmeiras played in?", "team_profile",
     {"team": "Palmeiras"}, "- Copa Libertadores: seasons"),
    ("Who are the top Brazilian players?", "search_players",
     {"nationality": "Brazil", "limit": 10}, "Neymar Jr"),
    ("Brazilian players at Brazilian clubs", "players_by_club", {}, "avg rating"),
    ("Compare the 2018 and 2019 seasons", "compare_seasons",
     {"seasons": [2018, 2019]}, "Top of table: Flamengo (90 pts)"),
    ("What data do you have?", "data_summary", {}, "fifa_data.csv: 18207 players"),
]


@pytest.mark.parametrize("question, tool, args, expected", SAMPLE_QUESTIONS,
                         ids=[q[0] for q in SAMPLE_QUESTIONS])
def test_sample_question(kb, question, tool, args, expected):
    start = time.perf_counter()
    text = call_tool(tool, args, kb)
    assert expected in text, text[:600]
    assert time.perf_counter() - start < 2


def test_at_least_20_sample_questions_and_every_tool_covered():
    assert len(SAMPLE_QUESTIONS) >= 20
    assert {q[1] for q in SAMPLE_QUESTIONS} == set(TOOLS)


def test_match_line_format(kb):
    text = call_tool("search_matches", {"team": "Flamengo", "opponent": "Fluminense",
                                        "season": 2019, "competition": "Brasileirão"}, kb)
    assert "- 2019-10-20: Flamengo 2-0 Fluminense (Brasileirão Série A 2019, Round 27" in text


def test_long_lists_are_truncated(kb):
    text = call_tool("search_matches", {"team": "Flamengo", "limit": 5}, kb)
    assert text.count("\n- ") == 6 and "more matches in dataset)" in text


def rpc(method, params=None, id=1):
    return handle({"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}})


class TestProtocol:
    def test_initialize(self):
        r = rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})["result"]
        assert r["protocolVersion"] == "2024-11-05"
        assert "tools" in r["capabilities"] and r["serverInfo"]["name"] == "brazilian-soccer"

    def test_notifications_get_no_response(self):
        assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    def test_tools_list_has_valid_schemas(self):
        tools = rpc("tools/list")["result"]["tools"]
        assert len(tools) == len(TOOLS) >= 10
        for t in tools:
            assert t["description"] and t["inputSchema"]["type"] == "object"
            assert set(t["inputSchema"]["required"]) <= set(t["inputSchema"]["properties"])

    def test_tools_call(self):
        r = rpc("tools/call", {"name": "standings", "arguments": {"season": 2019, "limit": 1}})
        assert r["result"]["isError"] is False
        assert "Flamengo - 90 pts" in r["result"]["content"][0]["text"]

    def test_bad_input_is_a_tool_error_not_a_crash(self):
        for args in ({"team": "Nonexistent FC"}, {"bogus": 1}, {"date_from": "soon"},
                     {"season": "abc"}):
            r = rpc("tools/call", {"name": "search_matches", "arguments": args})["result"]
            assert r["isError"] is True and r["content"][0]["text"].startswith("Error:")
        r = rpc("tools/call", {"name": "team_stats", "arguments": {}})["result"]
        assert r["isError"] and "Missing required" in r["content"][0]["text"]

    def test_unknown_tool_and_method(self):
        assert rpc("tools/call", {"name": "nope"})["error"]["code"] == -32602
        assert rpc("resources/list")["error"]["code"] == -32601

    def test_stdio_end_to_end(self):
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "test", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "team_stats", "arguments": {"team": "São Paulo", "season": 2008}}},
        ]
        payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in requests) + "\nnot json\n"
        proc = subprocess.run([sys.executable, "-m", "brazilian_soccer_mcp.server"], cwd=ROOT,
                              input=payload.encode("utf-8"), capture_output=True, timeout=60)
        assert proc.returncode == 0, proc.stderr.decode()
        out = [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]
        assert [o["id"] for o in out] == [1, 2, 3, None]
        assert "São Paulo record" in out[2]["result"]["content"][0]["text"]
        assert out[3]["error"]["code"] == -32700
