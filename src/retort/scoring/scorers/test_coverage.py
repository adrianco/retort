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
from retort.scoring.scorers._venv import ensure_test_deps, find_venv, make_venv_env

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
    "java": ["mvn", "test"],
    "python": ["pytest", "-q", "--tb=no"],
    "go": ["go", "test", "./..."],
    # -M:test runs :main-opts (most common agent pattern); -X:test requires
    # :exec-fn which agents less commonly set up.
    "clojure": ["clojure", "-M:test"],
    # Rust: cargo-llvm-cov not always installed; fall back to plain test run.
    "rust": ["cargo", "test"],
    # Elixir: mix test (agent-generated projects ship their fetched deps/, so a
    # plain `mix test` compiles + runs; the old `mix do deps.get, test` comma
    # syntax was removed in recent Elixir and silently failed -> test_coverage=0).
    "elixir": ["mix", "test"],
    # Erlang: rebar3 eunit fetches deps, compiles, and runs EUnit.
    "erlang": ["rebar3", "eunit"],
}

def _tests_only_commands(language: str, output_dir: Path) -> list[list[str]]:
    """Ordered plain-test commands to try for the pass-rate fallback.

    Most languages have a single runner (see _TESTS_ONLY_COMMANDS). Clojure
    is the exception: the runner depends on the layout the agent produced — a
    deps.edn project is driven by the clojure CLI (`-M:test`), a Leiningen
    project by `lein test`. Earlier scoring only ran the clojure CLI, so a
    valid lein project (whose `lein test` passes) scored test_coverage=0 and
    tripped the gate. Return every runner whose project file is present.
    """
    if language == "clojure":
        cmds: list[list[str]] = []
        if (output_dir / "deps.edn").exists():
            cmds.append(["clojure", "-M:test"])
        if (output_dir / "project.clj").exists():
            cmds.append(["lein", "test"])
        return cmds or [["clojure", "-M:test"]]
    if language == "erlang":
        # `rebar3 eunit` only runs EUnit (`*_tests.erl` / `_test` functions).
        # Agents sometimes write a Common Test suite (`test/*_SUITE.erl`)
        # instead, which eunit reports as "0 tests" -> test_coverage=0 -> false
        # gate fail (a valid CT suite passes under `rebar3 ct`). Add ct as a
        # fallback runner when a suite is present; eunit stays first so an
        # EUnit project short-circuits before ct compiles anything.
        cmds = [["rebar3", "eunit"]]
        test_dir = output_dir / "test"
        if test_dir.is_dir() and any(test_dir.glob("*_SUITE.erl")):
            cmds.append(["rebar3", "ct"])
        return cmds
    cmd = _TESTS_ONLY_COMMANDS.get(language)
    return [cmd] if cmd is not None else []


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

        # Languages without a coverage command (e.g. rust) go straight to the
        # tests-only fallback. Coverage commands are tried first when they exist.
        if cmd is None:
            rate2 = self._tests_pass_rate(output_dir, language)
            return rate2 * 100.0 if rate2 is not None else None

        env = None
        if language == "python":
            venv = find_venv(output_dir)
            if venv is not None:
                ensure_test_deps(venv)
                env = make_venv_env(venv)

        try:
            result = subprocess.run(
                cmd,
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
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
        # (e.g. mvn jacoco:report when the plugin isn't in the pom, or the
        # clojure-CLI cloverage command on a Leiningen project). Try the
        # project's native plain test command(s) and parse the pass rate.
        rate2 = self._tests_pass_rate(output_dir, language, env=env)
        return rate2 * 100.0 if rate2 is not None else None

    def _tests_pass_rate(
        self, output_dir: Path, language: str, env: dict | None = None
    ) -> float | None:
        """Run the project's plain test command(s); return the pass rate [0,1].

        This is the "did the tests actually run?" check the mechanical gate
        relies on. It tries every runner whose project file is present and
        returns the first that yields a parseable test summary — so a valid
        project does not score 0 merely because the default runner doesn't
        match the build tool the agent happened to choose (e.g. a Leiningen
        `project.clj`, which needs `lein test`, where the clojure CLI's
        `-M:test` finds no alias and silently starts a REPL). stdin is closed
        so a runner that drops to a REPL on a missing alias exits instead of
        hanging.
        """
        for tests_cmd in _tests_only_commands(language, output_dir):
            try:
                result = subprocess.run(
                    tests_cmd, cwd=output_dir, capture_output=True,
                    text=True, timeout=300, env=env, stdin=subprocess.DEVNULL,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
            combined = _strip_ansi((result.stdout or "") + "\n" + (result.stderr or ""))
            rate = _parse_test_pass_rate(combined, language)
            if rate is not None:
                return rate
        return None

    def _typescript_coverage(self, output_dir: Path) -> float | None:
        """TypeScript coverage path — detects jest vs vitest from package.json."""
        pkg = output_dir / "package.json"
        if not pkg.exists():
            return None
        try:
            text = pkg.read_text()
        except OSError:
            return None

        if not (output_dir / "node_modules").exists():
            try:
                subprocess.run(
                    ["npm", "install", "--ignore-scripts"],
                    cwd=output_dir, capture_output=True, timeout=120,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        if "vitest" in text:
            # Prefer invoking via node directly: npm may install vitest with a
            # broken relative-path bin wrapper (.bin/vitest → ./dist/cli.js)
            # that fails when cwd != node_modules/.bin.
            vitest_cli = output_dir / "node_modules" / "vitest" / "dist" / "cli.js"
            if vitest_cli.exists():
                for args in [["--coverage"], []]:
                    try:
                        r = subprocess.run(
                            ["node", str(vitest_cli), "run"] + args,
                            cwd=output_dir, capture_output=True, text=True, timeout=180,
                        )
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue
                    combined = _strip_ansi(r.stdout + "\n" + r.stderr)
                    pct = _parse_coverage(combined, "typescript")
                    if pct is not None:
                        return pct
                    rate = _parse_test_pass_rate(combined, "typescript")
                    if rate is not None:
                        return rate * 100.0
                return None
            # Try coverage first, then a plain run for the pass-rate fallback —
            # a project without @vitest/coverage-v8 fails `--coverage` but its
            # tests still pass, and that must not score 0 (test-gate veto).
            cmds = [
                ["npx", "vitest", "run", "--coverage", "--reporter=basic"],
                ["npx", "vitest", "run", "--reporter=basic"],
            ]
        elif "jest" in text:
            cmds = [
                ["npx", "jest", "--coverage", "--coverageReporters=text-summary"],
                ["npx", "jest"],
            ]
        else:
            return None

        for cmd in cmds:
            try:
                result = subprocess.run(
                    cmd, cwd=output_dir, capture_output=True, text=True, timeout=180,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
            combined = _strip_ansi(result.stdout + "\n" + result.stderr)
            pct = _parse_coverage(combined, "typescript")
            if pct is not None:
                return pct
            rate = _parse_test_pass_rate(combined, "typescript")
            if rate is not None:
                return rate * 100.0
        return None


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
    "typescript": [
        # vitest summary (--reporter=basic or default):
        #   Tests  49 passed (49)
        #   Tests  45 passed | 4 failed (49)
        re.compile(r"Tests\s+(?P<passed>\d+)\s+passed(?:\s*\|\s*\d+\s+\w+)?\s+\((?P<total>\d+)\)"),
        # jest summary (--verbose or default):
        #   Tests:      49 passed, 49 total
        re.compile(r"Tests:\s+(?P<passed>\d+)\s+passed(?:,\s*\d+\s+\w+)*,\s*(?P<total>\d+)\s+total"),
    ],
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
    "rust": [
        # cargo test summary:
        #   test result: ok. 27 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
        re.compile(
            r"test result:.*?(?P<passed>\d+)\s+passed;\s*(?P<failed>\d+)\s+failed"
        ),
    ],
    "elixir": [
        # ExUnit summary:  "5 tests, 0 failures"  /  "8 tests, 1 failure, 2 skipped"
        re.compile(
            r"(?P<total>\d+)\s+tests?,\s+(?P<failures>\d+)\s+failures?"
            r"(?:,\s*(?P<skipped>\d+)\s+(?:skipped|excluded))?"
        ),
    ],
    "erlang": [
        # EUnit success:  "  All 12 tests passed."
        re.compile(r"All\s+(?P<passed>\d+)\s+tests?\s+passed"),
        # EUnit with failures:  "Failed: 1.  Skipped: 0.  Passed: 11."
        re.compile(
            r"Failed:\s*(?P<failed>\d+)\.\s+Skipped:\s*(?P<skipped>\d+)\.\s+"
            r"Passed:\s*(?P<passed>\d+)"
        ),
        # Generic "N tests, M failures" (some EUnit/CT formatters use it)
        re.compile(r"(?P<total>\d+)\s+tests?,\s+(?P<failures>\d+)\s+failures?"),
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
        # Use finditer so we see every match (e.g. one per binary for `cargo test`)
        # and pick the one with the highest total — the most informative signal.
        best_passed: int | None = None
        best_total: int | None = None
        for m in pattern.finditer(output):
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
                    continue  # empty binary — skip
            if passed is not None and passed >= 0:
                if best_total is None or total > best_total:
                    best_passed, best_total = passed, total
        if best_total is not None and best_total > 0:
            return max(0.0, min(1.0, best_passed / best_total))
    return None


def _to_int(s: str | None) -> int | None:
    if s is None:
        return None
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


