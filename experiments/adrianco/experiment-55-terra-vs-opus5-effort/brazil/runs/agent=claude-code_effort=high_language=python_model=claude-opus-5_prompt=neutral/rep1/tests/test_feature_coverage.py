"""Keeps the Gherkin feature files and the executable scenarios in step.

Context
-------
``tests/features/*.feature`` is the human-readable specification of behaviour;
the modules in ``tests/bdd`` (and ``test_mcp_server.py`` for the protocol
feature) are its executable counterpart.  Documentation that silently drifts
away from the tests is worse than no documentation, so this module asserts that
every declared scenario still has a test carrying the same name.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

import pytest

FEATURES_DIR = Path(__file__).parent / "features"

#: Which module implements each feature file.
IMPLEMENTED_BY = {
    "match_queries": "bdd/test_match_queries.py",
    "team_queries": "bdd/test_team_queries.py",
    "player_queries": "bdd/test_player_queries.py",
    "competition_queries": "bdd/test_competition_queries.py",
    "statistics": "bdd/test_statistics.py",
    "mcp_protocol": "test_mcp_server.py",
}

_SCENARIO_RE = re.compile(r"^\s*Scenario:\s*(.+)$", re.MULTILINE)
_TEST_RE = re.compile(r"^def (test_\w+)", re.MULTILINE)


def _normalise(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def _scenarios() -> list[tuple[str, str]]:
    pairs = []
    for feature in sorted(FEATURES_DIR.glob("*.feature")):
        for scenario in _SCENARIO_RE.findall(feature.read_text(encoding="utf-8")):
            pairs.append((feature.stem, scenario.strip()))
    return pairs


def test_every_feature_file_has_an_implementing_module():
    stems = {feature.stem for feature in FEATURES_DIR.glob("*.feature")}
    assert stems == set(IMPLEMENTED_BY)
    for path in IMPLEMENTED_BY.values():
        assert (Path(__file__).parent / path).is_file(), path


@pytest.mark.parametrize("feature,scenario", _scenarios(),
                         ids=[f"{f}:{s[:40]}" for f, s in _scenarios()])
def test_every_scenario_has_a_test(feature, scenario):
    module = (Path(__file__).parent / IMPLEMENTED_BY[feature])
    tests = _TEST_RE.findall(module.read_text(encoding="utf-8"))
    candidates = {_normalise(name.removeprefix("test_")): name for name in tests}
    target = _normalise(scenario)
    best = difflib.get_close_matches(target, list(candidates), n=1, cutoff=0.6)
    assert best, (
        f"No test in {IMPLEMENTED_BY[feature]} implements scenario "
        f"{scenario!r}. Tests present: {sorted(candidates.values())}")


def test_the_suite_covers_every_specification_category():
    """The five required capability categories each have a feature file."""
    stems = {feature.stem for feature in FEATURES_DIR.glob("*.feature")}
    assert {"match_queries", "team_queries", "player_queries",
            "competition_queries", "statistics"} <= stems
