"""Tests for playpen runner types and DockerRunner."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from retort.playpen.runner import PlaypenRunner, RunArtifacts, StackConfig, TaskSpec
from retort.playpen.docker_runner import DockerRunner


class TestStackConfig:
    def test_from_run_config_basic(self):
        config = {"language": "python", "agent": "claude-code", "framework": "fastapi"}
        stack = StackConfig.from_run_config(config)
        assert stack.language == "python"
        assert stack.agent == "claude-code"
        assert stack.framework == "fastapi"
        assert stack.extra == {}

    def test_from_run_config_with_extras(self):
        config = {
            "language": "go",
            "agent": "cursor",
            "framework": "stdlib",
            "app_type": "cli-tool",
        }
        stack = StackConfig.from_run_config(config)
        assert stack.language == "go"
        assert stack.extra == {"app_type": "cli-tool"}

    def test_from_run_config_missing_fields(self):
        config = {"language": "rust"}
        stack = StackConfig.from_run_config(config)
        assert stack.language == "rust"
        assert stack.agent == "unknown"
        assert stack.framework == "unknown"


class TestRunArtifacts:
    def test_succeeded_true(self):
        a = RunArtifacts(exit_code=0)
        assert a.succeeded is True

    def test_succeeded_false(self):
        a = RunArtifacts(exit_code=1)
        assert a.succeeded is False

    def test_to_dict(self):
        a = RunArtifacts(exit_code=0, duration_seconds=5.0, token_count=1000)
        d = a.to_dict()
        assert d["exit_code"] == 0
        assert d["duration_seconds"] == 5.0
        assert d["token_count"] == 1000
        assert d["succeeded"] is True

    def test_to_json(self):
        a = RunArtifacts(exit_code=0)
        j = a.to_json()
        assert '"exit_code": 0' in j


class TestDockerRunner:
    def test_implements_protocol(self):
        runner = DockerRunner()
        assert isinstance(runner, PlaypenRunner)

    def test_provision_creates_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = DockerRunner(work_dir=Path(tmpdir))
            stack = StackConfig(language="python", agent="test", framework="fastapi")
            task = TaskSpec(name="test-task", description="Test", prompt="Do something")

            env_id = runner.provision(stack, task)
            assert env_id.startswith("retort-")

            # Check workspace was created
            env_dir = Path(tmpdir) / env_id
            assert env_dir.exists()
            assert (env_dir / "TASK.md").exists()
            assert (env_dir / "stack.json").exists()

            runner.teardown(env_id)
            assert not env_dir.exists()

    def test_simulate_run(self):
        """When Docker isn't available, runner falls back to simulation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = DockerRunner(work_dir=Path(tmpdir))
            stack = StackConfig(language="python", agent="test", framework="fastapi")
            task = TaskSpec(name="test-task", description="Test", prompt="Do something")

            env_id = runner.provision(stack, task)
            artifacts = runner.execute(env_id, stack, task)

            # In CI/test environments without Docker, we get simulated results
            assert artifacts.duration_seconds >= 0
            assert isinstance(artifacts.exit_code, int)

            runner.teardown(env_id)
