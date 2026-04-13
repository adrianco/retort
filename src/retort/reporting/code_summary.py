"""Deterministic per-run code summary.

A lightweight, no-API-call equivalent of the `run-summary` skill: scans
an archived run workspace and emits a structured summary suitable for
inlining into the static web report. Intentionally simple — file listing,
LOC, top-level symbols by language. Heavier semantic analysis is what
the real `run-summary` skill is for.

Used by reporting/web.py to populate the per-replicate "Code review"
detail blocks on stack drill-down pages, so the published HTML report
is self-contained (no broken links to gitignored summary files).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


_SOURCE_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "typescript": {".ts", ".tsx", ".js", ".jsx"},
    "go": {".go"},
    "rust": {".rs"},
    "java": {".java"},
    "clojure": {".clj", ".cljc", ".cljs"},
}

_SKIP_PARTS = {
    "node_modules", "target", "__pycache__", ".git", "dist", "build",
    ".venv", "venv", ".pytest_cache", ".beads", ".claude", ".retort-cache",
}

# Language-specific patterns for top-level symbols.
_SYMBOL_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "python": [
        ("class", re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)),
        ("def",   re.compile(r"^\s*def\s+(\w+)", re.MULTILINE)),
    ],
    "typescript": [
        ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE)),
        ("const",    re.compile(r"^\s*export\s+const\s+(\w+)\s*=", re.MULTILINE)),
        ("class",    re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.MULTILINE)),
    ],
    "go": [
        ("func",   re.compile(r"^func\s+(?:\([^)]*\)\s+)?(\w+)", re.MULTILINE)),
        ("type",   re.compile(r"^type\s+(\w+)", re.MULTILINE)),
    ],
    "rust": [
        ("fn",     re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE)),
        ("struct", re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)", re.MULTILINE)),
        ("enum",   re.compile(r"^\s*(?:pub\s+)?enum\s+(\w+)", re.MULTILINE)),
    ],
    "java": [
        ("class",     re.compile(r"^\s*(?:public\s+|abstract\s+|final\s+)*class\s+(\w+)", re.MULTILINE)),
        ("interface", re.compile(r"^\s*(?:public\s+)?interface\s+(\w+)", re.MULTILINE)),
        ("method",    re.compile(
            r"^\s*(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?"
            r"[\w<>\[\]]+\s+(\w+)\s*\(",
            re.MULTILINE,
        )),
    ],
    "clojure": [
        ("defn", re.compile(r"^\s*\(defn-?\s+([\w?!*+/<=>-]+)", re.MULTILINE)),
        ("def",  re.compile(r"^\s*\(def\s+([\w?!*+/<=>-]+)", re.MULTILINE)),
        ("ns",   re.compile(r"^\s*\(ns\s+([\w.]+)", re.MULTILINE)),
    ],
}


@dataclass(frozen=True)
class FileSummary:
    """A single source file in a run archive."""
    relpath: str
    loc: int
    is_test: bool
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class CodeSummary:
    """Summary of all source code in one run archive."""
    archive_dir: Path
    language: str
    n_files: int
    n_test_files: int
    total_loc: int
    test_loc: int
    files: tuple[FileSummary, ...] = field(default_factory=tuple)


def summarize_archive(archive_dir: Path, language: str) -> CodeSummary | None:
    """Scan archive_dir for source files of the given language.

    Returns None if the archive doesn't exist or has no source files —
    the caller renders that as "no archive" rather than an empty summary.
    """
    if not archive_dir.exists() or not archive_dir.is_dir():
        return None

    extensions = _SOURCE_EXTENSIONS.get(language, set())
    if not extensions:
        return None

    files: list[FileSummary] = []
    for ext in extensions:
        for p in sorted(archive_dir.rglob(f"*{ext}")):
            if any(part in _SKIP_PARTS for part in p.parts):
                continue
            try:
                content = p.read_text()
            except OSError:
                continue
            loc = sum(1 for line in content.splitlines() if line.strip())
            symbols = tuple(_extract_symbols(content, language))
            relpath = str(p.relative_to(archive_dir))
            files.append(FileSummary(
                relpath=relpath,
                loc=loc,
                is_test=_looks_like_test(p),
                symbols=symbols,
            ))

    if not files:
        return None

    total_loc = sum(f.loc for f in files)
    test_files = [f for f in files if f.is_test]
    test_loc = sum(f.loc for f in test_files)

    return CodeSummary(
        archive_dir=archive_dir,
        language=language,
        n_files=len(files),
        n_test_files=len(test_files),
        total_loc=total_loc,
        test_loc=test_loc,
        files=tuple(files),
    )


def _extract_symbols(content: str, language: str) -> list[str]:
    """Return top-level symbol declarations as 'kind name' strings."""
    out: list[str] = []
    for kind, pattern in _SYMBOL_PATTERNS.get(language, []):
        for m in pattern.finditer(content):
            out.append(f"{kind} {m.group(1)}")
    return out


def _looks_like_test(p: Path) -> bool:
    name = p.name.lower()
    parts = {part.lower() for part in p.parts}
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith("_test.go")
        or name.endswith(".test.ts") or name.endswith(".test.tsx")
        or name.endswith(".spec.ts") or name.endswith(".spec.tsx")
        or "test" in parts or "tests" in parts or "__tests__" in parts
    )
