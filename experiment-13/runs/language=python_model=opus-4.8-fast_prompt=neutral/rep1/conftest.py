"""
Shared pytest fixtures for the Brazilian Soccer MCP test suite.

The KnowledgeGraph (which parses ~40k match rows and 18k players) is expensive
to build, so it is constructed once per test session and shared read-only.
"""

import pytest

from knowledge_graph import KnowledgeGraph


@pytest.fixture(scope="session")
def kg() -> KnowledgeGraph:
    return KnowledgeGraph()
