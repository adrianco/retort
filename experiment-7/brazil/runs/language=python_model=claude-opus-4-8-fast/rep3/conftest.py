"""
================================================================================
Context
================================================================================
Module:   conftest.py
Project:  Brazilian Soccer MCP Server
Purpose:  Shared pytest fixtures.  The full knowledge graph is loaded once per
          test session (it is read-only) and reused across every test, keeping
          the BDD suite fast while exercising the real datasets.

Dependencies: pytest, knowledge_graph.
================================================================================
"""

from __future__ import annotations

import pytest

from knowledge_graph import KnowledgeGraph


@pytest.fixture(scope="session")
def kg() -> KnowledgeGraph:
    """The Given for most scenarios: 'the match data is loaded'."""
    return KnowledgeGraph.load()
