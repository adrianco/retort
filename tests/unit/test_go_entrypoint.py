"""Go entrypoint discovery for the runtime/factual probes.

`go build -o X .` assumes the module root is the main package. Half the archived
runs use the idiomatic layout instead — a library at the root and
`cmd/<name>/main.go` — and for a NON-main package `go build` emits a package
ARCHIVE, exits 0, and writes it mode 0644. The probe then failed with
"Permission denied" on a build it believed had succeeded, and the factual gate
recorded a working implementation as broken.

Exit status is not enough: the fix asks `go list` which package is main and
verifies the artifact is executable. It was originally verified only against one
archived run, which is why these exist.
"""
from __future__ import annotations

import subprocess

import pytest

from retort.scoring.scorers import runtime as rt


class _Result:
    def __init__(self, stdout="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


@pytest.fixture
def go_module(tmp_path):
    (tmp_path / "go.mod").write_text("module brazilian-soccer-mcp\n\ngo 1.22\n")
    return tmp_path


def _patch_go(monkeypatch, list_stdout, *, make_exe=True, exe_mode=0o755,
              build_rc=0):
    """Stand in for the go toolchain: `go list` output, then `go build`."""
    calls = []

    def fake_run(cmd, *a, **k):
        calls.append(cmd)
        if "list" in cmd:
            return _Result(stdout=list_stdout)
        if "build" in cmd:
            if make_exe:
                out = k.get("cwd") or a[0]
                from pathlib import Path
                p = Path(out) / ".retort-bin"
                p.write_bytes(b"\x7fELF fake")
                p.chmod(exe_mode)
            return _Result(returncode=build_rc)
        return _Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_idiomatic_cmd_layout_builds_the_cmd_package(go_module, monkeypatch):
    """The regression: main lives in cmd/<name>, not at the module root."""
    listing = ("soccer brazilian-soccer-mcp\n"
               "main brazilian-soccer-mcp/cmd/brazilian-soccer-mcp\n")
    calls = _patch_go(monkeypatch, listing)

    cmd, note = rt._build_then_entry(go_module, "go")

    assert note == ""
    assert cmd == [str(go_module / ".retort-bin")]
    build = next(c for c in calls if "build" in c)
    assert build[-1] == "brazilian-soccer-mcp/cmd/brazilian-soccer-mcp"


def test_flat_layout_still_builds_the_root(go_module, monkeypatch):
    calls = _patch_go(monkeypatch, "main brazilian-soccer-mcp\n")

    cmd, note = rt._build_then_entry(go_module, "go")

    assert note == ""
    assert next(c for c in calls if "build" in c)[-1] == "brazilian-soccer-mcp"


def test_cmd_path_preferred_when_several_mains_exist(go_module, monkeypatch):
    """A repo may also build a helper tool; the server is the one under cmd/."""
    listing = ("main brazilian-soccer-mcp/tools/seed\n"
               "main brazilian-soccer-mcp/cmd/server\n")
    calls = _patch_go(monkeypatch, listing)

    rt._build_then_entry(go_module, "go")

    assert next(c for c in calls if "build" in c)[-1] == "brazilian-soccer-mcp/cmd/server"


def test_non_executable_archive_is_a_failure_not_a_binary(go_module, monkeypatch):
    """`go build` on a library exits 0 and writes a 0644 package archive.

    This is the exact shape that produced "Permission denied" from a build the
    probe thought had succeeded.
    """
    _patch_go(monkeypatch, "soccer brazilian-soccer-mcp\n", exe_mode=0o644)

    cmd, note = rt._build_then_entry(go_module, "go")

    assert cmd is None
    assert "non-executable" in note and "no main package" in note


def test_no_go_mod_is_an_explicit_non_result(tmp_path):
    cmd, note = rt._build_then_entry(tmp_path, "go")
    assert cmd is None
    assert note == "no go.mod"


def test_failed_build_names_the_target(go_module, monkeypatch):
    _patch_go(monkeypatch, "main m/cmd/x\n", make_exe=False, build_rc=1)

    cmd, note = rt._build_then_entry(go_module, "go")

    assert cmd is None
    assert "m/cmd/x" in note


def test_go_list_failure_falls_back_to_the_module_root(go_module, monkeypatch):
    """A `go list` that errors must not block the flat case from building."""
    def fake_run(cmd, *a, **k):
        if "list" in cmd:
            raise OSError("go list exploded")
        if "build" in cmd:
            from pathlib import Path
            p = Path(k.get("cwd")) / ".retort-bin"
            p.write_bytes(b"x"); p.chmod(0o755)
        return _Result()
    monkeypatch.setattr(subprocess, "run", fake_run)

    cmd, note = rt._build_then_entry(go_module, "go")

    assert note == ""
    assert cmd == [str(go_module / ".retort-bin")]
