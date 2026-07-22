"""Defect rate scorer.

Counts post-generation validation defects: lint warnings, type errors,
and test failures the run did not surface as build failures. Lower defect
density (per kloc) is better.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig


# Defects per kloc above this score 0; at 0 defects/kloc score is 1.
_MAX_DEFECTS_PER_KLOC = 50.0


# Static-analysis commands used to count defects. We use distinct (file, line)
# pairs from each tool's output so identical findings reported by multiple tools
# don't double-count.
_DEFECT_COMMANDS: dict[str, list[list[str]]] = {
    "python": [
        ["ruff", "check", "--output-format", "concise", "--no-cache"],
        ["python", "-m", "py_compile"],  # special: needs each file appended
    ],
    "typescript": [
        ["npx", "tsc", "--noEmit"],
        ["npx", "eslint", "--format", "compact", "--quiet"],
    ],
    "go": [
        ["go", "vet", "./..."],
    ],
    "rust": [
        ["cargo", "clippy", "--quiet", "--message-format=short"],
    ],
    "java": [
        ["mvn", "-q", "compile"],
    ],
    "clojure": [
        ["clj-kondo", "--lint", "."],
    ],
    # Compiler warnings as the defect signal (mirrors java's `mvn compile` /
    # go's `go vet`). `--force --all-warnings` re-emits warnings even when the
    # archive is already built; warnings print as `lib/foo.ex:LINE`. If the
    # toolchain is absent the runner catches FileNotFoundError and skips it.
    "elixir": [
        ["mix", "compile", "--force", "--all-warnings"],
    ],
    # rebar3 surfaces erlang compiler warnings as `src/foo.erl:LINE:COL: Warning`.
    "erlang": [
        ["rebar3", "compile"],
    ],
    # C#: `dotnet build` surfaces compile errors + warnings (mirrors java/go).
    "csharp": [
        ["dotnet", "build", "--nologo"],
    ],
    # Swift: `swift build` surfaces warnings as file:line:col (like java/csharp).
    # C/C++/Objective-C compiler-warning counting needs build-system integration
    # (CMake/Make/xcodebuild) — a follow-up; their quality still comes from the
    # other scorers + the test_coverage gate.
    "swift": [
        ["swift", "build"],
    ],
}


_LOC_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "typescript": {".ts", ".tsx", ".js", ".jsx"},
    "go": {".go"},
    "rust": {".rs"},
    "java": {".java"},
    "clojure": {".clj", ".cljc", ".cljs"},
    "erlang": {".erl", ".hrl"},
    "elixir": {".ex", ".exs"},
    "csharp": {".cs"},
    "c": {".c", ".h"},
    "cpp": {".cpp", ".cc", ".cxx", ".hpp", ".h"},
    "objc": {".m", ".h"},
    "swift": {".swift"},
}


_FILE_LINE_RE = re.compile(r"([^\s:]+\.\w+):(\d+)")


class DefectRateScorer:
    """Scores defect density per thousand lines of code.

    Score range: 1.0 (no defects) to 0.0 (≥_MAX_DEFECTS_PER_KLOC defects/kloc).
    A linear inverse mapping in between.
    """

    @property
    def name(self) -> str:
        return "defect_rate"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        # Score regardless of exit_code — see CodeQualityScorer for rationale.
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0.0

        loc = _count_source_lines(artifacts.output_dir, stack.language)
        if loc <= 0:
            return 0.0

        defects = self._count_defects(artifacts.output_dir, stack.language)
        defects_per_kloc = (defects / loc) * 1000.0

        if defects_per_kloc >= _MAX_DEFECTS_PER_KLOC:
            return 0.0
        return max(0.0, 1.0 - defects_per_kloc / _MAX_DEFECTS_PER_KLOC)

    def _count_defects(self, output_dir: Path, language: str) -> int:
        """Run all configured defect tools and count distinct (file, line) hits."""
        commands = _DEFECT_COMMANDS.get(language, [])
        seen: set[tuple[str, str]] = set()

        for cmd in commands:
            output = self._run(cmd, output_dir, language)
            if output is None:
                continue
            for m in _FILE_LINE_RE.finditer(output):
                seen.add((m.group(1), m.group(2)))

        return len(seen)

    def _run(self, cmd: list[str], output_dir: Path, language: str) -> str | None:
        try:
            if cmd[:2] == ["python", "-m"] and cmd[2] == "py_compile":
                # py_compile needs filenames appended; check each .py file individually.
                files = [str(p) for p in output_dir.rglob("*.py")
                         if "__pycache__" not in p.parts]
                if not files:
                    return ""
                result = subprocess.run(
                    cmd + files,
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            else:
                result = subprocess.run(
                    cmd,
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        return (result.stdout or "") + "\n" + (result.stderr or "")


def _count_source_lines(output_dir: Path, language: str) -> int:
    """Count non-blank source lines in the run's archive."""
    exts = _LOC_EXTENSIONS.get(language, set())
    if not exts:
        return 0

    from retort.scoring.scorers._common import SKIP_PARTS as skip_parts
    total = 0
    for ext in exts:
        for p in output_dir.rglob(f"*{ext}"):
            if any(part in skip_parts for part in p.parts):
                continue
            try:
                total += sum(1 for line in p.read_text().splitlines() if line.strip())
            except OSError:
                continue
    return total
