"""Tests for the MetaHarness playpen runner (offline — no network, no node)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from retort.playpen.metaharness_runner import (
    MetaHarnessRunner,
    _parse_solver_telemetry,
)
from retort.playpen.runner import PlaypenRunner, StackConfig, TaskSpec


class TestMetaHarnessRunner:
    def test_implements_protocol(self):
        assert isinstance(MetaHarnessRunner(), PlaypenRunner)

    def test_provision_creates_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = MetaHarnessRunner(work_dir=Path(tmpdir))
            stack = StackConfig(language="python", agent="metaharness", framework="flask")
            task = TaskSpec(name="t", description="d", prompt="Build a thing")
            env_id = runner.provision(stack, task)
            env_dir = Path(tmpdir) / env_id
            assert env_id.startswith("retort-")
            assert (env_dir / "TASK.md").read_text() == "Build a thing"
            stack_json = json.loads((env_dir / "stack.json").read_text())
            assert stack_json["language"] == "python"
            assert stack_json["agent"] == "metaharness"
            runner.teardown(env_id)

    def test_execute_errors_clearly_when_solver_unset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = MetaHarnessRunner(work_dir=Path(tmpdir), solver=None)
            runner.solver = None  # force unset even if env provides one
            stack = StackConfig(language="python", agent="metaharness", framework="flask")
            task = TaskSpec(name="t", description="d", prompt="Build a thing")
            env_id = runner.provision(stack, task)
            artifacts = runner.execute(env_id, stack, task)
            assert artifacts.exit_code == 1
            assert "METAHARNESS_SOLVER" in artifacts.stderr

    def test_execute_errors_when_solver_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = MetaHarnessRunner(work_dir=Path(tmpdir), solver="/no/such/solver.mjs")
            stack = StackConfig(language="python", agent="metaharness", framework="flask")
            task = TaskSpec(name="t", description="d", prompt="x")
            env_id = runner.provision(stack, task)
            artifacts = runner.execute(env_id, stack, task)
            assert artifacts.exit_code == 1
            assert "not found" in artifacts.stderr


class TestSolverTelemetry:
    def test_prefers_result_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "metaharness-result.json"
            p.write_text(json.dumps({
                "tokens": 1234, "cost": 0.0042, "steps": 9,
                "calls": 9, "model": "deepseek/deepseek-v4-pro", "escalated": False,
            }))
            tokens, cost, meta = _parse_solver_telemetry("ignored", p)
            assert tokens == 1234
            assert abs(cost - 0.0042) < 1e-9
            assert meta["steps"] == 9
            assert meta["escalated"] is False

    def test_falls_back_to_stdout_last_json(self):
        stdout = "noise line\n" + json.dumps({"tokens": 50, "cost": 0.001, "model": "x", "escalated": True})
        tokens, cost, meta = _parse_solver_telemetry(stdout, Path("/no/such/file.json"))
        assert tokens == 50
        assert meta["escalated"] is True

    def test_empty_is_zero(self):
        tokens, cost, meta = _parse_solver_telemetry("", Path("/no/such/file.json"))
        assert tokens == 0
        assert cost == 0.0
        assert meta == {}
