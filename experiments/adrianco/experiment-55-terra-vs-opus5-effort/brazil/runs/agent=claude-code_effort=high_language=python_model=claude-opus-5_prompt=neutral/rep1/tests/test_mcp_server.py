"""MCP protocol tests -- in-process and end-to-end over a real subprocess.

Context
-------
The in-process tests cover the JSON-RPC semantics cheaply.  The subprocess test
is the one that proves the deliverable actually works as an MCP server: it
launches ``python -m brazilian_soccer.server`` exactly as a client such as
Claude Desktop would, performs the ``initialize`` handshake, lists the tools
and calls one, all over line-delimited JSON on stdin/stdout.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from brazilian_soccer.server import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    MCPServer,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def rpc(server: MCPServer, method: str, params=None, request_id=1):
    request = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        request["params"] = params
    return server.handle(request)


# ---------------------------------------------------------------------------
# in-process protocol behaviour
# ---------------------------------------------------------------------------

def test_initialize_handshake(server):
    response = rpc(server, "initialize", {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "1.0"},
    })
    result = response["result"]
    assert result["protocolVersion"] == PROTOCOL_VERSION
    assert result["serverInfo"]["name"] == "brazilian-soccer"
    assert "tools" in result["capabilities"]
    assert "resources" in result["capabilities"]
    assert "Campeonato Brasileiro" in result["instructions"]


@pytest.mark.parametrize("version", SUPPORTED_PROTOCOL_VERSIONS)
def test_older_protocol_versions_are_echoed_back(server, version):
    response = rpc(server, "initialize", {"protocolVersion": version})
    assert response["result"]["protocolVersion"] == version


def test_unsupported_protocol_version_falls_back_to_ours(server):
    response = rpc(server, "initialize", {"protocolVersion": "1999-01-01"})
    assert response["result"]["protocolVersion"] == PROTOCOL_VERSION


def test_notifications_get_no_response(server):
    assert server.handle({"jsonrpc": "2.0",
                          "method": "notifications/initialized"}) is None


def test_ping(server):
    assert rpc(server, "ping")["result"] == {}


def test_tools_list(server):
    tools = rpc(server, "tools/list")["result"]["tools"]
    assert len(tools) == 16
    names = {tool["name"] for tool in tools}
    assert {"find_matches", "head_to_head", "standings", "search_players",
            "dataset_summary"} <= names
    for tool in tools:
        assert tool["description"] and tool["inputSchema"]["type"] == "object"


def test_tools_call_returns_content_and_structured_content(server):
    result = rpc(server, "tools/call",
                 {"name": "standings", "arguments": {"season": 2019}})["result"]
    assert result["isError"] is False
    assert "Flamengo" in result["content"][0]["text"]
    assert result["structuredContent"]["champion"] == "Flamengo"


def test_tool_errors_are_results_not_protocol_failures(server):
    response = rpc(server, "tools/call",
                   {"name": "team_stats", "arguments": {"team": "Barcelona FC"}})
    assert "error" not in response
    assert response["result"]["isError"] is True


def test_unknown_method_is_rejected(server):
    response = rpc(server, "definitely/not/a/method")
    assert response["error"]["code"] == METHOD_NOT_FOUND


def test_malformed_request_is_rejected(server):
    response = server.handle({"method": "ping", "id": 1})
    assert response["error"]["code"] == INVALID_REQUEST
    # The id is readable, so it must be echoed: a client correlating replies
    # by id can never resolve a call answered with id null.
    assert response["id"] == 1
    assert server.handle({"jsonrpc": "2.0", "id": 2})["id"] == 2


def test_positional_params_are_invalid_params_not_an_internal_error(server):
    response = server.handle({"jsonrpc": "2.0", "id": 10,
                              "method": "tools/call", "params": [1, 2]})
    assert response["error"]["code"] == INVALID_PARAMS
    assert "object" in response["error"]["message"]
    # ...and a notification with bad params still gets no reply at all.
    assert server.handle({"jsonrpc": "2.0", "method": "ping",
                          "params": [1, 2]}) is None


def test_empty_batch_is_an_invalid_request(server):
    import io

    stdout = io.StringIO()
    server.serve(io.StringIO("[]\n"), stdout)
    assert json.loads(stdout.getvalue())["error"]["code"] == INVALID_REQUEST


def test_resources_list_and_read(server):
    resources = rpc(server, "resources/list")["result"]["resources"]
    assert len(resources) == 6
    uri = resources[0]["uri"]
    contents = rpc(server, "resources/read", {"uri": uri})["result"]["contents"]
    assert "Rows loaded:" in contents[0]["text"]


def test_prompts(server):
    prompts = rpc(server, "prompts/list")["result"]["prompts"]
    assert {p["name"] for p in prompts} == {"season-review", "derby-report"}
    message = rpc(server, "prompts/get",
                  {"name": "season-review", "arguments": {"season": 2019}})
    assert "2019" in message["result"]["messages"][0]["content"]["text"]


def test_serve_handles_a_stream_of_requests(server, tmp_path):
    import io

    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": PROTOCOL_VERSION}}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
    )
    stdout = io.StringIO()
    server.serve(stdin, stdout)
    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [r["id"] for r in responses] == [1, 2]


def test_invalid_json_gets_a_parse_error(server):
    import io

    stdout = io.StringIO()
    server.serve(io.StringIO("{not json}\n"), stdout)
    assert json.loads(stdout.getvalue())["error"]["code"] == PARSE_ERROR


def test_batched_requests(server):
    import io

    batch = [
        {"jsonrpc": "2.0", "id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    stdout = io.StringIO()
    server.serve(io.StringIO(json.dumps(batch) + "\n"), stdout)
    responses = json.loads(stdout.getvalue())
    assert [r["id"] for r in responses] == [1, 2]


# ---------------------------------------------------------------------------
# end-to-end: a real subprocess speaking stdio JSON-RPC
# ---------------------------------------------------------------------------

def _exchange(requests: list[dict]) -> list[dict]:
    payload = "".join(json.dumps(request) + "\n" for request in requests)
    completed = subprocess.run(
        [sys.executable, "-m", "brazilian_soccer.server"],
        input=payload, capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]


@pytest.mark.slow
def test_end_to_end_over_stdio():
    responses = _exchange([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "head_to_head",
                    "arguments": {"team_a": "Gremio", "team_b": "Internacional",
                                  "limit": 3}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "search_players",
                    "arguments": {"nationality": "Brazil", "min_overall": 85,
                                  "limit": 5}}},
    ])
    assert [r["id"] for r in responses] == [1, 2, 3, 4]
    assert responses[0]["result"]["serverInfo"]["name"] == "brazilian-soccer"
    assert len(responses[1]["result"]["tools"]) == 16

    derby = responses[2]["result"]
    assert derby["structuredContent"]["derby_name"] == "Gre-Nal"
    assert "Gre-Nal" in derby["content"][0]["text"]

    players = responses[3]["result"]["structuredContent"]
    assert all(p["overall"] >= 85 for p in players["players"])


@pytest.mark.slow
def test_self_test_command_runs():
    completed = subprocess.run(
        [sys.executable, "-m", "brazilian_soccer.server", "--self-test"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert "16 tools registered" in completed.stdout
    assert "unique fixtures" in completed.stdout
