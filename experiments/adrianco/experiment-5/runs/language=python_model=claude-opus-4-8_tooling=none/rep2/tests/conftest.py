"""
Shared pytest fixtures for the Brazilian Soccer MCP test-suite.

Context
-------
Loading the six CSV datasets is moderately expensive, so the real knowledge
graph is built once per test session and shared (read-only) by every BDD
scenario.  A second, tiny hand-built fixture provides a deterministic dataset
for tests that assert exact numbers without depending on the bundled data.
"""

import datetime
import os
import sys

import pytest

# Make the project modules importable when pytest runs from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_loader import Player, _make_match  # noqa: E402
from knowledge_graph import KnowledgeGraph  # noqa: E402


@pytest.fixture(scope="session")
def kg():
    """The knowledge graph loaded from the bundled Kaggle datasets."""
    return KnowledgeGraph.load()


@pytest.fixture(scope="session")
def mini_kg():
    """A small, deterministic knowledge graph for exact-value assertions.

    A 3-team mini league plus a couple of players.  Team A clearly tops the
    table (2 wins), Team B draws/loses, Team C loses everything.
    """
    def d(s):
        return datetime.date.fromisoformat(s)

    def mk(date, home, away, hg, ag, rnd):
        return _make_match("Brasileirao", 2020, d(date), home, away, hg, ag,
                           source="mini", round_=rnd)

    matches = [
        mk("2020-01-01", "Team A", "Team B", 2, 0, "1"),
        mk("2020-01-08", "Team A", "Team C", 3, 1, "2"),
        mk("2020-01-15", "Team B", "Team C", 1, 1, "3"),
        mk("2020-01-22", "Team C", "Team B", 0, 4, "4"),
    ]
    players = [
        Player("1", "Star Brazilian", 25, "Brazil", 90, 92, "Team A", "ST"),
        Player("2", "Young Brazilian", 19, "Brazil", 70, 88, "Team A", "CM"),
        Player("3", "Foreign Keeper", 30, "Argentina", 85, 85, "Team B", "GK"),
    ]
    return KnowledgeGraph(matches, players)
