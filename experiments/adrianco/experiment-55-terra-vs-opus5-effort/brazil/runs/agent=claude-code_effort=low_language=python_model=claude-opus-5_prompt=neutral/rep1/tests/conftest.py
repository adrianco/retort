"""
Context
=======
Shared pytest fixtures.

The real CSV corpus is loaded exactly once per test session (`graph` fixture,
session-scoped) because parsing all six files takes ~1s and every scenario reads
the same immutable graph.  Tests that need a hand-built corpus use `tiny_graph`,
which exercises the same code paths against data whose expected answers can be
worked out by hand.

`server_call` dispatches through brazilian_soccer.server.dispatch -- the exact
entry point the MCP transport uses -- so the behaviour tests cover the tool layer
and not just the library underneath it.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brazilian_soccer import KnowledgeGraph, load_default_graph  # noqa: E402
from brazilian_soccer.loader import DEFAULT_DATA_DIR, deduplicate  # noqa: E402
from brazilian_soccer.models import BRASILEIRAO_A, COPA_DO_BRASIL, Match, Player  # noqa: E402
from brazilian_soccer.names import DisplayNames  # noqa: E402
from brazilian_soccer.server import dispatch  # noqa: E402


@pytest.fixture(scope="session")
def graph() -> KnowledgeGraph:
    """The full knowledge graph over the six provided datasets."""
    if not DEFAULT_DATA_DIR.exists():
        pytest.skip(f"dataset directory missing: {DEFAULT_DATA_DIR}")
    return load_default_graph()


@pytest.fixture
def server_call(graph):
    """Call an MCP tool the same way the stdio server does."""
    def _call(tool: str, **arguments):
        return dispatch(tool, arguments, graph=graph)
    return _call


def make_match(
    home, away, home_goals, away_goals, *,
    competition=BRASILEIRAO_A, season=2020, day=1, month=1,
    source="test", **extra,
) -> Match:
    """Build a Match from raw (un-normalised) team names, as a loader would."""
    names = extra.pop("names", None) or DisplayNames()
    home_key, away_key = names.observe(home), names.observe(away)
    return Match(
        competition=competition,
        season=season,
        match_date=date(season, month, day),
        home_team=home_key,
        away_team=away_key,
        home_display=names.display(home_key),
        away_display=names.display(away_key),
        home_goals=home_goals,
        away_goals=away_goals,
        source=source,
        **extra,
    )


@pytest.fixture
def tiny_graph() -> KnowledgeGraph:
    """A four-team mini-league whose every statistic is checkable by hand.

    Alpha:  W vs Beta (3-1 H), W vs Gama (2-0 A), D vs Delta (1-1 H)
            -> 2W 1D 0L, GF 6, GA 2, 7 pts
    """
    names = DisplayNames()
    rows = [
        ("Alpha-SP", "Beta-RJ", 3, 1, 3, 5),
        ("Gama-MG", "Alpha-SP", 0, 2, 3, 12),
        ("Alpha-SP", "Delta-BA", 1, 1, 3, 19),
        ("Beta-RJ", "Gama-MG", 2, 2, 4, 2),
        ("Delta-BA", "Beta-RJ", 0, 4, 4, 9),
        ("Gama-MG", "Delta-BA", 1, 0, 4, 16),
    ]
    matches = [
        make_match(h, a, hg, ag, month=mo, day=d, names=names, round=str(i + 1))
        for i, (h, a, hg, ag, mo, d) in enumerate(rows)
    ]
    # One cup tie so competition filtering has something to separate.
    matches.append(
        make_match("Alpha", "Beta", 0, 1, competition=COPA_DO_BRASIL,
                   season=2020, month=6, day=1, names=names, stage="final")
    )
    players = [
        Player(1, "Ana Silva", 24, "Brazil", 82, 88, "Alpha-SP",
               names.observe("Alpha-SP"), "ST", "9", "5'11", "165lbs",
               "€30M", "€50K", "Right", {"Finishing": 85}),
        Player(2, "Bruno Costa", 31, "Brazil", 75, 75, "Beta-RJ",
               names.observe("Beta-RJ"), "GK", "1", "6'2", "180lbs",
               "€8M", "€20K", "Right", {"GKReflexes": 78}),
        Player(3, "Carlos Ruiz", 27, "Argentina", 79, 80, "Alpha-SP",
               names.observe("Alpha-SP"), "CB", "4", "6'0", "175lbs",
               "€15M", "€30K", "Left", {"Marking": 80}),
    ]
    return KnowledgeGraph(deduplicate(matches), players, names, {"test": len(matches)})
