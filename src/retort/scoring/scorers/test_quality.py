"""Test quality scorer — rewards BDD tests over plain unit tests.

Detects BDD test frameworks and applies a bonus:
  0.15 if BDD tests are present
  0.25 if BDD tests are present but TASK.md gave no BDD hints (unprompted)
"""

from __future__ import annotations

import re
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig


_BDD_TASK_KEYWORDS = re.compile(
    r"\b(BDD|behave|cucumber|feature file|Given|When|Then|scenario|pytest-bdd)\b"
)

_BDD_IMPORT_RE = re.compile(
    r"\b(behave|pytest[-_]bdd|cucumber|JBehave)\b"
)

_TS_BDD_RE = re.compile(
    r"\b(Given|When|Then)\s*\("
)


def _has_bdd_tests(output_dir: Path) -> bool:
    """Return True if any BDD test artifacts are found in output_dir."""
    # Feature files
    if any(output_dir.rglob("*.feature")):
        return True

    # Step definition directories
    for step_dir in ("steps", "step_defs"):
        if any(output_dir.rglob(f"{step_dir}/*.py")):
            return True

    # conftest.py with given/when/then
    for conftest in output_dir.rglob("conftest.py"):
        text = conftest.read_text(errors="replace").lower()
        if any(kw in text for kw in ("@given", "@when", "@then")):
            return True

    # Python files importing BDD frameworks
    for py_file in output_dir.rglob("*.py"):
        try:
            text = py_file.read_text(errors="replace")
        except OSError:
            continue
        if _BDD_IMPORT_RE.search(text):
            return True

    # TypeScript: describe/it blocks with Given/When/Then calls
    for ts_file in output_dir.rglob("*.ts"):
        try:
            text = ts_file.read_text(errors="replace")
        except OSError:
            continue
        if _TS_BDD_RE.search(text):
            return True

    return False


def _task_md_has_bdd_hints(output_dir: Path) -> bool:
    """Return True if TASK.md contains BDD-related keywords."""
    task_md = output_dir / "TASK.md"
    if not task_md.exists():
        return False
    try:
        text = task_md.read_text(errors="replace")
    except OSError:
        return False
    return bool(_BDD_TASK_KEYWORDS.search(text))


class TestQualityScorer:
    """Scores test quality, rewarding BDD tests over plain unit tests.

    Score range: 0.0 (no tests / failed run) to 1.0.
    """

    @property
    def name(self) -> str:
        return "test_quality"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if not artifacts.succeeded:
            return 0.0
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0.0

        from retort.scoring.scorers.test_coverage import TestCoverageScorer

        base_score = TestCoverageScorer().score(artifacts, stack)

        if not _has_bdd_tests(artifacts.output_dir):
            return base_score

        if _task_md_has_bdd_hints(artifacts.output_dir):
            bdd_bonus = 0.15
        else:
            bdd_bonus = 0.25

        return min(1.0, base_score + bdd_bonus)
