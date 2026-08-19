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

import hashlib
import os
import sys
import time

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


# --- a hang is terminal, and the monitor can see the probe -------------------

def test_budget_bounds_every_phase_of_one_measurement():
    """The per-iteration timeouts alone permit 24 minutes per cell.

    3 warm-up + 10 timed launches at ITER_TIMEOUT_S, plus first_query,
    serve_latency and the factual check at their own timeouts, is 24 minutes of
    scoring for ONE run that will not answer — longer than the agent took to
    write it. The shared budget is what keeps a stalled server from turning
    scoring into the experiment.
    """
    from retort.scoring.scorers import factual_accuracy as fa
    from retort.scoring.scorers import runtime as rt

    # cold-start relaunches + first_query + serve_latency + the factual probe's
    # own handshake and its six candidate tool calls, each at its own timeout.
    unbounded = (
        (rt.WARMUP_ITERS + rt.TIMED_ITERS) * rt.ITER_TIMEOUT_S   # relaunch loop
        + rt.QUERY_TIMEOUT_S * 2                                 # first_query, serve
        + rt.ITER_TIMEOUT_S + rt.QUERY_TIMEOUT_S * 6             # factual
    )
    bounded = rt.PROBE_BUDGET_S + fa.FACTUAL_BUDGET_S
    assert unbounded > 20 * 60, "the ceiling this bounds is per CELL, not per run"
    assert bounded < unbounded / 4


def test_budget_slice_never_exceeds_what_is_left():
    from retort.scoring.scorers.runtime import _Budget

    b = _Budget(0.5)
    assert b.slice(30.0) <= 0.5
    assert b.slice(0.1) == pytest.approx(0.1, abs=0.05)
    b.deadline -= 10.0                      # pretend it elapsed
    assert b.spent() and b.slice(30.0) == 0.0


def test_a_hung_server_is_not_relaunched_thirteen_times(tmp_path, monkeypatch):
    """One timeout is enough evidence. Retrying spends six minutes re-proving it."""
    from retort.scoring.scorers import runtime as rt

    (tmp_path / "package.json").write_text(
        '{"name": "s", "scripts": {"start": "node server.js"}}')
    launches = []

    def _never_answers(proc, timeout, captured=None):
        launches.append(timeout)
        time.sleep(min(timeout, 0.05))      # burn the whole (tiny) window
        return None

    monkeypatch.setattr(rt, "ITER_TIMEOUT_S", 0.05)
    monkeypatch.setattr(rt, "_mcp_handshake", _never_answers)
    monkeypatch.setattr(rt, "_build_then_entry",
                        lambda d, l, r=None: ([sys.executable, "-c", "import time;time.sleep(9)"], ""))
    res = rt._probe_brazil(tmp_path, "typescript", rt._Budget(30.0))

    assert res.ok is False
    # One launch, not WARMUP_ITERS + TIMED_ITERS + README candidates.
    assert len(launches) == 1, f"relaunched a hung server {len(launches)} times"
    assert res.cold_start_ms is None        # a non-result, never a zero


def test_probe_status_lets_the_monitor_see_scoring(tmp_path):
    """Scoring launches the model's program, not an agent — so it must announce."""
    from retort.scoring import probe_status

    base = str(tmp_path)
    assert probe_status.read(os.getpid(), base) is None
    with probe_status.announcing("measuring runtime (go)", "go", base) as update:
        crumb = probe_status.read(os.getpid(), base)
        assert crumb["phase"] == "measuring runtime (go)"
        update("checking answers (go)")
        assert probe_status.read(os.getpid(), base)["phase"] == "checking answers (go)"
    assert probe_status.read(os.getpid(), base) is None


def test_probe_status_ignores_a_crashed_runs_leftover(tmp_path):
    """A stale crumb must not report a dead process as busy scoring."""
    from retort.scoring import probe_status

    base = str(tmp_path)
    probe_status.announce("measuring runtime (c)", "c", base)
    assert probe_status.read(os.getpid(), base) is not None
    assert probe_status.read(os.getpid(), base, max_age_s=-1.0) is None


def test_probe_kills_the_whole_process_tree_not_just_the_launcher(tmp_path):
    """`npm start` forks node; killing npm reparents the server, it doesn't stop it.

    This repo has an MCP server from exp-56 that outlived its probe by thirteen
    days. A leaked server holds memory and a port while LATER cells are being
    timed — the one thing a wall-clock measurement cannot tolerate.
    """
    import subprocess

    from retort.scoring.scorers import runtime as rt

    marker = tmp_path / "grandchild.pid"
    launcher = tmp_path / "launcher.py"
    launcher.write_text(
        "import subprocess, sys, time, pathlib\n"
        "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        f"pathlib.Path({str(marker)!r}).write_text(str(c.pid))\n"
        "time.sleep(120)\n"
    )
    proc = rt._spawn([sys.executable, str(launcher)], tmp_path, subprocess.DEVNULL)
    for _ in range(100):
        if marker.is_file():
            break
        time.sleep(0.05)
    grandchild = int(marker.read_text())
    rt._reap(proc)

    time.sleep(0.3)
    with pytest.raises(OSError):          # ESRCH — the grandchild died with the group
        os.kill(grandchild, 0)


@pytest.mark.parametrize("fn", ["_first_query", "_serve_latency"])
def test_phase_helpers_default_their_own_budget(fn, tmp_path, monkeypatch):
    """Called without a budget they must still work, not raise AttributeError.

    Both take `budget=None` and call `budget.slice(...)`. _probe_brazil always
    passes one, so this only breaks for a direct caller — which is exactly the
    kind of latent crash that surfaces during a run, at the worst moment.
    """
    from retort.scoring.scorers import runtime as rt

    # The handshake must SUCCEED, or the function returns before it ever touches
    # the budget and the test passes while the bug is still there — which is
    # exactly what the first version of this test did.
    monkeypatch.setattr(rt, "_mcp_handshake", lambda *a, **k: {
        "result": {"tools": [{"name": "get_team", "inputSchema": {}}]}})
    monkeypatch.setattr(rt, "mcp_send", lambda *a, **k: True)   # must SUCCEED
    monkeypatch.setattr(rt, "mcp_await_id", lambda *a, **k: None)
    monkeypatch.setattr(rt, "_pick_working_call", lambda *a, **k: None)
    result = getattr(rt, fn)([sys.executable, "-c", "pass"], tmp_path)
    assert result is None or result[0] is None      # a non-result, not a crash


def test_the_verdict_records_what_was_actually_installed(tmp_path, monkeypatch):
    """A declared requirement and a resolved version are different facts.

    An archived run declares `mcp>=1.28,<3`. That HAS an upper bound, so
    _cap_majors leaves it alone, mcp 2.x is installed, and the server dies with
    `AttributeError: 'Server' object has no attribute 'list_tools'` — an API
    that exists in 1.x. Whether that is the model's defect (its own manifest
    claims 2.x works) or an artifact of resolving years later is undecidable
    from the traceback. Record the versions and it becomes decidable.
    """
    from retort.scoring.scorers import runtime as rt

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "s"\ndependencies = ["mcp>=1.28,<3"]\n'
        '[project.scripts]\ns = "s.server:main"\n')
    pkg = tmp_path / "s"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "server.py").write_text("def main():\n    pass\n")

    fake_py = tmp_path / "venv" / "bin" / "python"
    fake_py.parent.mkdir(parents=True)
    fake_py.write_text("")
    monkeypatch.setattr(rt, "_probe_venv", lambda deps: fake_py)
    monkeypatch.setattr(rt, "_venv_freeze", lambda py: ["mcp==2.1.0", "anyio==4.6.0"])
    monkeypatch.setattr(rt, "_importable", lambda py, d, t: "")

    resolved: dict = {}
    cmd, note = rt._python_entry(tmp_path, resolved)
    assert cmd is not None
    assert resolved["declared"] == ["mcp>=1.28,<3"]
    assert resolved["capped"] is False        # the run's OWN bound, left alone
    assert "mcp==2.1.0" in resolved["installed"]


def test_deps_reach_the_json_the_reader_actually_opens():
    """Recording it internally is useless if it never lands in the archive."""
    from retort.scoring.scorers.factual_accuracy import FactualResult
    from retort.scoring.scorers.runtime import RuntimeResult

    rt_res = RuntimeResult(task="t", language="python", ok=False,
                           deps={"installed": ["mcp==2.1.0"]})
    fa_res = FactualResult(deps={"installed": ["mcp==2.1.0"]})
    assert rt_res.as_dict()["deps"]["installed"] == ["mcp==2.1.0"]
    assert fa_res.as_dict()["deps"]["installed"] == ["mcp==2.1.0"]


def test_an_unresolvable_dep_set_is_recorded_too(tmp_path, monkeypatch):
    """A venv that could not be built is the most important case to record.

    "could not build a venv" and "the program is broken" are different facts,
    and the note alone has never been enough to separate them.
    """
    from retort.scoring.scorers import runtime as rt

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "s"\ndependencies = ["mcp>=1.28,<3"]\n'
        '[project.scripts]\ns = "s.server:main"\n')
    pkg = tmp_path / "s"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "server.py").write_text("def main():\n    pass\n")
    monkeypatch.setattr(rt, "_probe_venv", lambda deps: None)

    resolved: dict = {}
    cmd, note = rt._python_entry(tmp_path, resolved)
    assert cmd is None
    assert resolved["declared"] == ["mcp>=1.28,<3"]
    assert resolved["attempts"] and resolved["attempts"][0]["built"] is False
    assert resolved["installed"] == []


def test_a_declared_upper_bound_is_left_alone():
    """`mcp>=1.2` is the absence of a claim; `mcp>=1.28,<3` is a claim.

    Capping the second would overrule the run's own stated constraint and hide a
    real defect: exp-58 rep3 declares `<3`, uses the low-level API mcp 2.0
    removed, and fails — while rep1 (`<2`, 1.x code) and rep2 (`>=2,<3`, 2.x
    code) both pass. The model can match its manifest to its code and did, in
    both directions. See docs/runtime-measurement.md before changing this.
    """
    from retort.scoring.scorers.runtime import _cap_majors

    assert _cap_majors(["mcp>=1.2"]) == ["mcp>=1.2,<2"]      # no claim -> cap
    assert _cap_majors(["mcp>=1.28,<3"]) == ["mcp>=1.28,<3"]  # a claim -> keep
    assert _cap_majors(["mcp>=2,<3"]) == ["mcp>=2,<3"]


def test_a_transient_venv_failure_does_not_destroy_a_working_cache_entry(tmp_path, monkeypatch):
    """One network blip was costing the cached venv AND the run's measurement.

    Building a venv reaches the network, so it fails transiently — PyPI
    rate-limits a sweep that builds many in quick succession. Measured: 7 python
    runs in one archive sweep recorded "could not build a venv" for dependency
    sets that resolved fine on a manual retry seconds later, and one of them had
    a working cached venv until _probe_venv deleted it on the way out.
    """
    import subprocess as sp

    from retort.scoring.scorers import runtime as rt

    monkeypatch.setenv("RETORT_HOME", str(tmp_path))
    deps = ["mcp>=1.28,<3"]
    key = hashlib.sha1("\n".join(deps).encode()).hexdigest()[:12]
    venv_dir = tmp_path / "cache" / "probe-venvs" / key
    (venv_dir / "bin").mkdir(parents=True)
    (venv_dir / "bin" / "python").write_text("#!/bin/sh\n")   # a working entry

    calls = {"n": 0}

    def flaky(cmd, **kw):
        calls["n"] += 1
        raise sp.CalledProcessError(1, cmd, stderr=b"ERROR: 429 Too Many Requests")

    monkeypatch.setattr(rt.subprocess, "run", flaky)
    # py.exists() is True, so _probe_venv returns the cache entry without building
    assert rt._probe_venv(deps) is not None
    assert calls["n"] == 0, "a usable cached venv must not be rebuilt"
    assert (venv_dir / "bin" / "python").exists(), "the cache entry was destroyed"


def test_a_failed_venv_build_says_why(tmp_path, monkeypatch):
    """"could not build a venv" hid seven transient network failures."""
    import subprocess as sp

    from retort.scoring.scorers import runtime as rt

    monkeypatch.setenv("RETORT_HOME", str(tmp_path))
    monkeypatch.setattr(rt.subprocess, "run", lambda cmd, **kw: (_ for _ in ()).throw(
        sp.CalledProcessError(1, cmd, stderr=b"ERROR: 429 Too Many Requests")))

    assert rt._probe_venv(["mcp>=9000"]) is None
    key = hashlib.sha1("mcp>=9000".encode()).hexdigest()[:12]
    assert "429" in rt._VENV_ERRORS.get(key, ""), "the cause was swallowed"
