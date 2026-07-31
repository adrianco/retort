"""Shared fixtures.

Context
-------
The whole suite is written Given/When/Then; each test carries the Gherkin
scenario it implements in its docstring.

Building the knowledge graph reads six CSVs (~1s), so it is a session scoped
fixture shared by every test.  Tests must therefore treat it as read-only.
``call_tool`` drives the real MCP server so the tool layer is covered end to end
without needing pytest-asyncio -- ``anyio.run`` is enough.
"""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest

from brazilian_soccer.graph import KnowledgeGraph
from brazilian_soccer.loaders import default_data_dir
from brazilian_soccer.server import build_server

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Directory holding the six Kaggle CSVs."""
    directory = default_data_dir()
    if not directory.exists():  # pragma: no cover - data ships with the repo
        pytest.skip(f"Kaggle data directory not found: {directory}")
    return directory


@pytest.fixture(scope="session")
def graph(data_dir: Path) -> KnowledgeGraph:
    """The knowledge graph, built once for the whole session (read-only)."""
    return KnowledgeGraph.load(data_dir)


@pytest.fixture(scope="session")
def server(graph: KnowledgeGraph):
    """An MCP server bound to the shared graph."""
    return build_server(graph=graph)


@pytest.fixture(scope="session")
def call_tool(server):
    """Call an MCP tool and return its text content."""

    def _call(tool_name: str, /, **arguments):
        # positional-only so a tool argument called "name" cannot collide
        async def _run():
            return await server.call_tool(tool_name, arguments)

        result = anyio.run(_run)
        return "\n".join(
            block.text for block in result.content if getattr(block, "text", None)
        )

    return _call
