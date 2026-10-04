import io
import json

from brazilian_soccer_mcp.data import SoccerData, parse_date
from brazilian_soccer_mcp.knowledge import SoccerKnowledge
from brazilian_soccer_mcp.server import McpServer, serve


def server():
    return McpServer(SoccerKnowledge(SoccerData()))


def exchange(*messages):
    reader = io.StringIO("".join((m if isinstance(m, str) else json.dumps(m)) + "\n" for m in messages))
    writer = io.StringIO()
    serve(server(), reader, writer)
    return [json.loads(line) for line in writer.getvalue().splitlines()]


def test_initialize_agrees_a_protocol_version_and_offers_tools():
    [response] = exchange({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                           "params": {"protocolVersion": "2025-03-26", "capabilities": {}}})
    assert response["result"]["protocolVersion"] == "2025-03-26"
    assert "tools" in response["result"]["capabilities"]


def test_unsupported_protocol_versions_get_the_latest():
    [response] = exchange({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999"}})
    assert response["result"]["protocolVersion"] == "2025-06-18"


def test_notifications_get_no_reply():
    assert exchange({"jsonrpc": "2.0", "method": "notifications/initialized"}) == []


def test_ping():
    assert exchange({"jsonrpc": "2.0", "id": 7, "method": "ping"}) == [{"jsonrpc": "2.0", "id": 7, "result": {}}]


def test_malformed_json_is_a_parse_error():
    [response] = exchange("{not json")
    assert response["error"]["code"] == -32700


def test_unknown_methods_are_reported():
    [response] = exchange({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})
    assert response["error"]["code"] == -32601


def test_unknown_tools_are_invalid_params():
    [response] = exchange({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nope"}})
    assert response["error"]["code"] == -32602


def test_questions_that_cannot_be_answered_are_tool_errors_not_crashes():
    [response] = exchange({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                           "params": {"name": "standings", "arguments": {"season": "twenty"}}})
    assert response["result"]["isError"] is True
    assert "not a valid season" in response["result"]["content"][0]["text"]


def test_every_tool_describes_its_input():
    [response] = exchange({"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
    for tool in response["result"]["tools"]:
        assert tool["description"] and tool["inputSchema"]["type"] == "object"


def test_dates_in_every_format():
    assert parse_date("2023-09-24") == "2023-09-24"
    assert parse_date("2012-05-19 18:30:00") == "2012-05-19"
    assert parse_date("29/03/2003") == "2003-03-29"
    assert parse_date("NA") is None
