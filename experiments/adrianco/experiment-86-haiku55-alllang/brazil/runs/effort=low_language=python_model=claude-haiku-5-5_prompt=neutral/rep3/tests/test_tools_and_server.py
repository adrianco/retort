"""Feature: the LLM reaches the data through MCP tools over JSON-RPC stdio."""

import io
import json

import pytest

from brazsoccer_mcp.mcp_server import MCPServer
from brazsoccer_mcp.tools import TOOLS, call_tool


def _rpc(server: MCPServer, method: str, params=None, request_id=1):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return server.handle(message)


def _serve(data, *lines: str) -> list[dict]:
    """Feed raw input lines to the server and return every response object."""
    reader = io.StringIO("\n".join(lines) + "\n")
    writer = io.StringIO()
    MCPServer(data).serve(reader, writer)
    return [json.loads(line) for line in writer.getvalue().splitlines()]


class TestProtocol:
    def test_given_initialize_then_server_advertises_tools_capability(self, data):
        # Given a server over the data set
        # When a client initializes
        response = _rpc(MCPServer(data), "initialize", {})
        # Then the protocol version, tools capability and server name are returned
        result = response["result"]
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "brazilian-soccer-mcp"

    def test_given_tools_list_then_every_tool_has_a_schema(self, data):
        tools = _rpc(MCPServer(data), "tools/list")["result"]["tools"]
        assert {t["name"] for t in tools} == {t.name for t in TOOLS}
        for tool in tools:
            assert tool["inputSchema"]["type"] == "object"
            assert tool["description"]

    def test_given_notification_then_no_response_is_sent(self, data):
        message = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        assert MCPServer(data).handle(message) is None

    def test_given_unknown_method_then_method_not_found_error(self, data):
        response = _rpc(MCPServer(data), "resources/list")
        assert response["error"]["code"] == -32601

    def test_given_malformed_json_then_parse_error_and_server_keeps_going(self, data):
        responses = _serve(data, "{not json", json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}))
        assert responses[0]["error"]["code"] == -32700
        assert responses[1] == {"jsonrpc": "2.0", "id": 2, "result": {}}


class TestToolCalls:
    def test_given_tools_call_then_result_is_text_content(self, data):
        response = _rpc(MCPServer(data), "tools/call", {
            "name": "standings", "arguments": {"season": 2019},
        })
        result = response["result"]
        assert result["isError"] is False
        assert result["content"][0]["type"] == "text"
        assert "Flamengo - 90 pts" in result["content"][0]["text"]

    def test_given_unknown_tool_then_is_error_flag_is_set(self, data):
        text, is_error = call_tool(data, "does_not_exist", {})
        assert is_error and "Unknown tool" in text

    def test_given_bad_team_name_then_user_facing_error_not_crash(self, data):
        text, is_error = call_tool(data, "team_stats", {"team": "Nope FC"})
        assert is_error and "no team matches" in text

    def test_given_missing_required_argument_then_invalid_arguments_error(self, data):
        text, is_error = call_tool(data, "head_to_head", {"team_a": "Flamengo"})
        assert is_error and "Invalid arguments" in text

    def test_given_bad_date_then_error_names_the_argument(self, data):
        text, is_error = call_tool(data, "find_matches", {"team": "Flamengo", "start_date": "2019/01/01"})
        assert is_error and "start_date" in text

    def test_given_find_matches_without_team_then_error(self, data):
        text, is_error = call_tool(data, "find_matches", {})
        assert is_error

    def test_given_head_to_head_then_answer_follows_spec_format(self, data):
        text, is_error = call_tool(data, "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"})
        assert not is_error
        assert text.startswith("Flamengo vs Fluminense:")
        assert "Head-to-head in dataset:" in text

    @pytest.mark.parametrize("name, args", [
        ("team_stats", {"team": "Corinthians", "season": 2022, "venue": "home"}),
        ("league_stats", {"include_biggest_wins": True}),
        ("best_away_records", {}),
        ("search_players", {"nationality": "Brazil", "limit": 3}),
        ("brazilian_players_by_club", {}),
    ])
    def test_given_each_tool_then_it_answers_without_error(self, data, name, args):
        text, is_error = call_tool(data, name, args)
        assert not is_error, text
        assert text
