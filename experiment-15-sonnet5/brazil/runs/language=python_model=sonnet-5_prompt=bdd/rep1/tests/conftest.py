"""Shared BDD fixtures: the full dataset is loaded once per test session
(it's fast - well under a second) and reused by every test module.
"""

import pytest

from brazilian_soccer_mcp.data_loader import load_all
from brazilian_soccer_mcp.graph import KnowledgeGraph
from brazilian_soccer_mcp.queries import QueryEngine


@pytest.fixture(scope="session")
def soccer_data():
    return load_all()


@pytest.fixture(scope="session")
def matches_df(soccer_data):
    return soccer_data.matches


@pytest.fixture(scope="session")
def players_df(soccer_data):
    return soccer_data.players


@pytest.fixture(scope="session")
def graph(soccer_data):
    return KnowledgeGraph(soccer_data.matches, soccer_data.players)


@pytest.fixture(scope="session")
def engine(graph):
    return QueryEngine(graph)
