#!/usr/bin/env python3
"""Validation script for the cli-data-pipeline task."""

from __future__ import annotations

import sys
from pathlib import Path


def check_structure(workspace: Path) -> list[str]:
    errors = []
    source_exts = {".py", ".ts", ".go", ".rs", ".js"}
    source_files = [
        f for f in workspace.rglob("*")
        if f.suffix in source_exts and f.is_file()
    ]
    if not source_files:
        errors.append("No source files found")
    if not (workspace / "README.md").exists():
        errors.append("Missing README.md")
    return errors


def check_tests_exist(workspace: Path) -> list[str]:
    test_patterns = ["test_*", "*_test.*", "*.test.*", "*_spec.*"]
    test_files = []
    for pattern in test_patterns:
        test_files.extend(workspace.rglob(pattern))
    if len(test_files) < 3:
        return [f"Expected at least 3 test files, found {len(test_files)}"]
    return []


def main() -> int:
    workspace = Path.cwd()
    all_errors: list[str] = []

    print("Validating cli-data-pipeline task...")

    errors = check_structure(workspace)
    all_errors.extend(errors)
    for e in errors:
        print(f"  FAIL: {e}")

    errors = check_tests_exist(workspace)
    all_errors.extend(errors)
    for e in errors:
        print(f"  FAIL: {e}")

    if all_errors:
        print(f"\n{len(all_errors)} validation error(s)")
        return 1

    print("All structural validations passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
