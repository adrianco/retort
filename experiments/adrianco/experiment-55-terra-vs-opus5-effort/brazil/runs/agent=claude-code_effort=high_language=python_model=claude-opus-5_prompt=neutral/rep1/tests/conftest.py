"""Shared pytest fixtures.

Context
-------
Building the knowledge graph reads ~24k match rows and 18k player rows.  That
takes under half a second, but doing it per test would still dominate the
suite, so the graph is built once per session and shared read-only.  Query
functions never mutate it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from brazilian_soccer.graph import KnowledgeGraph, load_graph  # noqa: E402
from brazilian_soccer.loaders import default_data_dir  # noqa: E402


@pytest.fixture(scope="session")
def data_dir() -> Path:
    directory = default_data_dir()
    if not directory.is_dir():
        pytest.skip(f"Kaggle data directory not found at {directory}")
    return directory


@pytest.fixture(scope="session")
def graph(data_dir: Path) -> KnowledgeGraph:
    """The shared, fully built knowledge graph."""
    return load_graph(data_dir)


@pytest.fixture(scope="session")
def server(graph: KnowledgeGraph):
    """An in-process MCP server wired to the shared graph."""
    from brazilian_soccer.server import MCPServer

    return MCPServer(graph=graph)
