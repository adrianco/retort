"""Shared pytest fixtures.

A single knowledge graph is built once per test session (loading the CSVs is
the expensive part) and shared across all scenarios.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brazilian_soccer_mcp import SoccerKnowledgeGraph  # noqa: E402


@pytest.fixture(scope="session")
def graph() -> SoccerKnowledgeGraph:
    return SoccerKnowledgeGraph.from_data_dir()
