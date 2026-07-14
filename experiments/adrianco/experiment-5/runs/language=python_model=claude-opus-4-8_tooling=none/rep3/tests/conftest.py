# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : tests.conftest
# Purpose : Shared pytest fixtures. The KnowledgeGraph is expensive-ish to build
#           (parses ~24k rows) so it is loaded once per test session and shared
#           read-only across all BDD scenarios.
# =============================================================================

import os
import sys

import pytest

# Make the package importable when tests are run from any working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soccer_mcp.knowledge_graph import KnowledgeGraph  # noqa: E402


@pytest.fixture(scope="session")
def graph() -> KnowledgeGraph:
    """A fully-loaded knowledge graph (Given: the data is loaded)."""
    return KnowledgeGraph.load()
