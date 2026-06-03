"""
==============================================================================
File: conftest.py
==============================================================================
CONTEXT
-------
Shared pytest fixtures for the Brazilian Soccer test-suite. The full knowledge
graph is loaded ONCE per test session (session-scoped fixture) because loading
all six CSV files takes ~0.5s; re-loading per test would be wasteful. Tests are
written in BDD Given-When-Then style (see tests/).
==============================================================================
"""

import pytest

from brazilian_soccer.knowledge_graph import KnowledgeGraph


@pytest.fixture(scope="session")
def graph():
    """Given the full Brazilian soccer dataset is loaded into the graph."""
    return KnowledgeGraph.load()
