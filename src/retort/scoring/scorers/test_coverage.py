"""Test coverage scorer.

Runs the language's coverage tooling and parses the percentage covered.
Higher is better. When coverage tooling isn't configured (e.g. an agent
that wrote tests but didn't add jacoco to its pom.xml), falls back to
the test pass rate — better signal than 0 when tests clearly do run.
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

# Plain test commands for the test-pass-rate fallback. Run when the
# coverage command above produces no parseable percentage AND no
# parseable test-pass output (e.g. maven aborts on missing jacoco
# plugin before tests run).
_TESTS_ONLY_COMMANDS: dict[str, list[str]] = {
    "java": ["mvn", "-q", "test"],
    "python": ["pytest", "-q", "--tb=no"],
    "go": ["go", "test", "./..."],
    "clojure": ["clojure", "-X:test"],
}

# Regex to extract a percentage like "75%" from coverage output.
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")

# Match ANSI color escape sequences so test-runner output that ships
# with colorized terminals still parses cleanly.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


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
                timeout=300,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

        combined = _strip_ansi((result.stdout or "") + "\n" + (result.stderr or ""))
        pct = _parse_coverage(combined, language)
        if pct is not None:
            return pct
        # Fallback 1: same combined output may contain a test-pass summary.
        # Note: _parse_test_pass_rate returns [0, 1]; the caller divides
        # by 100 (because real coverage tools return 0-100). Scale up.
        rate = _parse_test_pass_rate(combined, language)
        if rate is not None:
            return rate * 100.0
        # Fallback 2: the coverage command may have aborted before tests ran
        # (e.g. mvn jacoco:report when the plugin isn't in the pom). Try
        # a plain test command and parse pass rate from its output.
        tests_cmd = _TESTS_ONLY_COMMANDS.get(language)
        if tests_cmd is None:
            return None
        try:
            result2 = subprocess.run(
                tests_cmd, cwd=output_dir, capture_output=True,
                text=True, timeout=300,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        combined2 = _strip_ansi((result2.stdout or "") + "\n" + (result2.stderr or ""))
        rate2 = _parse_test_pass_rate(combined2, language)
        return rate2 * 100.0 if rate2 is not None else None

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


# Patterns for "X passed / Y total" messages from common test runners.
# Match returns (passed, total) as strings.
_TEST_PASS_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "java": [
        # JUnit Surefire summary:
        #   Tests run: 24, Failures: 0, Errors: 0, Skipped: 0
        re.compile(
            r"Tests run:\s*(?P<total>\d+),\s*"
            r"Failures:\s*(?P<failures>\d+),\s*"
            r"Errors:\s*(?P<errors>\d+)(?:,\s*Skipped:\s*(?P<skipped>\d+))?"
        ),
        # Cucumber:
        #   24 Scenarios (24 passed)
        #   83 Steps (83 passed)
        re.compile(r"(?P<total>\d+)\s+Scenarios\s+\((?P<passed>\d+)\s+passed\)"),
    ],
    "go": [
        # `go test`: each PASS/FAIL line. Use ratio of PASS lines to total lines
        # via a separate counter (handled in _parse_test_pass_rate below).
    ],
    "clojure": [
        # `lein test` or `clojure -M:test`:
        #   Ran 12 tests containing 34 assertions.
        #   0 failures, 0 errors.
        re.compile(
            r"Ran\s+(?P<total>\d+)\s+tests.*?(?P<failures>\d+)\s+failures,\s*"
            r"(?P<errors>\d+)\s+errors",
            re.DOTALL,
        ),
    ],
    "python": [
        # pytest summary:
        #   ===== 12 passed, 2 failed, 1 skipped in 0.34s =====
        re.compile(r"(?P<passed>\d+)\s+passed(?:,\s*(?P<failed>\d+)\s+failed)?"),
    ],
}


def _parse_test_pass_rate(output: str, language: str) -> float | None:
    """Last-resort: extract a tests-pass-rate from common test-runner output.

    Returns a value in [0, 1] for the fraction of tests that passed.
    Better signal than `0.0` when tests clearly ran but no coverage
    percentage was reported. Returns None if no test-summary pattern
    matches.
    """
    if not output:
        return None
    for pattern in _TEST_PASS_PATTERNS.get(language, []):
        m = pattern.search(output)
        if not m:
            continue
        groups = m.groupdict()
        total = _to_int(groups.get("total"))
        passed = _to_int(groups.get("passed"))
        failures = _to_int(groups.get("failures")) or 0
        errors = _to_int(groups.get("errors")) or 0
        skipped = _to_int(groups.get("skipped")) or 0
        failed = _to_int(groups.get("failed")) or 0

        if total is not None and total > 0:
            if passed is None:
                passed = total - failures - errors - skipped - failed
        else:
            # No explicit total — derive from passed + the failure-class counts.
            if passed is None:
                continue
            total = passed + failures + errors + failed
            if total == 0:
                continue
        if passed >= 0:
            return max(0.0, min(1.0, passed / total))
    return None


def _to_int(s: str | None) -> int | None:
    if s is None:
        return None
    try:
        return int(s)
    except (TypeError, ValueError):
        return None
