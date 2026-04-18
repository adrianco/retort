"""Test quality scorer — detects BDD tests and rewards them over unit tests.

BDD tests (feature files, step definitions, framework imports) indicate
acceptance-level verification. Producing them unprompted signals the agent
understood intent, not just the letter of the task.
"""

from __future__ import annotations

import re
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig


_BDD_FRAMEWORK_RE = re.compile(
    r"\b(?:behave|pytest.bdd|cucumber|jbehave)\b", re.IGNORECASE
)

_GIVEN_WHEN_THEN_RE = re.compile(
    r"@(?:given|when|then)\b", re.IGNORECASE
)

_TS_BDD_FUNCTION_RE = re.compile(
    r'\b(?:Given|When|Then)\s*\(', re.MULTILINE
)

_BDD_TASK_KEYWORDS: frozenset[str] = frozenset([
    "bdd", "behave", "cucumber", "feature file",
    "given", "when", "then", "scenario", "pytest-bdd",
])


def _has_bdd_tests(output_dir: Path, language: str) -> bool:
    """Return True if the output directory contains BDD tests."""
    # Feature files (.feature) — language-agnostic
    if any(output_dir.rglob("*.feature")):
        return True

    # Python step-definition directories
    if any(output_dir.rglob("steps/*.py")) or any(output_dir.rglob("step_defs/*.py")):
        return True

    # conftest.py / Python test files using given/when/then decorators
    if language in ("python", ""):
        for py_file in output_dir.rglob("*.py"):
            try:
                text = py_file.read_text(errors="replace")
            except OSError:
                continue
            if _GIVEN_WHEN_THEN_RE.search(text):
                return True
            if _BDD_FRAMEWORK_RE.search(text):
                return True

    # TypeScript / JavaScript — describe/it blocks with Given/When/Then calls
    if language == "typescript":
        for ts_file in list(output_dir.rglob("*.ts")) + list(output_dir.rglob("*.tsx")):
            try:
                text = ts_file.read_text(errors="replace")
            except OSError:
                continue
            if _TS_BDD_FUNCTION_RE.search(text):
                return True

    # Java / Kotlin: JBehave or Cucumber imports
    if language in ("java", "kotlin"):
        for jf in list(output_dir.rglob("*.java")) + list(output_dir.rglob("*.kt")):
            try:
                text = jf.read_text(errors="replace")
            except OSError:
                continue
            if _BDD_FRAMEWORK_RE.search(text):
                return True

    return False


def _unprompted_bdd(output_dir: Path) -> bool:
    """Return True if TASK.md does not mention BDD, meaning BDD was agent initiative."""
    task_md = output_dir / "TASK.md"
    if not task_md.exists():
        return True
    try:
        text = task_md.read_text(errors="replace").lower()
    except OSError:
        return True
    return not any(kw in text for kw in _BDD_TASK_KEYWORDS)


class TestQualityScorer:
    """Scores test quality, rewarding BDD tests over plain unit tests.

    Uses TestCoverageScorer as the base score, then adds a bonus when BDD
    tests are detected. The bonus is larger when BDD was not requested in
    TASK.md (unprompted initiative).

    Score range: 0.0 to 1.0 (capped).
    """

    @property
    def name(self) -> str:
        return "test_quality"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0.0

        from retort.scoring.scorers.test_coverage import TestCoverageScorer
        base_score = TestCoverageScorer().score(artifacts, stack)

        # No bonus if tests didn't execute — BDD files that can't run are not
        # better than unit tests that can't run.
        if base_score == 0.0:
            return 0.0

        if not _has_bdd_tests(artifacts.output_dir, stack.language):
            return base_score

        bdd_bonus = 0.25 if _unprompted_bdd(artifacts.output_dir) else 0.15
        return min(1.0, base_score + bdd_bonus)
