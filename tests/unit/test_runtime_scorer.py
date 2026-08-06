"""Entrypoint discovery for the runtime probe.

These are regression tests for a measurement bias, not for a crash. The probe
used to look only for a TOP-LEVEL server.py/main.py and to run it with the
SYSTEM interpreter. Both choices silently excluded runs:

  - a package layout (`pkg/server.py`, importing `from .x import y`) has no
    top-level script, so it was reported as having no entrypoint;
  - a project declaring dependencies could not start, because they are not
    installed system-wide.

The exclusions were not random with respect to what was being measured: only
2 of 11 Python runs measured, and both were hand-rolled stdlib servers. Fixing
discovery took that to 7 of 11 and widened the observed Python range from
38-42 ms to 32-1622 ms — a 50x spread inside one language.

Deliberately NOT claimed here: that importing the `mcp` SDK explains the spread.
That was the first hypothesis and it did not survive checking — the SDK imports
in these runs sit inside try/except blocks, so they are lazy, and a grep anchored
at line start had counted them wrongly. The cause found by reading the two
extreme runs is eager-vs-lazy DATA loading; see the tools/call section below.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from retort.scoring.scorers import runtime as rt


@pytest.fixture
def fake_venv(monkeypatch):
    """Skip the real pip install AND the import smoke-test.

    _python_entry verifies the chosen entry actually imports in the venv it
    built — that is what recovers a run whose open-ended `mcp>=1.2` now
    resolves to a 2.0 that removed the module it needs. With a fake interpreter
    there is nothing to import into, so stub it as "imports cleanly".
    """
    monkeypatch.setattr(rt, "_probe_venv", lambda deps: Path("/venv/bin/python"))
    monkeypatch.setattr(rt, "_importable", lambda py, run_dir, module: "")
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


# --- synthesized tools/call -------------------------------------------------
#
# Cold start alone is not comparable between implementations, and reading it as
# if it were produced a 29x "difference" between two runs of the SAME model on
# the SAME task. `tools/list` is protocol metadata: an implementation that loads
# 42k rows at import answers it having done the work, one that streams lazily
# (`yield from csv.DictReader(...)`) answers it having done none.
#
# Measured on the same machine: the lazy run starts in 41 ms and takes 461 ms to
# answer a real question; the eager run starts in 1109 ms and answers in 2 ms.
# Cold start says 27x apart; time-to-first-answer says 2.2x, the other way round.
# So the call below is what makes the number mean anything.

def test_synthesized_args_cover_required_properties_by_name():
    schema = {
        "type": "object",
        "properties": {
            "team_a": {"type": "string"},
            "team_b": {"type": "string"},
            "season": {"type": "integer"},
            "note": {"type": "string"},
        },
        "required": ["team_a", "team_b", "season"],
    }
    args = rt._synthesize_args(schema)

    assert set(args) == {"team_a", "team_b", "season"}     # optional ones omitted
    assert args["team_a"] != args["team_b"]                # head_to_head needs two
    assert isinstance(args["season"], int)


def test_synthesized_args_honour_declared_type_over_name_match():
    """A season declared as a string must not be sent as an int."""
    schema = {"properties": {"season": {"type": "string"}}, "required": ["season"]}
    assert rt._synthesize_args(schema)["season"] == "2019"


def test_synthesized_args_fall_back_by_type_for_unknown_names():
    schema = {
        "properties": {"zzz": {"type": "integer"}, "flag": {"type": "boolean"}},
        "required": ["zzz", "flag"],
    }
    args = rt._synthesize_args(schema)
    assert args["zzz"] == 1
    assert args["flag"] is False


def test_no_required_properties_yields_empty_arguments():
    assert rt._synthesize_args({"properties": {"team": {"type": "string"}}}) == {}


def test_data_touching_tools_are_tried_before_metadata_tools():
    """`list_teams` may be served from an index without loading the matches."""
    names = ["list_teams", "team_stats", "ping", "find_matches"]

    def rank(name: str) -> int:
        low = name.lower()
        for i, pref in enumerate(rt._QUERY_PREFERENCE):
            if pref in low:
                return i
        return len(rt._QUERY_PREFERENCE)

    assert sorted(names, key=rank)[0] == "team_stats"
    assert rank("ping") == len(rt._QUERY_PREFERENCE)
