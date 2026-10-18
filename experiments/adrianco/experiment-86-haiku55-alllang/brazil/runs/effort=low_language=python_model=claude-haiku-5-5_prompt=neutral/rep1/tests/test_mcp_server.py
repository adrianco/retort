# Context: Scenarios for the MCP protocol layer: initialize, tools/list, tools/call, error handling
# and the newline-delimited stdio loop. Drives the server through its public functions with
# in-memory streams, so no subprocess is needed.

import io
import json

from brazilian_soccer_mcp.server import SoccerTools, handle_message, serve


def _tools(kb) -> SoccerTools:
    return SoccerTools(kb)


def _call(tools, name, arguments):
    return handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
        tools,
    )


def test_given_a_client_when_it_initializes_then_the_server_advertises_tool_support(sample_kb):
    # Given an MCP client
    # When it sends initialize
    response = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, _tools(sample_kb))
    # Then the server reports the protocol version and tools capability
    assert response["result"]["capabilities"] == {"tools": {}}
    assert response["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"


def test_given_a_client_when_it_lists_tools_then_every_query_category_is_exposed(sample_kb):
    # Given the server is running
    # When the client lists tools
    response = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, _tools(sample_kb))
    # Then match, team, competition, statistics and player tools are all available
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert {"find_matches", "team_record", "head_to_head", "standings", "season_stats",
            "venue_ranking", "search_players", "list_players", "club_profile"} <= names
    for tool in response["result"]["tools"]:
        assert tool["inputSchema"]["type"] == "object"


def test_given_a_match_question_when_the_tool_is_called_then_a_formatted_answer_is_returned(sample_kb):
    # Given the match data is loaded
    # When the client calls find_matches for Palmeiras in 2023
    response = _call(_tools(sample_kb), "find_matches", {"team": "Palmeiras", "season": 2023})
    # Then the answer is text listing the matches, not an error
    result = response["result"]
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert result["content"][0]["text"].startswith("Matches found:")


def test_given_a_standings_question_when_the_tool_is_called_then_the_champion_is_named(sample_kb):
    # Given the 2023 results
    # When the client asks for the 2023 standings
    text = _call(_tools(sample_kb), "standings", {"season": 2023})["result"]["content"][0]["text"]
    # Then the leader is shown as champion
    assert "1. Palmeiras (SP) - 8 pts" in text
    assert "Champion" in text


def test_given_an_unknown_tool_when_called_then_an_error_result_is_returned_not_a_crash(sample_kb):
    # Given a tool name the server does not have
    # When the client calls it
    response = _call(_tools(sample_kb), "does_not_exist", {})
    # Then the result is flagged as an error with a readable message
    assert response["result"]["isError"] is True
    assert "Unknown tool" in response["result"]["content"][0]["text"]


def test_given_a_missing_required_argument_when_called_then_an_error_result_is_returned(sample_kb):
    # Given a tool that needs a team name
    # When the client omits it
    response = _call(_tools(sample_kb), "team_record", {})
    # Then the result is an error, not a server failure
    assert response["result"]["isError"] is True


def test_given_an_unknown_method_when_received_then_a_method_not_found_error_is_returned(sample_kb):
    # Given a JSON-RPC request for a method the server lacks
    # When it is handled
    response = handle_message({"jsonrpc": "2.0", "id": 9, "method": "bogus"}, _tools(sample_kb))
    # Then a standard -32601 error is returned for that id
    assert response["id"] == 9
    assert response["error"]["code"] == -32601


def test_given_a_notification_when_received_then_no_response_is_sent(sample_kb):
    # Given the client's initialized notification (no id)
    # When it is handled
    # Then no reply is produced
    assert handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}, _tools(sample_kb)) is None


def test_given_a_stream_with_bad_json_when_served_then_the_server_recovers_for_the_next_request(sample_kb):
    # Given a stdin stream with a malformed line followed by a valid request
    stdin = io.StringIO(
        "not json\n"
        + json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ping"}) + "\n"
    )
    stdout = io.StringIO()
    # When the server processes the stream
    serve(stdin, stdout, _tools(sample_kb))
    # Then it reports a parse error and still answers the valid request
    replies = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert replies[0]["error"]["code"] == -32700
    assert replies[1] == {"jsonrpc": "2.0", "id": 3, "result": {}}
