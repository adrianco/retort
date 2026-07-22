"""Shared source-file scanning for scorers.

One canonical skip set so scorers can't drift. Directories here hold generated,
vendored, or build output — never hand-authored source — so counting their files
as source inflates scores. Notably `obj/` and `bin/` hold a `dotnet new` scaffold's
~9 generated `.cs` files (`*.AssemblyInfo.cs`, `*.GlobalUsings.g.cs`, …); without
skipping them an empty C# project false-PASSes with code_quality=1.0,
defect_rate=1.0 on zero authored code (issue #43).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

SKIP_PARTS = {
    "node_modules", "target", "__pycache__", ".git", "dist", "build",
    "_build", "deps", ".rebar3", "obj", "bin", ".venv", "build-warn",
    # SwiftPM vendors its dependency SOURCE (Vapor/NIO/... .swift files) under
    # `.build/checkouts`; without skipping it a Swift project's loc balloons by
    # ~1000x (measured: 834K vs ~500 authored lines), wrecking every per-file
    # metric (defect_rate, maintainability, token_efficiency, idiomatic).
    ".build",
}


def is_skipped(p: Path) -> bool:
    """True if any path component is a generated/vendored/build dir."""
    return any(part in SKIP_PARTS for part in p.parts)


def iter_source_files(root: Path, ext: str):
    """Yield ``*ext`` files under ``root``, skipping generated/build dirs."""
    for p in root.rglob(f"*{ext}"):
        if not is_skipped(p):
            yield p


# C / C++ / Objective-C compiler diagnostics: ``path/foo.cpp:12:5: warning: ...``
# (and ``error:``). Captures ``(file, line)`` and matches ONLY warning/error
# lines, so ``note:`` continuations and bare ``file:line`` noise aren't counted
# as separate defects.
NATIVE_DIAG_RE = re.compile(r"([^\s:]+\.\w+):(\d+):(?:\d+:)?\s*(?:warning|error):")


def native_warnings_build(root: Path) -> str:
    """Best-effort build a C/C++/Objective-C project with warnings enabled.

    Returns the combined compiler output (warnings + errors as ``file:line:col:``)
    so the defect_rate and code_quality scorers can count diagnostics — the
    compiler-as-linter pattern the other compiled languages already use (java's
    ``mvn compile``, C#'s ``dotnet build``, erlang's ``rebar3 compile``). Since
    C/C++/ObjC have no single canonical linter and ``clang-tidy`` needs a
    per-file compile database, ``-Wall -Wextra`` on the real build is the robust,
    build-system-agnostic signal.

    Detects the build system: CMake (configure with the warning flags + a
    compile-command export, then build), then Makefile. Returns ``""`` when
    there's no build system or the tools are missing — callers read that as
    "no signal" (neutral), never as a defect. Builds into ``build-warn/`` (kept
    in ``SKIP_PARTS``) so its artifacts are never counted as source and it never
    disturbs the separate coverage build.

    Every call forces a FULL recompile (a fresh ``build-warn/`` for CMake, a
    ``make clean`` for Makefiles). A compiler only prints ``-Wall`` warnings for
    files it actually compiles, so an incremental/cached build re-emits *zero*
    warnings — the same caching trap that silently zeroed Go coverage. Both the
    defect_rate and code_quality scorers call this independently, so each must
    start from a clean slate to see the diagnostics at all.
    """
    root = root.resolve()

    def _run(cmd: list[str], timeout: int = 300) -> str:
        try:
            r = subprocess.run(cmd, cwd=root, capture_output=True,
                               text=True, timeout=timeout)
            return (r.stdout or "") + "\n" + (r.stderr or "")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ""

    if (root / "CMakeLists.txt").exists():
        # Fresh build dir → every source is (re)compiled → warnings are emitted.
        shutil.rmtree(root / "build-warn", ignore_errors=True)
        out = _run(["cmake", "-S", ".", "-B", "build-warn",
                    "-DCMAKE_BUILD_TYPE=Debug",
                    "-DCMAKE_C_FLAGS=-Wall -Wextra",
                    "-DCMAKE_CXX_FLAGS=-Wall -Wextra",
                    # Objective-C / Objective-C++ compile with their own flag vars;
                    # without these, `.m`/`.mm` files build WITHOUT -Wall and no
                    # warnings surface.
                    "-DCMAKE_OBJC_FLAGS=-Wall -Wextra",
                    "-DCMAKE_OBJCXX_FLAGS=-Wall -Wextra",
                    "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"])
        out += "\n" + _run(["cmake", "--build", "build-warn"])
        return out
    if (root / "Makefile").exists() or (root / "makefile").exists():
        # Agent-authored Makefiles vary; force a rebuild via `make clean` (best
        # effort — ignored if there's no clean target) then run the default
        # target and hope warnings are enabled in their CFLAGS.
        _run(["make", "clean"])
        return _run(["make"])
    return ""
