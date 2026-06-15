#!/usr/bin/env python3
"""Structural validation for the funkygibbon-port task.

Language-agnostic, best-effort checks that a plausible port was produced: source
files, a test suite, a README, and signals that the conformance surface (MCP
tools + the protocol) was actually addressed. The real pass/fail comes from the
spec-gate requirement_coverage (REQUIREMENTS.json) and the port's own tests; this
just catches empty / obviously-incomplete submissions.
"""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_EXTS = {".go", ".rs", ".ts", ".js", ".py", ".ex", ".exs", ".erl", ".java",
               ".clj", ".rb", ".swift", ".kt", ".cs", ".cpp", ".c", ".hs"}

# The 12 tools must be wired by name somewhere in the port.
TOOLS = [
    "search_entities", "get_entity_details", "create_entity", "update_entity",
    "create_relationship", "get_devices_in_room", "find_device_controls",
    "get_room_connections", "find_path", "find_similar_entities",
    "get_procedures_for_device", "get_automations_in_room",
]

# Protocol signals the port should reference somewhere.
PROTOCOL_SIGNALS = ["inbetweenies-v2", "server_time", "deleted"]


def _text_of(files: list[Path]) -> str:
    blob = []
    for f in files:
        try:
            blob.append(f.read_text(errors="ignore"))
        except OSError:
            pass
    return "\n".join(blob)


def main() -> int:
    ws = Path.cwd()
    errors: list[str] = []

    # The reference Python/TS clients may be present (the agent cloned the repo);
    # only consider files OUTSIDE blowing-off/ and the TS port as "the port".
    def is_port(f: Path) -> bool:
        parts = set(f.parts)
        return not (parts & {"blowing-off", "blowingoff", "funkygibbon",
                             "inbetweenies", "oook", "the-goodies-typescript",
                             "kittenkong", "node_modules", ".git"})

    source = [f for f in ws.rglob("*")
              if f.is_file() and f.suffix in SOURCE_EXTS and is_port(f)]
    if not source:
        errors.append("No port source files found")

    tests = [f for f in source
             if any(k in f.name.lower() for k in ("test", "spec", "_test"))]
    if not tests:
        errors.append("No test files found in the port")

    if not list(ws.rglob("README.md")):
        errors.append("Missing README.md")

    blob = _text_of(source)
    missing_tools = [t for t in TOOLS if t not in blob]
    if len(missing_tools) > 4:  # allow a few naming differences, but most must be present
        errors.append(f"Most MCP tools missing from the port: {missing_tools}")

    missing_signals = [s for s in PROTOCOL_SIGNALS if s not in blob]
    if missing_signals:
        errors.append(f"Protocol signals not referenced: {missing_signals}")

    for e in errors:
        print(f"  FAIL: {e}")
    if errors:
        print(f"\n{len(errors)} validation error(s)")
        return 1
    print("All structural validations passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
