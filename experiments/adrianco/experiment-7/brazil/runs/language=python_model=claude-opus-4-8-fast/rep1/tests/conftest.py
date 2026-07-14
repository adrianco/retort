"""
================================================================================
tests.conftest
================================================================================

CONTEXT
-------
Shared pytest fixtures for the Brazilian Soccer MCP test-suite.

The whole suite follows a BDD / Given-When-Then style: each test reads as a
scenario where the *Given* is the loaded KnowledgeGraph fixture, the *When* is a
query method call, and the *Then* is the assertion block.

The KnowledgeGraph (which loads ~16k matches and ~18k players from the bundled
CSVs) is built once per test session for speed.
================================================================================
"""

import os
import sys

import pytest

# Make the package importable when tests are run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brazilian_soccer_mcp.knowledge_graph import KnowledgeGraph  # noqa: E402


@pytest.fixture(scope="session")
def kg() -> KnowledgeGraph:
    """Given: the full Brazilian soccer knowledge graph is loaded from the CSVs."""
    return KnowledgeGraph.load()
