"""Entrypoint discovery for the runtime probe.

These are regression tests for a measurement bias, not for a crash. The probe
used to look only for a TOP-LEVEL server.py/main.py and to run it with the
SYSTEM interpreter. Both choices silently excluded runs:

  - a package layout (`pkg/server.py`, importing `from .x import y`) has no
    top-level script, so it was reported as having no entrypoint;
  - an implementation importing the real `mcp` SDK could not start, because the
    SDK is not installed system-wide.

Neither exclusion was random. 21 of 36 Python brazil runs import the SDK, so the
runs that survived were the hand-rolled stdlib ones — the fastest-starting subset
by construction. Measured properly the same task takes 1386 ms with the SDK and
38 ms without: the "language" number was really an implementation number.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from retort.scoring.scorers import runtime as rt


@pytest.fixture
def fake_venv(monkeypatch):
    """Skip the real pip install; return a stable interpreter path."""
    monkeypatch.setattr(rt, "_probe_venv", lambda deps: Path("/venv/bin/python"))
    return "/venv/bin/python"


def test_declared_deps_reads_pyproject_and_requirements(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["mcp>=1.2", "orjson"]\n'
    )
    (tmp_path / "requirements.txt").write_text("# comment\nhttpx==0.27\n\n-e .\n")
    deps = rt._declared_deps(tmp_path)
    assert deps == ["httpx==0.27", "mcp>=1.2", "orjson"]


def test_declared_deps_drops_test_only_packages(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest>=7.4\nmcp\n")
    assert rt._declared_deps(tmp_path) == ["mcp"]


def test_package_layout_starts_with_dash_m_not_a_path(tmp_path, fake_venv):
    """The regression: `python pkg/server.py` cannot work here.

    server.py does `from .formatting import ...`, which raises "attempted
    relative import with no known parent package" when run as a path. It has to
    be `-m pkg.server`.
    """
    pkg = tmp_path / "brazilian_soccer"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    (pkg / "server.py").write_text("from .formatting import fmt\n")

    cmd, note = rt._python_entry(tmp_path)

    assert note == ""
    assert cmd == [fake_venv, "-m", "brazilian_soccer.server"]


def test_declared_console_script_wins_over_convention(tmp_path, fake_venv):
    pkg = tmp_path / "brazilian_soccer"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    (pkg / "server.py").touch()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = []\n\n'
        '[project.scripts]\n'
        'brazilian-soccer-mcp = "brazilian_soccer.server:main"\n'
        '\n[tool.setuptools]\n'
    )

    cmd, note = rt._python_entry(tmp_path)

    assert note == ""
    assert cmd == [fake_venv, "-c",
                   "from brazilian_soccer.server import main; main()"]


def test_server_script_preferred_when_a_cli_is_also_declared(tmp_path, fake_venv):
    """Projects declare both a server and a CLI; measuring the CLI is wrong."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = []\n\n'
        '[project.scripts]\n'
        'brazilian-soccer = "brazilian_soccer.cli:main"\n'
        'brazilian-soccer-mcp = "brazilian_soccer.server:main"\n'
    )

    cmd, _ = rt._python_entry(tmp_path)

    assert "brazilian_soccer.server" in cmd[2]
    assert "cli" not in cmd[2]


def test_dunder_main_beats_server_module(tmp_path, fake_venv):
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    (pkg / "__main__.py").touch()
    (pkg / "server.py").touch()

    cmd, _ = rt._python_entry(tmp_path)

    assert cmd == [fake_venv, "-m", "app"]


def test_plain_top_level_script_still_works(tmp_path, fake_venv):
    """The hand-rolled stdlib implementations must keep measuring."""
    (tmp_path / "server.py").write_text("import json, sys\n")

    cmd, note = rt._python_entry(tmp_path)

    assert note == ""
    assert cmd == [fake_venv, "server.py"]


def test_no_entrypoint_is_an_explicit_non_result(tmp_path, fake_venv):
    (tmp_path / "notes.md").write_text("nothing runnable here\n")

    cmd, note = rt._python_entry(tmp_path)

    assert cmd is None
    assert "no python entrypoint" in note


def test_unbuildable_venv_is_reported_not_silently_downgraded(tmp_path, monkeypatch):
    """A failed venv must NOT fall back to the system interpreter.

    Falling back is what produced the bias: the run then either fails to import
    its SDK and looks broken, or happens to need nothing and measures fast.
    """
    monkeypatch.setattr(rt, "_probe_venv", lambda deps: None)
    (tmp_path / "server.py").touch()
    (tmp_path / "requirements.txt").write_text("mcp\n")

    cmd, note = rt._python_entry(tmp_path)

    assert cmd is None
    assert "venv" in note and "mcp" in note
