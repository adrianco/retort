"""
================================================================================
 Test fixtures: shared knowledge graph & query engine
================================================================================
Context
-------
Loading all six datasets takes ~0.5s, so the knowledge graph is built once per
test session (``scope="session"``) and shared across every BDD scenario.  This
keeps the suite fast (well within the spec's < 2s simple / < 5s aggregate
targets) while still exercising the real, full datasets rather than fixtures.
================================================================================
"""

import pytest

from brazilian_soccer_mcp.knowledge_graph import KnowledgeGraph
from brazilian_soccer_mcp.queries import SoccerQueryEngine


@pytest.fixture(scope="session")
def graph() -> KnowledgeGraph:
    """The fully-loaded knowledge graph (all datasets)."""
    return KnowledgeGraph.from_data_dir()


@pytest.fixture(scope="session")
def engine(graph) -> SoccerQueryEngine:
    """The query engine wrapping the shared graph."""
    return SoccerQueryEngine(graph)
