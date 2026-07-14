"""
================================================================================
Brazilian Soccer MCP Server :: tests/conftest
================================================================================

Context
-------
Shared pytest fixtures. The knowledge graph is expensive-ish to build (~0.5s for
~24k matches + 18k players) so it is constructed once per test session and shared
through a session-scoped fixture. The repo root is added to sys.path so the
`brazilian_soccer` package imports without installation.
================================================================================
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from brazilian_soccer import KnowledgeGraph, QueryEngine  # noqa: E402


@pytest.fixture(scope="session")
def graph():
    return KnowledgeGraph.from_data_dir()


@pytest.fixture(scope="session")
def engine(graph):
    return QueryEngine(graph)
