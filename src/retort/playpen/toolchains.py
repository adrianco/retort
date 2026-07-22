"""Language toolchain preflight — ensure the compilers/test runners a run needs.

A Retort experiment's ``language`` factor decides which build/test toolchains the
scorers invoke (``go test``, ``cargo test``, ``dotnet build``, ``mvn``, …). If a
toolchain is missing the scorers either skip (neutral score) or the mechanical
conformance gate fails — silently biasing results *against* whatever language the
host happens not to have installed. That makes a cross-language comparison unfair
in exactly the way issue #32 flagged for Python deps.

This module maps each ``language`` level to the toolchain it needs, checks which
are present, and best-effort installs the missing ones via the platform package
manager (Homebrew on macOS, ``apt-get`` on Debian/Ubuntu) before the run starts.

It is deliberately best-effort: on an unsupported platform, with no package
manager, or on a failed install it records the failure and continues rather than
aborting — the scorers' existing skip-on-``FileNotFoundError`` behavior still
applies, so a run is never *worse off* than before this preflight existed.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# How long to allow a single toolchain install before giving up (seconds).
_INSTALL_TIMEOUT_S = 1800


@dataclass(frozen=True)
class Toolchain:
    """A language's build/test toolchain and how to install it."""

    language: str
    probe: str  # executable that must be on PATH for the scorers to build/test
    brew: tuple[str, ...]  # Homebrew formula(e) that provide it
    apt: tuple[str, ...]  # Debian/Ubuntu package(s) that provide it
    label: str  # human-friendly name for messages


# ``language`` factor level -> toolchain it needs. Keys are matched
# case-insensitively against the levels in workspace.yaml. Languages whose probe
# is normally preinstalled (python) carry no install mapping and are simply
# reported if absent.
TOOLCHAINS: dict[str, Toolchain] = {
    "python": Toolchain("python", "python3", (), ("python3",), "Python"),
    "typescript": Toolchain("typescript", "node", ("node",), ("nodejs",), "Node.js (TypeScript)"),
    "javascript": Toolchain("javascript", "node", ("node",), ("nodejs",), "Node.js"),
    "go": Toolchain("go", "go", ("go",), ("golang",), "Go"),
    "rust": Toolchain("rust", "cargo", ("rust",), ("cargo",), "Rust"),
    "java": Toolchain("java", "mvn", ("maven",), ("maven",), "Java (Maven)"),
    "csharp": Toolchain("csharp", "dotnet", ("dotnet",), ("dotnet-sdk",), ".NET SDK (C#)"),
    "clojure": Toolchain("clojure", "lein", ("leiningen",), ("leiningen",), "Clojure (Leiningen)"),
    "elixir": Toolchain("elixir", "mix", ("elixir",), ("elixir",), "Elixir"),
    "erlang": Toolchain("erlang", "rebar3", ("rebar3",), ("rebar3",), "Erlang (rebar3)"),
    # Systems / Apple languages (exploration — see docs/future-experiments.md
    # "More languages"). The probe is the compiler/driver; the scorers also need
    # CMake (C/C++) and coverage tooling — documented with the experiment.
    "c": Toolchain("c", "clang", ("llvm", "cmake", "lcov"), ("clang", "cmake", "lcov"), "C (clang + CMake)"),
    "cpp": Toolchain("cpp", "clang++", ("llvm", "cmake", "lcov"), ("clang", "cmake", "lcov"), "C++ (clang++ + CMake)"),
    "objc": Toolchain("objc", "clang", ("llvm",), (), "Objective-C (clang + Foundation, macOS)"),
    "swift": Toolchain("swift", "swift", ("swift",), (), "Swift (SwiftPM)"),
}
# Common aliases for the same toolchain.
for _alias, _canon in {"ts": "typescript", "js": "javascript", "c#": "csharp",
                       "dotnet": "csharp", "c++": "cpp", "cxx": "cpp",
                       "objective-c": "objc", "objectivec": "objc"}.items():
    TOOLCHAINS[_alias] = TOOLCHAINS[_canon]


@dataclass
class ToolchainStatus:
    """Result of checking (and maybe installing) one toolchain."""

    language: str
    label: str
    probe: str
    present: bool
    installed: bool = False  # True if this preflight installed it just now
    error: str | None = None  # set when an install was attempted and didn't work

    @property
    def ok(self) -> bool:
        return self.present


def required_toolchains(languages: Iterable[str]) -> list[Toolchain]:
    """De-duplicated toolchains needed by the given ``language`` levels.

    Unknown levels are ignored (a custom language with no scorer support isn't
    our business to install). Levels sharing a probe (typescript/javascript)
    collapse to one entry.
    """
    out: dict[str, Toolchain] = {}
    for lang in languages:
        tc = TOOLCHAINS.get(str(lang).strip().lower())
        if tc is not None and tc.probe not in out:
            out[tc.probe] = tc
    return list(out.values())


def _installer() -> tuple[str | None, Callable[[list[str]], list[str]] | None]:
    """Return ``(name, argv_builder)`` for this platform's package manager."""
    if sys.platform == "darwin" and shutil.which("brew"):
        return "brew", lambda pkgs: ["brew", "install", *pkgs]
    if sys.platform.startswith("linux") and shutil.which("apt-get"):

        def _apt(pkgs: list[str]) -> list[str]:
            base = ["apt-get", "install", "-y", *pkgs]
            if os.geteuid() != 0 and shutil.which("sudo"):
                return ["sudo", *base]
            return base

        return "apt-get", _apt
    return None, None


def ensure_toolchains(
    languages: Iterable[str],
    *,
    install: bool = True,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
) -> list[ToolchainStatus]:
    """Check (and optionally install) the toolchains the languages require.

    ``install=False`` only reports presence (used for ``--dry-run``). ``runner``
    and ``which`` are injectable for testing. Never raises for an install
    failure — the failure is recorded on the returned status and the run goes on.
    """
    statuses: list[ToolchainStatus] = []
    mgr_name, build_argv = _installer()

    for tc in required_toolchains(languages):
        if which(tc.probe) is not None:
            statuses.append(ToolchainStatus(tc.language, tc.label, tc.probe, present=True))
            continue

        if not install:
            statuses.append(ToolchainStatus(tc.language, tc.label, tc.probe, present=False))
            continue

        pkgs = tc.brew if mgr_name == "brew" else tc.apt if mgr_name == "apt-get" else ()
        if build_argv is None:
            err = "no supported package manager (need Homebrew or apt-get)"
        elif not pkgs:
            err = f"no {mgr_name} package mapping for {tc.label}"
        else:
            err = None

        if err is not None:
            statuses.append(ToolchainStatus(tc.language, tc.label, tc.probe, present=False, error=err))
            continue

        argv = build_argv(list(pkgs))
        logger.info("Installing %s toolchain: %s", tc.label, " ".join(argv))
        try:
            proc = runner(argv, capture_output=True, text=True, timeout=_INSTALL_TIMEOUT_S)
            rc = proc.returncode
            tail = (getattr(proc, "stderr", "") or getattr(proc, "stdout", "") or "").strip()
        except (OSError, subprocess.SubprocessError) as exc:
            rc, tail = 1, str(exc)

        now_present = which(tc.probe) is not None
        if now_present:
            statuses.append(
                ToolchainStatus(tc.language, tc.label, tc.probe, present=True, installed=True)
            )
        else:
            last = tail.splitlines()[-1] if tail else f"exit code {rc}"
            statuses.append(
                ToolchainStatus(tc.language, tc.label, tc.probe, present=False, error=last)
            )
    return statuses


def format_report(statuses: list[ToolchainStatus], *, installed_action: bool) -> list[str]:
    """Human-readable lines summarizing a preflight, for the CLI to echo."""
    lines: list[str] = []
    for s in statuses:
        if s.installed:
            lines.append(f"  ✓ {s.label}: installed ({s.probe})")
        elif s.present:
            lines.append(f"  ✓ {s.label}: present ({s.probe})")
        elif s.error:
            verb = "could not install" if installed_action else "missing"
            lines.append(f"  ⚠ {s.label}: {verb} — {s.error}. Runs in this language may fail to score.")
        else:
            lines.append(f"  ⚠ {s.label}: missing ({s.probe}). Install it or runs may fail to score.")
    return lines
