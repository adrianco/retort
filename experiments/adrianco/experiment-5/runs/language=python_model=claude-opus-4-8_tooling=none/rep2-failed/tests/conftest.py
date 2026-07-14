"""
Context
=======
Module: tests.conftest
Purpose: Shared pytest fixtures for the Brazilian Soccer MCP test-suite.

The whole CSV dataset is loaded once per test session (``graph`` fixture) since
parsing ~42k rows on every test would be wasteful and the graph is read-only.
Tests are written in BDD Given/When/Then style mirroring the scenarios in
TASK.md.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import KnowledgeGraph


@pytest.fixture(scope="session")
def graph() -> KnowledgeGraph:
    """GIVEN the full Brazilian soccer dataset is loaded into the graph."""
    return KnowledgeGraph.load()
