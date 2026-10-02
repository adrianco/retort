"""Unit tests for the MCP JSON-RPC handling, using a tiny in-memory dataset."""

import io
import json

import pytest

from brazilian_soccer_mcp.data import SoccerData
from brazilian_soccer_mcp.server import TOOLS, SoccerMcpServer


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    directory = tmp_path_factory.mktemp("kaggle")
    (directory / "Brasileirao_Matches.csv").write_text(
        "datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n"
        "2019-05-01 16:00:00,Flamengo-RJ,RJ,Santos-SP,SP,3,1,2019,1\n", encoding="utf-8")
    return SoccerMcpServer(SoccerData(directory))


def request(server, method, params=None, request_id=1):
    return server.handle({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})


def test_initialize_negotiates_a_supported_protocol_version(server):
    result = request(server, "initialize", {"protocolVersion": "2024-11-05"})["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert "tools" in result["capabilities"]
    unknown = request(server, "initialize", {"protocolVersion": "1999-01-01"})["result"]
    assert unknown["protocolVersion"] == "2025-06-18"


def test_every_tool_is_listed_with_an_object_schema(server):
    tools = request(server, "tools/list")["result"]["tools"]
    assert [t["name"] for t in tools] == [t["name"] for t in TOOLS]
    assert all(t["inputSchema"]["type"] == "object" for t in tools)


def test_notifications_get_no_response(server):
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_unknown_method_and_tool_are_protocol_errors(server):
    assert request(server, "resources/list")["error"]["code"] == -32601
    assert request(server, "tools/call", {"name": "nope", "arguments": {}})["error"]["code"] == -32602


def test_bad_arguments_are_reported_as_tool_errors(server):
    result = request(server, "tools/call", {"name": "team_record", "arguments": {"colour": "red"}})["result"]
    assert result["isError"]
    assert "missing required argument(s) team" in result["content"][0]["text"]


def test_tool_call_returns_text_and_structured_content(server):
    result = request(server, "tools/call", {"name": "team_record", "arguments": {"team": "Flamengo"}})["result"]
    assert not result["isError"]
    assert result["structuredContent"]["wins"] == 1
    assert "Flamengo record" in result["content"][0]["text"]


def test_serve_answers_line_by_line_and_survives_garbage(server):
    stdin = io.StringIO("not json\n" + json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"}) + "\n")
    stdout = io.StringIO()
    server.serve(stdin, stdout)
    replies = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert replies[0]["error"]["code"] == -32700
    assert replies[1] == {"jsonrpc": "2.0", "id": 7, "result": {}}
