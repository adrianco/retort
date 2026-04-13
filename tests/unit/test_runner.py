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


class TestLocalRunnerSupportFiles:
    def test_provision_copies_support_files(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        # A fake support repo (e.g. brazil-bench/benchmark-template).
        support = tmp_path / "support"
        support.mkdir()
        (support / "README.md").write_text("# brazil-bench\n")
        (support / "data").mkdir()
        (support / "data" / "matches.csv").write_text("id,team\n1,SP\n")
        (support / ".git").mkdir()
        (support / ".git" / "config").write_text("[core]\n")  # source git → skipped

        work = tmp_path / "work"
        runner = LocalRunner(work_dir=work)
        stack = StackConfig(language="python", agent="claude-code", framework="fastapi")
        task = TaskSpec(
            name="test-with-support",
            description="task with support files",
            prompt="Do the thing using data/matches.csv",
            support_dir=support,
        )

        env_id = runner.provision(stack, task)
        env_dir = work / env_id

        # Support files copied
        assert (env_dir / "README.md").exists()
        assert (env_dir / "data" / "matches.csv").exists()
        assert (env_dir / "data" / "matches.csv").read_text().startswith("id,team")

        # Source .git NOT copied — the env's .git is from a fresh `git
        # init`, which never has the source's `[core]` line in its config.
        env_git_config = (env_dir / ".git" / "config").read_text()
        assert "[core]\n" not in env_git_config or "filemode" in env_git_config

        # TASK.md and stack.json still written (and TASK.md = the task prompt,
        # not anything the support repo might have had)
        assert (env_dir / "TASK.md").read_text() == task.prompt
        assert (env_dir / "stack.json").exists()

        # A new git repo was initialized
        assert (env_dir / ".git").exists()

        runner.teardown(env_id)

    def test_provision_no_support_unchanged(self, tmp_path):
        """Tasks without support_dir behave exactly as before."""
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(work_dir=tmp_path)
        stack = StackConfig(language="go", agent="claude-code", framework="stdlib")
        task = TaskSpec(name="plain", description="d", prompt="hi")
        env_id = runner.provision(stack, task)
        env_dir = tmp_path / env_id

        assert (env_dir / "TASK.md").exists()
        assert (env_dir / "stack.json").exists()
        # Only the files we wrote + .git from init
        names = {p.name for p in env_dir.iterdir()}
        assert names == {"TASK.md", "stack.json", ".git"}

        runner.teardown(env_id)
