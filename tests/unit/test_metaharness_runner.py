"""Tests for the MetaHarness playpen runner (offline — no network, no node)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from retort.playpen.metaharness_runner import (
    MetaHarnessRunner,
    _parse_solver_telemetry,
    _resolve_routing,
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


class TestResolveRouting:
    def test_off_is_no_escalation(self):
        # iteration-2 parity: routing off, no explicit escalate → router stays off.
        for level in ("off", "none", "", "false", "OFF"):
            escalate, route = _resolve_routing(level, "")
            assert escalate == ""
            assert route is False

    def test_opus_level_escalates_to_frontier(self):
        escalate, route = _resolve_routing("opus", "")
        assert escalate == "anthropic/claude-opus-4.8"
        assert route is True

    def test_glm_level_escalates_to_stronger_cheap(self):
        escalate, route = _resolve_routing("glm", "")
        assert escalate == "z-ai/glm-5.2"
        assert route is True

    def test_on_defaults_to_opus(self):
        escalate, route = _resolve_routing("on", "")
        assert escalate == "anthropic/claude-opus-4.8"
        assert route is True

    def test_explicit_escalate_turns_router_on_even_when_routing_off(self):
        escalate, route = _resolve_routing("off", "gpt-5.2")
        assert escalate == "openai/gpt-5.2"
        assert route is True

    def test_explicit_escalate_overrides_routing_target(self):
        # An explicit escalate level wins over the routing factor's default target.
        escalate, route = _resolve_routing("opus", "glm-5.2")
        assert escalate == "z-ai/glm-5.2"
        assert route is True

    def test_unknown_routing_level_falls_back_to_opus(self):
        escalate, route = _resolve_routing("frontier", "")
        assert escalate == "anthropic/claude-opus-4.8"
        assert route is True


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
