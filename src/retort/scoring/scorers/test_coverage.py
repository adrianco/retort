"""Test coverage scorer.

Runs the language's coverage tooling and parses the percentage covered.
Higher is better.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig


COVERAGE_COMMANDS: dict[str, list[str]] = {
    "python": ["pytest", "--cov=.", "--cov-report=term", "-q", "--tb=no"],
    "go": ["go", "test", "-cover", "./..."],
    # TypeScript handled specially — needs to detect jest vs vitest
    # Rust requires cargo-llvm-cov which isn't always installed
    # Java: jacoco via maven if pom.xml exists
    "java": ["mvn", "-q", "test", "jacoco:report"],
    # Clojure: cloverage via clojure CLI; requires :test alias to be set up
    "clojure": ["clojure", "-Sdeps",
                "{:deps {cloverage/cloverage {:mvn/version \"1.2.4\"}}}",
                "-M", "-m", "cloverage.coverage"],
}

# Regex to extract a percentage like "75%" from coverage output.
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


class TestCoverageScorer:
    """Scores test coverage as the line/statement coverage percentage.

    Score range: 0.0 (no coverage / no tests / coverage tool unavailable)
                 to 1.0 (100% coverage).
    """

    @property
    def name(self) -> str:
        return "test_coverage"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        # Score regardless of exit_code — see CodeQualityScorer for rationale.
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0.0

        if stack.language == "typescript":
            pct = self._typescript_coverage(artifacts.output_dir)
        else:
            pct = self._coverage_via_command(artifacts.output_dir, stack.language)

        if pct is None:
            return 0.0
        return max(0.0, min(1.0, pct / 100.0))

    def _coverage_via_command(self, output_dir: Path, language: str) -> float | None:
        cmd = COVERAGE_COMMANDS.get(language)
        if cmd is None:
            return None
        try:
            result = subprocess.run(
                cmd,
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

        return _parse_coverage(result.stdout + "\n" + result.stderr, language)

    def _typescript_coverage(self, output_dir: Path) -> float | None:
        """TypeScript coverage path — detects jest vs vitest from package.json."""
        pkg = output_dir / "package.json"
        if not pkg.exists():
            return None
        try:
            text = pkg.read_text()
        except OSError:
            return None

        if "vitest" in text:
            cmd = ["npx", "vitest", "run", "--coverage", "--reporter=basic"]
        elif "jest" in text:
            cmd = ["npx", "jest", "--coverage", "--coverageReporters=text-summary"]
        else:
            return None

        try:
            result = subprocess.run(
                cmd,
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

        return _parse_coverage(result.stdout + "\n" + result.stderr, "typescript")


def _parse_coverage(output: str, language: str) -> float | None:
    """Extract a coverage percentage from tool output. Heuristic per language."""
    if not output:
        return None

    if language == "python":
        # pytest-cov terminal report ends with a TOTAL line:
        #   TOTAL  124  12  90%
        for line in reversed(output.splitlines()):
            if line.strip().startswith("TOTAL"):
                m = _PERCENT_RE.search(line)
                if m:
                    return float(m.group(1))
        return None

    if language == "go":
        # `go test -cover` per-package: "ok  ./pkg  0.123s  coverage: 87.5% of statements"
        percentages: list[float] = []
        for line in output.splitlines():
            if "coverage:" in line:
                m = _PERCENT_RE.search(line)
                if m:
                    percentages.append(float(m.group(1)))
        if not percentages:
            return None
        # Mean across packages — simplistic but defensible.
        return sum(percentages) / len(percentages)

    if language == "typescript":
        # jest text-summary: "Lines  : 87.5% ( 70/80 )"
        # vitest basic:     "Coverage report from v8" then tabular output
        for line in output.splitlines():
            if "Lines" in line or "All files" in line:
                m = _PERCENT_RE.search(line)
                if m:
                    return float(m.group(1))
        return None

    return None
