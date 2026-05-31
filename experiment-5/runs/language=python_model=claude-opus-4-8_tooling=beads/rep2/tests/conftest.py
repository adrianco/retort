"""
================================================================================
conftest.py - Shared pytest fixtures for the BDD test-suite
================================================================================

CONTEXT
-------
Provides a session-scoped, fully loaded :class:`QueryEngine` so every BDD
scenario shares one in-memory store (the "Given the data is loaded" step). The
store is read-only, so sharing it across tests is safe and keeps the suite fast.
================================================================================
"""

import pytest

from brazilian_soccer_mcp import QueryEngine, load_default_store


@pytest.fixture(scope="session")
def engine() -> QueryEngine:
    """Given: all six datasets are loaded into the query engine."""
    return QueryEngine(load_default_store())
