"""Tests for playpen runner types and DockerRunner."""

from __future__ import annotations

import json
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


class TestLocalRunnerModelVersioning:
    """Versioned model IDs pass through to the --model flag unchanged."""

    def _cmd(self, model: str) -> list[str]:
        from retort.playpen.local_runner import LocalRunner
        runner = LocalRunner()
        stack = StackConfig(
            language="python",
            agent="claude-code",
            framework="fastapi",
            extra={"model": model},
        )
        task = TaskSpec(name="t", description="d", prompt="p")
        return runner._build_agent_command(stack, task)

    def test_alias_opus_resolves_to_versioned_id(self):
        from retort.playpen.local_runner import MODEL_ALIASES
        cmd = self._cmd("opus")
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == MODEL_ALIASES["opus"]

    def test_alias_sonnet_resolves_to_versioned_id(self):
        from retort.playpen.local_runner import MODEL_ALIASES
        cmd = self._cmd("sonnet")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == MODEL_ALIASES["sonnet"]

    def test_versioned_opus_46_passes_through(self):
        cmd = self._cmd("claude-opus-4-6")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-6"

    def test_versioned_opus_47_passes_through(self):
        cmd = self._cmd("claude-opus-4-7")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-7"

    def test_versioned_opus_48_passes_through(self):
        cmd = self._cmd("claude-opus-4-8")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-8"
        assert "--settings" not in cmd  # non-fast: no fastMode setting

    def test_fast_model_strips_suffix_and_enables_fast_mode(self):
        cmd = self._cmd("claude-opus-4-8-fast")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-8"  # suffix stripped to base model
        assert "--settings" in cmd
        assert cmd[cmd.index("--settings") + 1] == '{"fastMode": true}'

    def test_fast_alias_resolves_and_enables_fast_mode(self):
        cmd = self._cmd("opus-4.8-fast")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-8"
        assert '{"fastMode": true}' in cmd

    def test_no_model_flag_when_absent(self):
        from retort.playpen.local_runner import LocalRunner
        runner = LocalRunner()
        stack = StackConfig(language="python", agent="claude-code", framework="fastapi")
        task = TaskSpec(name="t", description="d", prompt="p")
        cmd = runner._build_agent_command(stack, task)
        assert "--model" not in cmd

    def test_stack_json_includes_extra_factors(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner
        runner = LocalRunner(work_dir=tmp_path)
        stack = StackConfig(
            language="python",
            agent="claude-code",
            framework="fastapi",
            extra={"model": "claude-opus-4-7", "tooling": "none"},
        )
        task = TaskSpec(name="t", description="d", prompt="hi")
        env_id = runner.provision(stack, task)
        env_dir = tmp_path / env_id
        data = json.loads((env_dir / "stack.json").read_text())
        assert data["language"] == "python"
        assert data["model"] == "claude-opus-4-7"
        assert data["tooling"] == "none"
        runner.teardown(env_id)

    def test_eval_model_triggers_post_run_evaluate(self, tmp_path):
        """When eval_model is set, _post_run_evaluate is called on success."""
        from unittest.mock import patch, MagicMock
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(work_dir=tmp_path, eval_model="haiku")
        with patch.object(runner, "_post_run_evaluate") as mock_eval:
            stack = StackConfig(language="python", agent="claude-code", framework="fastapi")
            task = TaskSpec(name="t", description="d", prompt="hi")
            env_id = runner.provision(stack, task)
            # Simulate a successful agent run via patched subprocess
            fake_result = MagicMock()
            fake_result.returncode = 0
            fake_result.stdout = ""
            fake_result.stderr = ""
            with patch("retort.playpen.local_runner.subprocess.run", return_value=fake_result):
                runner.execute(env_id, stack, task)
            mock_eval.assert_called_once()

    def test_find_skill_path_locates_skill(self, tmp_path):
        from retort.playpen.local_runner import _find_skill_path
        skills_dir = tmp_path / "skills" / "evaluate-run"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / "SKILL.md"
        skill_file.write_text("# skill")
        run_dir = tmp_path / "experiment" / "runs" / "rep1"
        run_dir.mkdir(parents=True)
        assert _find_skill_path("evaluate-run", start=run_dir) == skill_file

    def test_find_skill_path_returns_none_when_missing(self, tmp_path):
        from retort.playpen.local_runner import _find_skill_path
        assert _find_skill_path("evaluate-run", start=tmp_path) is None

    def test_versioned_alias_opus_46_resolves(self):
        cmd = self._cmd("opus-4.6")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-6"

    def test_versioned_alias_opus_47_resolves(self):
        cmd = self._cmd("opus-4.7")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-7"

    def test_versioned_alias_sonnet_45_resolves(self):
        cmd = self._cmd("sonnet-4.5")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-sonnet-4-5"

    def test_versioned_alias_sonnet_46_resolves(self):
        cmd = self._cmd("sonnet-4.6")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-sonnet-4-6"

    def test_versioned_alias_haiku_45_resolves(self):
        cmd = self._cmd("haiku-4.5")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-haiku-4-5"

    def test_unknown_string_passes_through(self):
        cmd = self._cmd("my-custom-model")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "my-custom-model"

    def test_short_alias_opus_still_resolves(self):
        from retort.playpen.local_runner import MODEL_ALIASES
        cmd = self._cmd("opus")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == MODEL_ALIASES["opus"]

    def test_short_alias_haiku_still_resolves(self):
        from retort.playpen.local_runner import MODEL_ALIASES
        cmd = self._cmd("haiku")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == MODEL_ALIASES["haiku"]


class TestLocalInferenceCost:
    """Tests for LocalInferenceCost cost model and LocalRunner integration."""

    def _make_cost(self, **kwargs):
        from retort.config.schema import LocalInferenceCost
        defaults = dict(
            cost_per_kwh=0.20,
            power_watts=210.0,
            hardware_cost_usd=550.0,
            amortization_months=36,
            utilization_fraction=0.25,
        )
        defaults.update(kwargs)
        return LocalInferenceCost(**defaults)

    def test_effective_cost_per_second_positive(self):
        cost = self._make_cost()
        assert cost.effective_cost_per_second() > 0

    def test_effective_cost_per_second_components(self):
        cost = self._make_cost(
            cost_per_kwh=0.20,
            power_watts=210.0,
            hardware_cost_usd=0.0,  # no hardware → only electricity
            amortization_months=36,
            utilization_fraction=0.25,
        )
        expected = (210.0 / 1000.0) * 0.20 / 3600.0
        assert abs(cost.effective_cost_per_second() - expected) < 1e-12

    def test_cost_for_run_scales_with_duration(self):
        cost = self._make_cost()
        cost_60s = cost.cost_for_run(60.0)
        cost_120s = cost.cost_for_run(120.0)
        assert abs(cost_120s - 2 * cost_60s) < 1e-12

    def test_effective_cost_per_token_zero_tokens(self):
        cost = self._make_cost()
        assert cost.effective_cost_per_token(0, 60.0) == 0.0

    def test_effective_cost_per_token_formula(self):
        cost = self._make_cost()
        duration, tokens = 120.0, 50000
        expected = cost.cost_for_run(duration) / tokens
        assert abs(cost.effective_cost_per_token(tokens, duration) - expected) < 1e-15

    def test_local_runner_computes_cost_when_no_api_cost(self, tmp_path):
        """LocalRunner with local_inference_cost fills metadata when agent reports no cost."""
        from unittest.mock import patch, MagicMock
        from retort.playpen.local_runner import LocalRunner

        lc = self._make_cost()
        runner = LocalRunner(work_dir=tmp_path, local_inference_cost=lc)

        stack = StackConfig(language="python", agent="claude-code", framework="fastapi")
        task = TaskSpec(name="t", description="d", prompt="hi")
        env_id = runner.provision(stack, task)

        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = "{}"   # agent reports no cost
        fake_result.stderr = ""

        with patch("retort.playpen.local_runner.subprocess.run", return_value=fake_result):
            with patch("retort.playpen.local_runner.time.monotonic", side_effect=[0.0, 60.0]):
                artifacts = runner.execute(env_id, stack, task)

        assert "total_cost_usd" in artifacts.metadata
        assert float(artifacts.metadata["total_cost_usd"]) > 0
        expected = lc.cost_for_run(60.0)
        assert abs(float(artifacts.metadata["total_cost_usd"]) - expected) < 1e-10

    def test_local_runner_does_not_override_api_cost(self, tmp_path):
        """When agent reports a non-zero cost, local_inference_cost is not applied."""
        from unittest.mock import patch, MagicMock
        import json as _json
        from retort.playpen.local_runner import LocalRunner

        lc = self._make_cost()
        runner = LocalRunner(work_dir=tmp_path, local_inference_cost=lc)

        stack = StackConfig(language="python", agent="claude-code", framework="fastapi")
        task = TaskSpec(name="t", description="d", prompt="hi")
        env_id = runner.provision(stack, task)

        agent_payload = _json.dumps({"total_cost_usd": 0.042, "usage": {}})
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = agent_payload
        fake_result.stderr = ""

        with patch("retort.playpen.local_runner.subprocess.run", return_value=fake_result):
            artifacts = runner.execute(env_id, stack, task)

        assert abs(float(artifacts.metadata["total_cost_usd"]) - 0.042) < 1e-10

    def test_local_runner_stores_effective_cost_per_token(self, tmp_path):
        """When tokens are reported and local cost computed, effective_cost_per_token is stored."""
        from unittest.mock import patch, MagicMock
        import json as _json
        from retort.playpen.local_runner import LocalRunner

        lc = self._make_cost()
        runner = LocalRunner(work_dir=tmp_path, local_inference_cost=lc)

        stack = StackConfig(language="python", agent="claude-code", framework="fastapi")
        task = TaskSpec(name="t", description="d", prompt="hi")
        env_id = runner.provision(stack, task)

        # Agent reports token counts but no API cost (local model)
        agent_payload = _json.dumps({"usage": {"output_tokens": 1000}})
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = agent_payload
        fake_result.stderr = ""

        with patch("retort.playpen.local_runner.subprocess.run", return_value=fake_result):
            with patch("retort.playpen.local_runner.time.monotonic", side_effect=[0.0, 60.0]):
                artifacts = runner.execute(env_id, stack, task)

        assert "effective_cost_per_token" in artifacts.metadata
        ept = float(artifacts.metadata["effective_cost_per_token"])
        assert ept > 0
        expected = lc.effective_cost_per_token(1000, 60.0)
        assert abs(ept - expected) < 1e-15
