"""Interop check with the official MCP Python SDK client (skipped when the ``mcp`` package is absent)."""

import asyncio
import sys
from pathlib import Path

import pytest

mcp = pytest.importorskip("mcp")
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


async def _session_roundtrip():
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("standings", {"season": 2019, "top": 1})
            return init, tools, result


def _attr(obj, *names):
    """SDK 1.x uses camelCase attributes, 2.x snake_case."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    raise AttributeError(names)


def test_official_sdk_client_can_use_server():
    init, tools, result = asyncio.run(_session_roundtrip())
    assert _attr(init, "server_info", "serverInfo").name == "brazilian-soccer"
    assert {"search_matches", "standings", "search_players"} <= {t.name for t in tools.tools}
    assert not _attr(result, "is_error", "isError")
    assert "Flamengo - 90 pts" in result.content[0].text
