"""Maintainability scorer.

Approximates maintainability via three structural proxies:

  1. Average function length (shorter = more maintainable, up to a floor).
  2. File-size variance (very large files are harder to maintain).
  3. Test-to-source ratio (more tests = easier to change safely).

This is intentionally tool-light: the plan calls out cross-agent
modification success as the gold-standard signal, but we don't yet have
that infrastructure. This scorer is a static-analysis stand-in that
correlates roughly with maintainability without requiring extra runs.
"""

from __future__ import annotations

import re
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig


# Function definition patterns per language. Captures everything up to the
# function name; we don't try to be a parser, just a heuristic counter.
_FUNCTION_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "python": [re.compile(r"^\s*def\s+\w+\s*\(", re.MULTILINE)],
    "typescript": [
        re.compile(r"^\s*(export\s+)?(async\s+)?function\s+\w+", re.MULTILINE),
        re.compile(r"^\s*(export\s+)?const\s+\w+\s*=\s*(async\s+)?\(", re.MULTILINE),
    ],
    "go": [re.compile(r"^func\s+(\(\w+\s+\*?\w+\)\s+)?\w+\s*\(", re.MULTILINE)],
    "rust": [re.compile(r"^\s*(pub\s+)?(async\s+)?fn\s+\w+\s*[<(]", re.MULTILINE)],
    "java": [
        # Methods inside classes — heuristic, captures public/private/protected
        # static return-type Name(. Won't match constructors but close enough
        # for the avg-length proxy.
        re.compile(
            r"^\s*(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?"
            r"[\w<>\[\]]+\s+\w+\s*\(",
            re.MULTILINE,
        ),
    ],
    "clojure": [re.compile(r"^\s*\(defn-?\s+\w+", re.MULTILINE)],
}

_SOURCE_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "typescript": {".ts", ".tsx", ".js", ".jsx"},
    "go": {".go"},
    "rust": {".rs"},
    "java": {".java"},
    "clojure": {".clj", ".cljc", ".cljs"},
}

_SKIP_PARTS = {"node_modules", "target", "__pycache__", ".git", "dist", "build"}

# Tunable thresholds. Each is the value at which the corresponding sub-score is 0.
# The sub-score is 1.0 at the "ideal" anchor and linearly decays.
_FN_LEN_IDEAL = 15        # average function lines
_FN_LEN_MAX = 80
_FILE_SIZE_VARIANCE_MAX = 200  # std dev of file LOC
_TEST_RATIO_IDEAL = 0.5    # test_loc / source_loc


class MaintainabilityScorer:
    """Composite maintainability score in [0, 1]."""

    @property
    def name(self) -> str:
        return "maintainability"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if not artifacts.succeeded:
            return 0.0
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0.0

        source_files, test_files = _collect_files(artifacts.output_dir, stack.language)
        if not source_files:
            return 0.0

        avg_fn_len = _avg_function_length(source_files, stack.language)
        size_variance = _file_size_variance(source_files)
        test_ratio = _test_to_source_ratio(source_files, test_files)

        scores = [
            _ramp(avg_fn_len, _FN_LEN_IDEAL, _FN_LEN_MAX, lower_is_better=True),
            _ramp(size_variance, 0.0, _FILE_SIZE_VARIANCE_MAX, lower_is_better=True),
            _ramp(test_ratio, _TEST_RATIO_IDEAL, 0.0, lower_is_better=False),
        ]
        return sum(scores) / len(scores)


def _collect_files(root: Path, language: str) -> tuple[list[Path], list[Path]]:
    exts = _SOURCE_EXTENSIONS.get(language, set())
    source: list[Path] = []
    tests: list[Path] = []
    for ext in exts:
        for p in root.rglob(f"*{ext}"):
            if any(part in _SKIP_PARTS for part in p.parts):
                continue
            if _looks_like_test(p):
                tests.append(p)
            else:
                source.append(p)
    return source, tests


def _looks_like_test(p: Path) -> bool:
    name = p.name.lower()
    parts = {part.lower() for part in p.parts}
    return (
        name.startswith("test_") or name.endswith("_test.py") or name.endswith(".test.ts")
        or name.endswith(".test.tsx") or name.endswith(".spec.ts") or name.endswith("_test.go")
        or "test" in parts or "tests" in parts or "__tests__" in parts
    )


def _avg_function_length(files: list[Path], language: str) -> float:
    """Mean LOC per function definition. Heuristic: split by function pattern."""
    patterns = _FUNCTION_PATTERNS.get(language, [])
    if not patterns:
        return _FN_LEN_IDEAL  # neutral

    total_lines = 0
    total_fns = 0
    for f in files:
        try:
            text = f.read_text()
        except OSError:
            continue
        non_blank = sum(1 for line in text.splitlines() if line.strip())
        fn_count = sum(len(p.findall(text)) for p in patterns)
        total_lines += non_blank
        total_fns += fn_count

    if total_fns == 0:
        return _FN_LEN_MAX  # all top-level code = bad
    return total_lines / total_fns


def _file_size_variance(files: list[Path]) -> float:
    """Sample standard deviation of file LOC. 0 = all files same size."""
    if len(files) < 2:
        return 0.0
    loc = []
    for f in files:
        try:
            loc.append(sum(1 for line in f.read_text().splitlines() if line.strip()))
        except OSError:
            continue
    if len(loc) < 2:
        return 0.0
    mean = sum(loc) / len(loc)
    return (sum((x - mean) ** 2 for x in loc) / (len(loc) - 1)) ** 0.5


def _test_to_source_ratio(source_files: list[Path], test_files: list[Path]) -> float:
    if not source_files:
        return 0.0
    src_loc = _total_loc(source_files)
    test_loc = _total_loc(test_files)
    if src_loc == 0:
        return 0.0
    return test_loc / src_loc


def _total_loc(files: list[Path]) -> int:
    total = 0
    for f in files:
        try:
            total += sum(1 for line in f.read_text().splitlines() if line.strip())
        except OSError:
            continue
    return total


def _ramp(value: float, ideal: float, edge: float, *, lower_is_better: bool) -> float:
    """Linear ramp: 1.0 at ideal, 0.0 at edge, clamped outside."""
    if lower_is_better:
        if value <= ideal:
            return 1.0
        if value >= edge:
            return 0.0
        return 1.0 - (value - ideal) / (edge - ideal)
    # higher is better
    if value >= ideal:
        return 1.0
    if value <= edge:
        return 0.0
    return (value - edge) / (ideal - edge)
