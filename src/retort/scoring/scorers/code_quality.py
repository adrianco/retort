"""Code quality scorer.

Measures code quality by checking for lint issues, type errors,
and basic complexity metrics in the generated output.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig

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
}


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
        cmd = LINT_COMMANDS.get(language)
        if cmd is None:
            return 0.5  # No linter available — neutral score

        try:
            result = subprocess.run(
                cmd,
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return 1.0
            # Count issues — each issue reduces score
            issues = result.stdout.count("\n") + result.stderr.count("\n")
            return max(0.0, 1.0 - (issues * 0.05))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0.5

    def _structure_score(self, output_dir: Path, language: str) -> float:
        """Score based on file organization."""
        extensions = {
            "python": ".py",
            "typescript": ".ts",
            "go": ".go",
            "rust": ".rs",
            "java": ".java",
            "clojure": ".clj",
        }
        ext = extensions.get(language, ".py")
        source_files = list(output_dir.rglob(f"*{ext}"))

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
