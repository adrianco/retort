"""Shared fixtures for the Brazilian soccer test suite.

Context
-------
Two kinds of fixture:

* ``queries`` / ``graph`` -- the *real* graph over ``data/kaggle`` built once
  per session (~0.4 s).  Used by the behaviour tests, so they assert against the
  data the spec actually ships.
* ``tiny_graph`` -- a hand-written five-match graph used where a deterministic,
  fully-known dataset makes the assertion clearer (de-duplication, standings
  arithmetic, edge cases).

The tests are written in Gherkin Given/When/Then order, with the step spelled
out in a comment on each block so the scenario reads top to bottom.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brazilian_soccer.graph import KnowledgeGraph, load_default_graph  # noqa: E402
from brazilian_soccer.loader import DEFAULT_DATA_DIR  # noqa: E402
from brazilian_soccer.models import BRASILEIRAO, COPA_DO_BRASIL, Match  # noqa: E402
from brazilian_soccer.queries import SoccerQueries  # noqa: E402

DATA_DIR = DEFAULT_DATA_DIR


@pytest.fixture(scope="session")
def data_dir() -> Path:
    if not DATA_DIR.exists():  # pragma: no cover - defensive
        pytest.skip(f"dataset directory {DATA_DIR} is missing")
    return DATA_DIR


@pytest.fixture(scope="session")
def graph(data_dir: Path) -> KnowledgeGraph:
    """The real knowledge graph, built once for the whole session."""
    return load_default_graph(data_dir)


@pytest.fixture(scope="session")
def queries(graph: KnowledgeGraph) -> SoccerQueries:
    return SoccerQueries(graph)


def _match(
    home: str,
    away: str,
    home_goals: int,
    away_goals: int,
    day: int,
    competition: str = BRASILEIRAO,
    season: int = 2020,
    source: str = "test",
    **kwargs,
) -> Match:
    """Build a Match through the normal loader path (keys get normalised)."""
    from brazilian_soccer.loader import _make_match

    return _make_match(
        competition=competition,
        season=season,
        match_date=date(season, 5, day),
        home_raw=home,
        away_raw=away,
        home_goals=home_goals,
        away_goals=away_goals,
        source=source,
        **kwargs,
    )


@pytest.fixture()
def tiny_graph() -> KnowledgeGraph:
    """A deterministic three-team league plus one cup tie.

    Alpha: beat Beta 2-0 (H), lost 1-3 at Gamma  -> 3 pts, GF 3 GA 3
    Beta:  lost 0-2 at Alpha, drew 1-1 with Gamma -> 1 pt,  GF 1 GA 3
    Gamma: beat Alpha 3-1 (H), drew 1-1 at Beta   -> 4 pts, GF 4 GA 2
    """
    matches = [
        _match("Alpha-SP", "Beta-RJ", 2, 0, day=1),
        _match("Gamma-MG", "Alpha-SP", 3, 1, day=2),
        _match("Beta-RJ", "Gamma-MG", 1, 1, day=3),
        # Same fixture as the first row, arriving from a second source file
        # with a slightly different spelling and a different date.
        _match("Alpha", "Beta", 2, 0, day=8, source="other"),
        _match(
            "Alpha-SP",
            "Gamma-MG",
            1,
            0,
            day=20,
            competition=COPA_DO_BRASIL,
            stage="final",
        ),
    ]
    return KnowledgeGraph.build([m for m in matches if m])


@pytest.fixture()
def tiny_queries(tiny_graph: KnowledgeGraph) -> SoccerQueries:
    return SoccerQueries(tiny_graph)
