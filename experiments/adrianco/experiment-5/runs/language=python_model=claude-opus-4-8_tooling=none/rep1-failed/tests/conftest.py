"""
================================================================================
Brazilian Soccer MCP Server - Test Fixtures
================================================================================

CONTEXT
-------
Shared pytest fixtures for the BDD (Given-When-Then) suite.

Two kinds of fixtures are provided:

  * ``synthetic_kg`` - a tiny hand-built knowledge graph with fully known
    results, used for *exact* assertions (standings, head-to-head, stats).
  * ``kg`` (session scope) - the real knowledge graph loaded from the bundled
    ``data/kaggle`` CSV files, used for integration / smoke tests that assert
    structural properties and performance.

Tests that need the real data are skipped automatically when the CSV files are
absent so the suite still runs in a stripped checkout.
================================================================================
"""

import os
import sys

import pytest

# Make the package importable when tests run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brazilian_soccer_mcp import KnowledgeGraph, load_knowledge_graph  # noqa: E402
from brazilian_soccer_mcp.data_loader import DEFAULT_DATA_DIR  # noqa: E402
from brazilian_soccer_mcp.models import Match, Player  # noqa: E402
from brazilian_soccer_mcp.normalize import COMP_BRASILEIRAO  # noqa: E402


def _match(home, away, hg, ag, season=2023, comp=COMP_BRASILEIRAO,
           date=None, round_=None, source="synthetic"):
    return Match(
        competition=comp, season=season, date=date,
        home_team=home, away_team=away, home_goal=hg, away_goal=ag,
        round=round_, source=source,
    )


@pytest.fixture
def synthetic_kg():
    """A deterministic 3-team double round-robin plus a handful of players."""
    matches = [
        # Flamengo dominant, Santos bottom.
        _match("Flamengo-RJ", "Palmeiras-SP", 2, 0, date="2023-05-01", round_="1"),
        _match("Palmeiras-SP", "Flamengo-RJ", 1, 1, date="2023-09-01", round_="20"),
        _match("Flamengo-RJ", "Santos-SP", 3, 1, date="2023-05-08", round_="2"),
        _match("Santos-SP", "Flamengo-RJ", 0, 0, date="2023-09-08", round_="21"),
        _match("Palmeiras-SP", "Santos-SP", 2, 1, date="2023-05-15", round_="3"),
        _match("Santos-SP", "Palmeiras-SP", 1, 2, date="2023-09-15", round_="22"),
        # A different competition / season for filtering tests.
        _match("Flamengo", "Fluminense", 2, 1, season=2022,
               comp="Copa do Brasil", date="2022-07-01", source="synthetic_cup"),
    ]
    players = [
        Player(name="Neymar Jr", age=31, nationality="Brazil", overall=92,
               potential=92, club="Paris Saint-Germain", position="LW"),
        Player(name="Gabriel Barbosa", age=27, nationality="Brazil", overall=83,
               potential=85, club="Flamengo", position="ST"),
        Player(name="Pedro", age=26, nationality="Brazil", overall=80,
               potential=84, club="Flamengo", position="ST"),
        Player(name="Endrick", age=17, nationality="Brazil", overall=70,
               potential=90, club="Palmeiras", position="ST"),
        Player(name="Lionel Messi", age=36, nationality="Argentina", overall=91,
               potential=91, club="Inter Miami", position="RW"),
    ]
    return KnowledgeGraph(matches=matches, players=players)


def _data_available():
    return os.path.exists(os.path.join(DEFAULT_DATA_DIR, "Brasileirao_Matches.csv"))


@pytest.fixture(scope="session")
def kg():
    """The real knowledge graph loaded from bundled CSVs (session scoped)."""
    if not _data_available():
        pytest.skip("Bundled Kaggle CSV data not available")
    return load_knowledge_graph()


@pytest.fixture(scope="session")
def real_brasileirao_season(kg):
    """Pick a Brasileirão season that has a full-looking table for testing."""
    best = None
    for season in kg.seasons(COMP_BRASILEIRAO):
        table = kg.standings(season, COMP_BRASILEIRAO)
        if len(table) >= 16:  # a real top-flight season
            best = season
            break
    if best is None:
        pytest.skip("No complete Brasileirão season found in data")
    return best
