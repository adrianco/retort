"""
================================================================================
Module: tests.conftest
--------------------------------------------------------------------------------
Context:
    Shared PyTest fixtures for the BDD (Given/When/Then) suite. Loading all six
    CSVs takes ~0.5s, so the knowledge graph is built once per test session and
    shared read-only across every scenario.

Responsibility:
    Provide the `graph` fixture (a loaded KnowledgeGraph) used as the "Given the
    match/player data is loaded" precondition throughout the feature tests.
================================================================================
"""

import sys
from pathlib import Path

import pytest

# Ensure the package is importable when running `pytest` from the repo root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brazilian_soccer_mcp import KnowledgeGraph  # noqa: E402


@pytest.fixture(scope="session")
def graph() -> KnowledgeGraph:
    """GIVEN the full Brazilian soccer dataset is loaded into the knowledge graph."""
    return KnowledgeGraph().load()
