"""
================================================================================
Module: conftest.py  (pytest root configuration + shared fixtures)
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Context
-------
Lives at the repo root so pytest puts the repo root on ``sys.path`` (prepend
import mode), letting the test modules import the top-level package modules
(``normalize``, ``data_loader``, ``knowledge_graph``, ``mcp_server``).

Provides the expensive, read-only fixtures shared across the whole BDD suite:
the loaded ``SoccerGraph`` and an ``MCPServer`` wrapping it. Both are
session-scoped because the underlying data never mutates, so we load the CSVs
exactly once for the entire test run.
================================================================================
"""

import pytest

from data_loader import load_dataset
from knowledge_graph import SoccerGraph
from mcp_server import MCPServer


@pytest.fixture(scope="session")
def dataset():
    """The raw loaded dataset (all six CSVs), loaded once per session."""
    return load_dataset()


@pytest.fixture(scope="session")
def graph(dataset):
    """The knowledge-graph query engine over the loaded dataset."""
    return SoccerGraph(dataset)


@pytest.fixture(scope="session")
def server(graph):
    """An MCP server sharing the session graph (no reload)."""
    return MCPServer(graph=graph)
