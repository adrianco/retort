"""MCP protocol behaviour: JSON-RPC handling, tool listing/calls, errors, and a real stdio subprocess."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from brsoccer.server import (INVALID_PARAMS, LATEST_PROTOCOL_VERSION, METHOD_NOT_FOUND, PARSE_ERROR, TOOLS,
                             MCPServer, tool_signature_check)

ROOT = Path(__file__).resolve().parent.parent


def rpc(server, method, params=None, msg_id=1):
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    return server.handle(msg)


@pytest.fixture()
def server(db):
    return MCPServer()


def test_initialize_negotiates_version(server):
    r = rpc(server, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                   "clientInfo": {"name": "t", "version": "0"}})
    assert r["result"]["protocolVersion"] == "2024-11-05"
    assert r["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert r["result"]["serverInfo"]["name"] == "brazilian-soccer"
    r = rpc(server, "initialize", {"protocolVersion": "1999-01-01"})
    assert r["result"]["protocolVersion"] == LATEST_PROTOCOL_VERSION


def test_notifications_get_no_response(server):
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert server.initialized


def test_ping(server):
    assert rpc(server, "ping")["result"] == {}


def test_tools_list_schemas(server):
    tools = rpc(server, "tools/list")["result"]["tools"]
    assert len(tools) == len(TOOLS) >= 15
    for t in tools:
        assert t["name"] and t["description"]
        schema = t["inputSchema"]
        assert schema["type"] == "object"
        assert set(schema["required"]) <= set(schema["properties"])
    assert tool_signature_check() == []


def test_tools_call_text_and_structured_content(server):
    rpc(server, "initialize", {"protocolVersion": "2025-06-18"})
    r = rpc(server, "tools/call", {"name": "standings", "arguments": {"season": 2019, "top": 2}})
    result = r["result"]
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert "Flamengo - 90 pts" in result["content"][0]["text"]
    assert result["structuredContent"]["champion"] == "Flamengo"


def test_old_protocol_has_no_structured_content(server):
    rpc(server, "initialize", {"protocolVersion": "2024-11-05"})
    r = rpc(server, "tools/call", {"name": "dataset_info", "arguments": {}})
    assert "structuredContent" not in r["result"]


def test_tool_errors_are_reported_in_result(server):
    r = rpc(server, "tools/call", {"name": "team_record", "arguments": {"team": "Nonexistent United"}})
    assert r["result"]["isError"] is True
    assert "No team matching" in r["result"]["content"][0]["text"]
    r = rpc(server, "tools/call", {"name": "team_record", "arguments": {}})
    assert r["result"]["isError"] and "Missing required" in r["result"]["content"][0]["text"]
    r = rpc(server, "tools/call", {"name": "team_record", "arguments": {"team": "Santos", "bogus": 1}})
    assert r["result"]["isError"] and "Unknown argument" in r["result"]["content"][0]["text"]


def test_protocol_errors(server):
    assert rpc(server, "tools/call", {"name": "nope"})["error"]["code"] == INVALID_PARAMS
    assert rpc(server, "resources/read")["error"]["code"] == METHOD_NOT_FOUND
    assert server.handle({"id": 1, "method": "ping"})["error"]["code"] == -32600


def test_batch(server):
    out = server.handle([{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                         {"jsonrpc": "2.0", "method": "notifications/initialized"},
                         {"jsonrpc": "2.0", "id": 2, "method": "ping"}])
    assert [r["id"] for r in out] == [1, 2]


def test_stdio_subprocess_end_to_end():
    """Launch the real server process and talk MCP to it over stdin/stdout."""
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "head_to_head", "arguments": {"team_a": "São Paulo", "team_b": "Palmeiras"}}},
    ]
    stdin = "\n".join(json.dumps(m, ensure_ascii=False) for m in messages) + "\nnot json\n"
    proc = subprocess.run([sys.executable, "mcp_server.py"], input=stdin.encode("utf-8"), cwd=ROOT,
                          capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode()
    responses = [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]
    assert [r.get("id") for r in responses] == [1, 2, 3, None]
    assert responses[0]["result"]["serverInfo"]["name"] == "brazilian-soccer"
    assert len(responses[1]["result"]["tools"]) == len(TOOLS)
    text = responses[2]["result"]["content"][0]["text"]
    assert "São Paulo vs Palmeiras (Choque-Rei derby)" in text
    assert responses[3]["error"]["code"] == PARSE_ERROR
