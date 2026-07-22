"""Code quality scorer.

Measures code quality by checking for lint issues, type errors,
and basic complexity metrics in the generated output.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring.scorers._venv import find_venv, make_venv_env

# Lint commands per language
LINT_COMMANDS: dict[str, list[str]] = {
    "python": ["ruff", "check", "--select", "E,F,W", "--quiet"],
    "typescript": ["npx", "eslint", "--format", "compact", "--quiet"],
    "go": ["go", "vet", "./..."],
    # Java: maven compile catches type errors and basic issues. Falls back
    # if no pom.xml — javac doesn't do project compilation easily.
    "java": ["mvn", "-q", "compile"],
    # Clojure: clj-kondo is the de facto linter; skip if not installed
    # (the scorer returns a neutral 0.5 when the command is missing).
    "clojure": ["clj-kondo", "--lint", "."],
    # Swift: swiftlint if present (skipped gracefully otherwise).
    "swift": ["swiftlint", "--quiet"],
    # C/C++/Objective-C use the compiler as the linter (see _NATIVE_LANGS +
    # _native_lint_score) — a build-system-aware `-Wall -Wextra` build, mirroring
    # how java/csharp/erlang use their compiler for lint.
    # Elixir: mix compile reports warnings-as-errors when the project is
    # properly structured. Credo (optional dep) is not assumed present.
    "elixir": ["mix", "compile", "--warnings-as-errors"],
    # Erlang: rebar3 compile covers most project layouts; falls back to
    # neutral 0.5 if rebar3 is not installed.
    "erlang": ["rebar3", "compile"],
    # C#: `dotnet build` catches compile errors + warnings (mirrors java's mvn compile).
    "csharp": ["dotnet", "build", "--nologo"],
}

# C-family languages whose lint signal comes from a native -Wall build rather
# than a fixed LINT_COMMANDS entry (see _native_lint_score).
_NATIVE_LANGS = frozenset({"c", "cpp", "objc"})


class CodeQualityScorer:
    """Scores code quality based on lint pass rate and structural metrics.

    Score range: 0.0 (worst) to 1.0 (best).
    """

    @property
    def name(self) -> str:
        return "code_quality"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        # Score whatever's in the workspace, regardless of the agent's
        # exit code. An agent that hit --max-turns may still have produced
        # buildable, useful code; an agent that exited 0 may have produced
        # nothing. The file-existence check below is the real gate.
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0.0

        scores: list[float] = []

        # 1. Lint pass rate
        lint_score = self._lint_score(artifacts.output_dir, stack.language)
        scores.append(lint_score)

        # 2. File structure score — reward organized code
        structure_score = self._structure_score(artifacts.output_dir, stack.language)
        scores.append(structure_score)

        # 3. No obvious issues in stderr
        stderr_score = 1.0 if not _has_error_patterns(artifacts.stderr) else 0.5
        scores.append(stderr_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _lint_score(self, output_dir: Path, language: str) -> float:
        """Run linter and compute pass rate."""
        if language in _NATIVE_LANGS:
            return self._native_lint_score(output_dir)

        cmd = LINT_COMMANDS.get(language)
        if cmd is None:
            return 0.5  # No linter available — neutral score

        env = None
        if language == "python":
            venv = find_venv(output_dir)
            if venv is not None:
                env = make_venv_env(venv)

        try:
            result = subprocess.run(
                cmd,
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
            if result.returncode == 0:
                return 1.0
            # Count issues — each issue reduces score
            issues = result.stdout.count("\n") + result.stderr.count("\n")
            return max(0.0, 1.0 - (issues * 0.05))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0.5

    def _native_lint_score(self, output_dir: Path) -> float:
        """Lint C/C++/Objective-C via a `-Wall -Wextra` build (compiler-as-linter).

        Counts distinct warning/error diagnostics; 0 → 1.0, each one costs 0.05
        (same curve as the generic linter path). A build system that's absent or
        whose tools are missing yields no output → neutral 0.5, never a false
        perfect score. A genuine build failure is still caught by the
        test_coverage conformance gate.
        """
        from retort.scoring.scorers._common import (
            NATIVE_DIAG_RE, native_warnings_build,
        )
        output = native_warnings_build(output_dir)
        if not output.strip():
            return 0.5  # no build system / toolchain — neutral, no signal
        issues = {(m.group(1), m.group(2)) for m in NATIVE_DIAG_RE.finditer(output)}
        if not issues:
            return 1.0
        return max(0.0, 1.0 - len(issues) * 0.05)

    def _structure_score(self, output_dir: Path, language: str) -> float:
        """Score based on file organization."""
        extensions = {
            "python": ".py",
            "typescript": ".ts",
            "go": ".go",
            "rust": ".rs",
            "java": ".java",
            "clojure": ".clj",
            "elixir": ".ex",
            "erlang": ".erl",
            "csharp": ".cs",
            "c": ".c",
            "cpp": ".cpp",
            "objc": ".m",
            "swift": ".swift",
        }
        ext = extensions.get(language, ".py")
        from retort.scoring.scorers._common import iter_source_files
        source_files = list(iter_source_files(output_dir, ext))

        if not source_files:
            return 0.0

        score = min(1.0, len(source_files) / 3.0)  # Reward multiple files

        # Bonus for test files
        test_files = [f for f in source_files if "test" in f.name.lower()]
        if test_files:
            score = min(1.0, score + 0.2)

        return score


def _has_error_patterns(text: str) -> bool:
    """Check for common error patterns in output."""
    patterns = [
        r"(?i)traceback",
        r"(?i)error:",
        r"(?i)fatal:",
        r"(?i)panic:",
    ]
    return any(re.search(p, text) for p in patterns)
