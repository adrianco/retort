"""
End-to-end tests of the MCP server.

Context
-------
These drive the real server through the MCP SDK's in-process client, so they
exercise the whole path an LLM client takes: ``initialize``, ``tools/list``,
``tools/call``, ``resources/read`` and ``prompts/get``.  Anything that passes
here behaves the same over stdio.

The client is opened inside each test rather than in a fixture on purpose: the
SDK's session is built on anyio cancel scopes, which must be entered and exited
in the same task, and a yielding async fixture finalises in a different one.
"""

from __future__ import annotations

import json

import pytest
from mcp import Client

from brazilian_soccer.graph import load_knowledge_graph
from brazilian_soccer.server import annotate_tool_schemas, server
from brazilian_soccer.tools import tool_names


@pytest.fixture(scope="module", autouse=True)
def warm_server_graph():
    """The server uses the process-wide cached graph -- build it up front."""

    load_knowledge_graph()


def connect() -> Client:
    return Client(server, raise_exceptions=True)


async def test_server_advertises_every_tool():
    async with connect() as client:
        tools = (await client.list_tools()).tools
    assert {tool.name for tool in tools} == set(tool_names())


async def test_tool_schemas_document_their_arguments():
    async with connect() as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
    schema = tools["search_matches"].input_schema
    assert schema["type"] == "object"
    assert {"team", "opponent", "competition", "season", "limit"} <= set(schema["properties"])
    assert schema["properties"]["home_away"]["description"]
    assert tools["head_to_head"].input_schema["required"] == ["team_a", "team_b"]


async def test_every_tool_has_a_description():
    async with connect() as client:
        tools = (await client.list_tools()).tools
    for tool in tools:
        assert tool.description and len(tool.description) > 20


async def test_every_tool_answers_over_the_wire():
    """Call all 24 tools through the protocol, not just the Python layer."""

    from test_tools import MINIMAL_ARGUMENTS

    async with connect() as client:
        results = {
            name: await client.call_tool(name, arguments)
            for name, arguments in sorted(MINIMAL_ARGUMENTS.items())
        }
    for name, result in results.items():
        assert result.content, f"{name} returned no content"
        assert result.content[0].text.strip(), f"{name} returned an empty answer"


async def test_call_tool_returns_a_formatted_answer():
    async with connect() as client:
        result = await client.call_tool("competition_standings",
                                        {"competition": "brasileirao", "season": 2019})
    text = result.content[0].text
    assert "Flamengo" in text and "Champion" in text


async def test_call_tool_with_a_name_argument():
    """`player_profile(name=...)` must not collide with the dispatch helper."""

    async with connect() as client:
        result = await client.call_tool("player_profile", {"name": "Neymar"})
    assert "Neymar Jr" in result.content[0].text


async def test_search_players_by_position_group():
    async with connect() as client:
        result = await client.call_tool(
            "search_players", {"club": "Santos", "position": "forward", "limit": 5}
        )
    assert "Overall" in result.content[0].text


async def test_head_to_head_over_the_wire():
    async with connect() as client:
        result = await client.call_tool("head_to_head",
                                        {"team_a": "Grêmio", "team_b": "Internacional"})
    text = result.content[0].text
    assert "Grenal" in text
    assert "Head-to-head in dataset" in text


async def test_unknown_club_is_answered_not_raised():
    async with connect() as client:
        result = await client.call_tool("team_stats", {"team": "Real Madrid"})
    assert result.content[0].text.strip()


async def test_resources_are_listed_and_readable():
    async with connect() as client:
        listed = {str(resource.uri)
                  for resource in (await client.list_resources()).resources}
        payloads = {uri: (await client.read_resource(uri)).contents[0].text
                    for uri in sorted(listed)}
    assert listed == {
        "soccer://datasets", "soccer://competitions", "soccer://teams",
        "soccer://graph/schema",
    }
    for uri, body in payloads.items():
        assert json.loads(body), uri


async def test_dataset_resource_reports_every_csv():
    async with connect() as client:
        contents = (await client.read_resource("soccer://datasets")).contents
    payload = json.loads(contents[0].text)
    assert len(payload["datasets"]) == 6
    assert payload["report"]["missing_files"] == []


async def test_graph_schema_resource():
    async with connect() as client:
        contents = (await client.read_resource("soccer://graph/schema")).contents
    schema = json.loads(contents[0].text)
    assert schema["nodes"]["match"] > 10000
    assert schema["edges"]["home_team"] == schema["edges"]["away_team"]


async def test_prompts_are_available():
    async with connect() as client:
        prompts = {prompt.name for prompt in (await client.list_prompts()).prompts}
        rendered = await client.get_prompt("analyze_team", {"team": "Flamengo"})
    assert prompts == {"analyze_team", "season_review"}
    assert "Flamengo" in rendered.messages[0].content.text


async def test_server_instructions_warn_about_coverage():
    async with connect() as client:
        instructions = client.instructions
    assert instructions
    assert "unlicensed" in instructions


def test_schema_annotation_is_idempotent():
    """Re-running the annotation pass must not duplicate or clobber anything."""

    assert annotate_tool_schemas() == 0


def test_stdio_entry_point_serves_real_json_rpc(tmp_path):
    """Launch `python -m brazilian_soccer.server` and speak MCP over stdio."""

    import json as _json
    import subprocess
    import sys

    process = subprocess.Popen(
        [sys.executable, "-m", "brazilian_soccer.server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )

    def send(message: dict) -> None:
        process.stdin.write(_json.dumps(message) + "\n")
        process.stdin.flush()

    def receive() -> dict:
        line = process.stdout.readline()
        assert line, "server closed the connection"
        return _json.loads(line)

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "pytest", "version": "1"}}})
        initialized = receive()
        assert initialized["result"]["serverInfo"]["name"] == "brazilian-soccer"

        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert len(receive()["result"]["tools"]) == len(tool_names())

        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "competition_standings",
                         "arguments": {"competition": "brasileirao", "season": 2019}}})
        answer = receive()["result"]["content"][0]["text"]
        assert "1. Flamengo (RJ) - 90 pts" in answer
    finally:
        process.stdin.close()
        process.terminate()
        process.wait(timeout=30)
