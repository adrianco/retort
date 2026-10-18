"""Scenarios for the MCP JSON-RPC layer, driven through handle_message and serve."""

import io
import json
import unittest
from pathlib import Path

from brazil_soccer_mcp.dataset import Dataset
from brazil_soccer_mcp.server import TOOLS, Tools, handle_message, serve

from .helpers import match, player


def make_tools() -> Tools:
    matches = [
        match("2023-09-03", "Flamengo", "Fluminense", 2, 1, season=2023),
        match("2023-05-28", "Fluminense", "Flamengo", 1, 0, season=2023),
        match("2023-04-01", "Palmeiras-SP", "Santos-SP", 3, 0, season=2023),
    ]
    players = [player(1, "Gabriel Barbosa", "Flamengo", 85)]
    return Tools(Dataset(matches, players))


def call(tools, name, arguments=None, msg_id=1):
    return handle_message(
        tools,
        {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}},
    )


class ProtocolHandshake(unittest.TestCase):
    def test_initialize_reports_server_and_tool_capability(self):
        """Given a client, when it initializes, the server advertises tool support."""
        response = handle_message(make_tools(), {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertIn("tools", response["result"]["capabilities"])
        self.assertEqual(response["result"]["serverInfo"]["name"], "brazilian-soccer")

    def test_notifications_get_no_response(self):
        """Given a notification (no id), when it arrives, no response is written."""
        self.assertIsNone(handle_message(make_tools(), {"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_unknown_method_returns_json_rpc_error(self):
        """Given an unsupported method, the server returns JSON-RPC error -32601."""
        response = handle_message(make_tools(), {"jsonrpc": "2.0", "id": 2, "method": "resources/list"})
        self.assertEqual(response["error"]["code"], -32601)

    def test_tools_list_exposes_every_tool_with_a_schema(self):
        """Given a client, when it lists tools, each one has a name, description and input schema."""
        response = handle_message(make_tools(), {"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        names = {t["name"] for t in response["result"]["tools"]}
        self.assertIn("search_matches", names)
        self.assertIn("standings", names)
        for tool in TOOLS:
            self.assertEqual(tool["inputSchema"]["type"], "object")


class ToolCalls(unittest.TestCase):
    def test_search_matches_returns_formatted_answer(self):
        """Given a Flamengo vs Fluminense query, the answer lists matches in the spec's format."""
        response = call(make_tools(), "search_matches", {"team": "Flamengo", "opponent": "Fluminense"})
        text = response["result"]["content"][0]["text"]
        self.assertFalse(response["result"]["isError"])
        self.assertIn("- 2023-09-03: Flamengo 2-1 Fluminense", text)
        self.assertIn("Total matches in dataset: 2", text)

    def test_team_record_returns_win_rate(self):
        """Given Flamengo won one and lost one in 2023, the answer shows a 50% win rate."""
        response = call(make_tools(), "team_record", {"team": "Flamengo", "season": 2023})
        self.assertIn("Win rate: 50.0%", response["result"]["content"][0]["text"])

    def test_bad_date_is_reported_as_tool_error(self):
        """Given an unparseable date, the tool result is flagged isError rather than crashing."""
        response = call(make_tools(), "search_matches", {"team": "Flamengo", "start_date": "tomorrow"})
        self.assertTrue(response["result"]["isError"])
        self.assertIn("Unrecognized date", response["result"]["content"][0]["text"])

    def test_unknown_tool_is_reported_as_tool_error(self):
        """Given an unknown tool name, the result is an error the model can read."""
        response = call(make_tools(), "make_coffee")
        self.assertTrue(response["result"]["isError"])

    def test_standings_defaults_to_serie_a(self):
        """Given a season with no competition argument, standings use Série A."""
        response = call(make_tools(), "standings", {"season": 2023})
        self.assertIn("2023 Brasileirão Série A standings", response["result"]["content"][0]["text"])

    def test_player_search_returns_matching_player(self):
        """Given a name search, the player's overall rating and club are shown."""
        response = call(make_tools(), "search_players", {"name": "Gabriel"})
        text = response["result"]["content"][0]["text"]
        self.assertIn("Gabriel Barbosa - Overall: 85", text)


class StdioTransport(unittest.TestCase):
    def test_serve_handles_a_stream_of_requests(self):
        """Given newline-delimited JSON-RPC requests, serve writes one response per request."""
        lines = "\n".join(
            [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                "not json",
            ]
        )
        out = io.StringIO()
        serve(stdin=io.StringIO(lines), stdout=out, data_dir=Path(__file__).resolve().parent.parent / "data" / "kaggle")
        responses = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(responses[0]["id"], 1)
        self.assertEqual(responses[1]["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
