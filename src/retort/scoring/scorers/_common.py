"""Shared source-file scanning for scorers.

One canonical skip set so scorers can't drift. Directories here hold generated,
vendored, or build output — never hand-authored source — so counting their files
as source inflates scores. Notably `obj/` and `bin/` hold a `dotnet new` scaffold's
~9 generated `.cs` files (`*.AssemblyInfo.cs`, `*.GlobalUsings.g.cs`, …); without
skipping them an empty C# project false-PASSes with code_quality=1.0,
defect_rate=1.0 on zero authored code (issue #43).
"""

from __future__ import annotations

from pathlib import Path

SKIP_PARTS = {
    "node_modules", "target", "__pycache__", ".git", "dist", "build",
    "_build", "deps", ".rebar3", "obj", "bin", ".venv",
}


def is_skipped(p: Path) -> bool:
    """True if any path component is a generated/vendored/build dir."""
    return any(part in SKIP_PARTS for part in p.parts)


def iter_source_files(root: Path, ext: str):
    """Yield ``*ext`` files under ``root``, skipping generated/build dirs."""
    for p in root.rglob(f"*{ext}"):
        if not is_skipped(p):
            yield p
