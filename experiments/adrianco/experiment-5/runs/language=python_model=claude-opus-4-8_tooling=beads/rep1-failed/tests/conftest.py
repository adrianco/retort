"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
File      : tests/conftest.py
Purpose   : Shared pytest fixtures for the BDD (Given/When/Then) test suite.

Provides:
  * `kg`  - a session-scoped KnowledgeGraph loaded once from the real datasets in
            data/kaggle/ (fast: built once, reused by every test).

The suite is written in a behaviour-driven style: each test reads as
Given (setup/fixture) / When (call a query) / Then (assert the behaviour),
mirroring the Gherkin scenarios in the specification.
================================================================================
"""

import os
import sys

import pytest

# Make the package importable when pytest is run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brazilian_soccer.knowledge_graph import KnowledgeGraph  # noqa: E402


@pytest.fixture(scope="session")
def kg() -> KnowledgeGraph:
    """Given the full Brazilian soccer dataset is loaded into the knowledge graph."""
    return KnowledgeGraph()
