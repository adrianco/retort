"""Feature: MCP server - tools are discoverable and answer the sample questions."""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from brazilian_soccer import QueryError
from brazilian_soccer.server import TOOLS, call_tool, handle_message

ROOT = Path(__file__).resolve().parent.parent

# (question, tool, arguments, text expected in the answer)
SAMPLE_QUESTIONS = [
    ("Show me all Flamengo vs Fluminense matches", "head_to_head",
     {"team_a": "Flamengo", "team_b": "Fluminense"}, "Fla-Flu"),
    ("What matches did Palmeiras play in 2023?", "search_matches",
     {"team": "Palmeiras", "season": 2023}, "Palmeiras"),
    ("Find all Copa do Brasil finals", "search_matches",
     {"competition": "Copa do Brasil", "stage": "final", "limit": 50}, "2012-07-11"),
    ("When did Flamengo last play Corinthians?", "search_matches",
     {"team": "Flamengo", "opponent": "Corinthians", "limit": 1}, "2023-"),
    ("What is Corinthians' home record in 2022?", "team_stats",
     {"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"},
     "Wins: 12, Draws: 4, Losses: 3"),
    ("Which team scored the most goals in Serie A 2019?", "rank_teams",
     {"metric": "goals_for", "competition": "Serie A", "season": 2019, "limit": 1}, "1. Flamengo"),
    ("Compare Palmeiras and Santos head-to-head", "head_to_head",
     {"team_a": "Palmeiras", "team_b": "Santos"}, "Head-to-head in dataset"),
    ("Find all Brazilian players in the dataset", "search_players",
     {"nationality": "Brazil"}, "Found 827 player(s)"),
    ("Who are the top Brazilian players?", "search_players",
     {"nationality": "Brazil", "limit": 3}, "1. Neymar Jr - Overall: 92"),
    ("Who are the highest-rated players at Grêmio?", "search_players",
     {"club": "Grêmio", "limit": 5}, "Club: Grêmio"),
    ("Show me all forwards from Santos", "search_players",
     {"club": "Santos", "position": "forward"}, "Position: ST"),
    ("Who is Neymar?", "player_details", {"name": "Neymar"}, "Paris Saint-Germain"),
    ("Brazilian players at Brazilian clubs", "players_by_club",
     {"nationality": "Brazil"}, "avg rating"),
    ("Who won the 2019 Brasileirão?", "standings",
     {"season": 2019}, "1. Flamengo - 90 pts (28W, 6D, 4L"),
    ("Which teams were relegated in 2020?", "season_summary",
     {"season": 2020}, "Relegated (bottom four): Vasco da Gama, Goiás, Coritiba, Botafogo"),
    ("Who won the 2019 Copa Libertadores?", "season_summary",
     {"season": 2019, "competition": "Libertadores"}, "Champion: Flamengo"),
    ("Show the 2018 Copa Libertadores knockout matches", "search_matches",
     {"competition": "Libertadores", "season": 2018, "stage": "semifinals"}, "semifinals"),
    ("What's the average goals per match in the Brasileirão?", "competition_stats",
     {"competition": "Brasileirão"}, "Average goals per match: 2.5"),
    ("Which team has the best away record?", "rank_teams",
     {"venue": "away", "min_matches": 100}, "ranked by away win rate"),
    ("Which team has the best home record?", "rank_teams",
     {"venue": "home", "min_matches": 100}, "ranked by home win rate"),
    ("Show me the biggest wins in the dataset", "biggest_wins", {}, "1. "),
    ("Show me all derbies in 2023", "list_derbies", {"season": 2023}, "Fla-Flu"),
    ("What competitions has Palmeiras played in?", "team_competitions",
     {"team": "Palmeiras"}, "Copa Libertadores"),
    ("Compare the 2018 and 2019 seasons", "compare_seasons",
     {"season_a": 2018, "season_b": 2019}, "Best record: Flamengo (90 pts)"),
    ("Tell me about Grêmio (matches + players)", "team_profile", {"team": "Grêmio"}, "FIFA squad"),
    ("What data do you have?", "dataset_summary", {}, "fifa_data.csv"),
]


@pytest.mark.parametrize("question, tool, arguments, expected", SAMPLE_QUESTIONS,
                         ids=[q[0] for q in SAMPLE_QUESTIONS])
def test_sample_question_is_answered_quickly(ask, question, tool, arguments, expected):
    # Given the data is loaded / When the question's tool call is made
    started = time.perf_counter()
    answer = ask(tool, **arguments)
    elapsed = time.perf_counter() - started
    # Then the answer contains the expected fact and arrives well within the limits
    assert expected in answer, answer
    assert elapsed < 2.0


def test_at_least_twenty_sample_questions_are_covered():
    assert len(SAMPLE_QUESTIONS) >= 20
    assert {q[1] for q in SAMPLE_QUESTIONS} == set(TOOLS)


def test_long_results_are_truncated_with_a_count(ask):
    answer = ask("search_matches", team="Flamengo", limit=5)
    assert answer.count("\n- ") == 6 and "more matches in dataset" in answer


def test_tool_argument_validation(db):
    with pytest.raises(QueryError, match="Missing required"):
        call_tool("team_stats", {}, db)
    with pytest.raises(QueryError, match="Unknown argument"):
        call_tool("team_stats", {"team": "Flamengo", "colour": "red"}, db)
    with pytest.raises(QueryError, match="Unknown tool"):
        call_tool("make_coffee", {}, db)
    with pytest.raises(QueryError):
        call_tool("search_players", {"min_overall": "high"}, db)


def _rpc(method, params=None, request_id=1):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def test_initialize_negotiates_protocol_and_advertises_tools(db):
    result = handle_message(_rpc("initialize", {"protocolVersion": "2024-11-05"}), db)["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert "tools" in result["capabilities"]
    assert result["serverInfo"]["name"] == "brazilian-soccer"
    newer = handle_message(_rpc("initialize", {"protocolVersion": "2099-01-01"}), db)["result"]
    assert newer["protocolVersion"] != "2099-01-01"


def test_tools_list_has_valid_schemas(db):
    tools = handle_message(_rpc("tools/list"), db)["result"]["tools"]
    assert len(tools) == len(TOOLS) >= 10
    for spec in tools:
        schema = spec["inputSchema"]
        assert spec["name"] and spec["description"]
        assert schema["type"] == "object"
        assert set(schema["required"]) <= set(schema["properties"])


def test_tools_call_returns_text_content(db):
    response = handle_message(
        _rpc("tools/call", {"name": "standings", "arguments": {"season": 2019, "limit": 1}}), db)
    result = response["result"]
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert "Flamengo - 90 pts" in result["content"][0]["text"]


def test_tool_errors_are_reported_in_band(db):
    result = handle_message(
        _rpc("tools/call", {"name": "team_stats", "arguments": {"team": "Nowhere FC"}}), db)["result"]
    assert result["isError"] is True
    assert "No team matching" in result["content"][0]["text"]


def test_protocol_errors(db):
    assert handle_message(_rpc("no/such/method"), db)["error"]["code"] == -32601
    assert handle_message(_rpc("tools/call", {"name": "nope"}), db)["error"]["code"] == -32602
    assert handle_message({"id": 1, "method": "ping"}, db)["error"]["code"] == -32600
    assert handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}, db) is None
    assert handle_message(_rpc("ping"), db)["result"] == {}


def test_server_speaks_mcp_over_stdio():
    # Given the server is started as a subprocess, as an MCP client would
    requests = [
        _rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                            "clientInfo": {"name": "pytest", "version": "0"}}, 1),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        _rpc("tools/list", request_id=2),
        _rpc("tools/call", {"name": "head_to_head",
                            "arguments": {"team_a": "Grêmio", "team_b": "Internacional"}}, 3),
    ]
    payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in requests) + "\nnot json\n"
    # When the requests are written to its stdin
    completed = subprocess.run([sys.executable, "-m", "brazilian_soccer.server"], input=payload,
                               capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=60)
    # Then one JSON-RPC response per request comes back on stdout, and nothing else
    assert completed.returncode == 0, completed.stderr
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    assert [r["id"] for r in responses] == [1, 2, 3, None]
    assert responses[0]["result"]["protocolVersion"] == "2025-06-18"
    assert len(responses[1]["result"]["tools"]) == len(TOOLS)
    assert "Gre-Nal" in responses[2]["result"]["content"][0]["text"]
    assert responses[3]["error"]["code"] == -32700
