"""
================================================================================
Feature: MCP server protocol
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
BDD tests for the JSON-RPC/MCP wire layer: initialize handshake, tools/list,
tools/call dispatch and in-band error reporting, plus an end-to-end stdio round
trip. Also asserts query-performance budgets from the Success Criteria.
================================================================================
"""

import io
import json
import time

from mcp_server import MCPServer, resolve_competition, TOOLS
from data_loader import SERIE_A, LIBERTADORES


class TestInitialize:
    def test_initialize_returns_capabilities(self, server):
        # Given an MCP client
        # When it sends `initialize`
        resp = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                              "params": {}})
        # Then the server advertises its name, version and tool capability
        assert resp["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"
        assert "tools" in resp["result"]["capabilities"]

    def test_initialized_notification_has_no_response(self, server):
        # Given the `notifications/initialized` notification (no id)
        # Then the server returns nothing (notifications must not be answered)
        assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


class TestToolsList:
    def test_lists_all_tools_with_schemas(self, server):
        # When the client asks for the tool list
        resp = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = resp["result"]["tools"]
        # Then all registered tools are present with input schemas
        assert len(tools) == len(TOOLS)
        for t in tools:
            assert t["name"] and t["description"]
            assert t["inputSchema"]["type"] == "object"


class TestToolsCall:
    def test_standings_tool(self, server):
        # When the client calls the standings tool for 2019
        resp = server.handle({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "standings",
                       "arguments": {"competition": "Brasileirao", "season": 2019}},
        })
        text = resp["result"]["content"][0]["text"]
        # Then the rendered table names Flamengo as champion
        assert resp["result"]["isError"] is False
        assert "Flamengo" in text and "Champion" in text

    def test_find_matches_tool(self, server):
        resp = server.handle({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "find_matches",
                       "arguments": {"team": "Flamengo", "opponent": "Fluminense"}},
        })
        text = resp["result"]["content"][0]["text"]
        assert "Flamengo" in text and "Fluminense" in text

    def test_tool_error_is_in_band(self, server):
        # Given a tool call for a non-existent team
        resp = server.handle({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "team_record", "arguments": {"team": "No Such Club"}},
        })
        # Then the error is reported in-band with isError=True (not a JSON-RPC error)
        assert resp["result"]["isError"] is True
        assert "Error" in resp["result"]["content"][0]["text"]

    def test_unknown_method_returns_jsonrpc_error(self, server):
        resp = server.handle({"jsonrpc": "2.0", "id": 6, "method": "no/such/method"})
        assert resp["error"]["code"] == -32601


class TestCompetitionResolution:
    def test_aliases_resolve(self):
        assert resolve_competition("Brasileirao") == SERIE_A
        assert resolve_competition("serie a") == SERIE_A
        assert resolve_competition("Libertadores") == LIBERTADORES


class TestStdioRoundTrip:
    def test_end_to_end_over_stdio(self, server):
        # Given a newline-delimited JSON-RPC request stream
        requests = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                        "params": {"name": "list_competitions", "arguments": {}}}),
        ]) + "\n"
        stdin, stdout = io.StringIO(requests), io.StringIO()
        # When the server processes the stream over stdio
        server.serve(stdin=stdin, stdout=stdout)
        # Then it emits exactly two responses (the notification is silent)
        lines = [l for l in stdout.getvalue().splitlines() if l.strip()]
        assert len(lines) == 2
        last = json.loads(lines[-1])
        assert "Copa Libertadores" in last["result"]["content"][0]["text"]


class TestPerformance:
    """Success Criteria > Query Performance."""

    def test_simple_lookup_under_2s(self, server):
        start = time.perf_counter()
        server.call_tool("head_to_head", {"team_a": "Flamengo", "team_b": "Corinthians"})
        assert time.perf_counter() - start < 2.0

    def test_aggregate_query_under_5s(self, server):
        start = time.perf_counter()
        server.call_tool("standings", {"competition": "Brasileirao", "season": 2019})
        server.call_tool("best_record", {"venue": "home", "competition": "Brasileirao"})
        assert time.perf_counter() - start < 5.0
