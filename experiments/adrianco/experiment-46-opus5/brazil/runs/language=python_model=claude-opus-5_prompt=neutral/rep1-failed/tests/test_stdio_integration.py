"""Feature: The server really speaks MCP over stdio.

  Scenario: A client connects, lists tools, calls one and reads a resource
    Given the server started as a subprocess
    When an MCP client drives it over stdio
    Then the handshake, tool list, tool call and resource read all succeed

This is the only test that starts a real process; everything else calls the
tool functions directly.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HANDSHAKE_TIMEOUT = 60


async def _drive_server() -> dict:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "brazilian_soccer.server"],
        cwd=str(PROJECT_ROOT),
        env=environment,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            standings = await session.call_tool(
                "standings", {"competition": "Brasileirão", "season": 2019})
            unknown = await session.call_tool(
                "team_statistics", {"team": "Nonexistent United"})
            resources = await session.list_resources()
            overview = await session.read_resource("soccer://overview")
            return {
                "server_name": init.serverInfo.name,
                "instructions": init.instructions or "",
                "tools": [tool.name for tool in tools.tools],
                "standings": standings.content[0].text,
                "unknown": unknown.content[0].text,
                "resources": [str(resource.uri) for resource in resources.resources],
                "overview": overview.contents[0].text,
            }


@pytest.fixture(scope="module")
def session_result() -> dict:
    return asyncio.run(asyncio.wait_for(_drive_server(), HANDSHAKE_TIMEOUT))


def test_handshake_reports_the_server_identity(session_result):
    assert session_result["server_name"] == "brazilian-soccer"
    assert "Brasileirão" in session_result["instructions"]


def test_tools_are_listed_over_the_protocol(session_result):
    assert len(session_result["tools"]) >= 20
    assert "standings" in session_result["tools"]
    assert "search_matches" in session_result["tools"]


def test_tool_call_returns_the_answer(session_result):
    text = session_result["standings"]

    assert "1. Flamengo - 90 pts" in text
    assert "Champion" in text


def test_bad_input_is_answered_not_raised(session_result):
    assert "No team matching" in session_result["unknown"]


def test_resources_are_readable(session_result):
    assert "soccer://overview" in session_result["resources"]
    assert "Knowledge graph:" in session_result["overview"]
