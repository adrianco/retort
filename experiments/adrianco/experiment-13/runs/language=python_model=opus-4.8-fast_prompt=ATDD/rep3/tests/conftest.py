"""
Pytest fixtures for the Brazilian Soccer MCP acceptance suite.

These fixtures connect to the System Under Test ONLY through the real MCP
protocol (a ``ClientSession`` talking JSON-RPC to the server over in-memory
streams). Tests never import the service or data layers directly -- they
exercise the published MCP tools exactly as an external LLM client would.
"""

import json
import os
import sys

import pytest
from anyio.from_thread import start_blocking_portal
from mcp.shared.memory import create_connected_server_and_client_session

# Make the project root importable so we can grab the server's MCP app object.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _structured(result):
    """Extract the domain payload from an MCP CallToolResult."""
    assert result.isError is False, f"tool returned an error: {result.content}"
    if result.structuredContent is not None:
        return result.structuredContent
    # Fall back to parsing the text content block as JSON.
    text = result.content[0].text
    return json.loads(text)


class SyncMCPClient:
    """A thin synchronous wrapper around an async MCP ClientSession."""

    def __init__(self, portal, session):
        self._portal = portal
        self._session = session

    def list_tools(self):
        result = self._portal.call(self._session.list_tools)
        return [t.name for t in result.tools]

    def call(self, _tool_name, /, **arguments):
        result = self._portal.call(self._session.call_tool, _tool_name, arguments)
        return _structured(result)

    def call_raw(self, _tool_name, /, **arguments):
        return self._portal.call(self._session.call_tool, _tool_name, arguments)


@pytest.fixture(scope="session")
def client():
    """A connected MCP client speaking the real protocol to the server."""
    from server import mcp  # imported lazily so unit tests need not load it

    with start_blocking_portal() as portal:
        cm = portal.wrap_async_context_manager(
            create_connected_server_and_client_session(mcp._mcp_server)
        )
        session = cm.__enter__()
        try:
            yield SyncMCPClient(portal, session)
        finally:
            cm.__exit__(None, None, None)
