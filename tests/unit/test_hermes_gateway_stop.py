"""Hermes >= v0.23.0 runs the agent in a detached gateway daemon; retort stops it per run."""

from __future__ import annotations

import subprocess as sp

from retort.playpen import local_runner


def test_stop_hermes_gateway_calls_the_runs_own_binary(monkeypatch):
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return sp.CompletedProcess(cmd, 0, stdout="Stopped", stderr="")

    monkeypatch.setattr(local_runner.subprocess, "run", run)
    assert local_runner._stop_hermes_gateway("/opt/hermes/bin/hermes") is True
    # --yes: without it `stop` refuses while the just-finished turn is still
    # listed live (exp-96: 5 of 6 stops failed that way).
    assert calls == [["/opt/hermes/bin/hermes", "gateway", "stop", "--yes"]]


def test_stop_hermes_gateway_failure_is_reported_not_raised(monkeypatch):
    def run(cmd, **kw):
        raise sp.TimeoutExpired(cmd, 60)

    monkeypatch.setattr(local_runner.subprocess, "run", run)
    assert local_runner._stop_hermes_gateway("hermes") is False


def test_a_killed_hermes_run_stops_the_gateway_too(tmp_path, monkeypatch):
    """Killing the oneshot client leaves the turn running inside the gateway
    (exp-96: a timed-out run went on 66 min, through the next run). The
    kill path must stop the gateway, not only the success path."""
    import sys
    from pathlib import Path

    from retort.config.schema import LocalAgentConfig
    from retort.playpen.runner import StackConfig, TaskSpec

    sys.path.insert(0, str(Path(__file__).parent))
    from test_runner import _fake_guard

    stopped = []
    monkeypatch.setattr(local_runner, "_stop_hermes_gateway",
                        lambda hb: stopped.append(hb) or True)
    monkeypatch.setattr(local_runner, "_run_with_progress_guard",
                        _fake_guard(kill_reason="wall", elapsed=3601.0))
    runner = local_runner.LocalRunner(
        work_dir=tmp_path,
        local_agents={"hermes-x": LocalAgentConfig(
            harness="hermes", model="llamacpp/M", bin="/opt/h/hermes")},
    )
    stack = StackConfig(language="go", agent="hermes-x", framework="none")
    env_id = runner.provision(stack, TaskSpec(name="t", description="d", prompt="hi"))
    art = runner.execute(env_id, stack, TaskSpec(name="t", description="d", prompt="hi"))
    assert art.exit_code == 124
    assert stopped == ["/opt/h/hermes"]
    assert art.metadata["hermes_gateway_stopped"] == "True"


def test_hung_interpreter_is_detected(tmp_path):
    """A python3 that never starts is reported; a healthy one is not."""
    import os
    import stat

    bad, good = tmp_path / "bad", tmp_path / "good"
    bad.mkdir(); good.mkdir()
    (bad / "python3").write_text("#!/bin/sh\n/bin/sleep 30\n")
    (good / "python3").write_text("#!/bin/sh\nexit 0\n")
    for d in (bad, good):
        (d / "python3").chmod(0o755)
    env = {"PATH": f"{good}{os.pathsep}{bad}"}
    assert local_runner._hung_interpreters(env, timeout=1.0) == [str(bad / "python3")]
    assert local_runner._hung_interpreters({"PATH": str(good)}, timeout=1.0) == []


def test_hung_interpreter_fails_the_run_fast(tmp_path, monkeypatch):
    from retort.playpen.runner import StackConfig, TaskSpec

    monkeypatch.setattr(local_runner, "_hung_interpreters", lambda env, timeout=20.0: ["/x/python3"])
    ran = []
    monkeypatch.setattr(local_runner, "_run_with_progress_guard",
                        lambda *a, **k: ran.append(1))
    runner = local_runner.LocalRunner(work_dir=tmp_path)
    stack = StackConfig(language="go", agent="claude-code", framework="none")
    task = TaskSpec(name="t", description="d", prompt="hi")
    env_id = runner.provision(stack, task)
    art = runner.execute(env_id, stack, task)
    assert art.exit_code == 125 and "HARNESS" in art.stderr and not ran


def test_pin_hermes_toolchain_writes_path_and_registers_it(tmp_path, monkeypatch):
    """#71: the agent's login-shell terminal must resolve the scorer's PATH."""
    import yaml

    monkeypatch.setenv("RETORT_HOME", str(tmp_path / "rh"))
    hh = tmp_path / "hh"
    hh.mkdir()
    (hh / "config.yaml").write_text(yaml.safe_dump({"model": {"default": "m"}}))
    env = {"PATH": "/opt/homebrew/bin:/usr/bin", "HERMES_HOME": str(hh)}
    script = local_runner._pin_hermes_toolchain(env)
    assert "export PATH=/opt/homebrew/bin:/usr/bin" in script.read_text()
    cfg = yaml.safe_load((hh / "config.yaml").read_text())
    assert cfg["terminal"]["shell_init_files"] == [str(script)]
    assert cfg["model"] == {"default": "m"}
    local_runner._pin_hermes_toolchain(env)  # idempotent: not registered twice
    cfg = yaml.safe_load((hh / "config.yaml").read_text())
    assert cfg["terminal"]["shell_init_files"] == [str(script)]


def test_find_skill_path_from_a_relative_start(tmp_path, monkeypatch):
    """recover passes a relative --experiment-dir; the walk must still go up."""
    from pathlib import Path

    (tmp_path / "skills" / "evaluate-run").mkdir(parents=True)
    (tmp_path / "skills" / "evaluate-run" / "SKILL.md").write_text("x")
    (tmp_path / "experiments" / "o" / "exp" / "runs").mkdir(parents=True)
    monkeypatch.chdir(tmp_path / "experiments" / "o")
    assert local_runner._find_skill_path("evaluate-run", start=Path("exp/runs")) is not None
