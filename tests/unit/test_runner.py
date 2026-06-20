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


class TestLocalRunnerOmpHarness:
    def _profile(self, **kwargs):
        from retort.config.schema import LocalAgentConfig

        return LocalAgentConfig(harness="omp", **kwargs)

    def test_builds_omp_command_with_model_factor(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"qwen-local": self._profile()},
        )
        stack = StackConfig(
            language="python",
            agent="qwen-local",
            framework="stdlib",
            extra={"model": "moe"},
        )
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert cmd[:5] == ["omp", "-p", "--no-session", "--mode", "json"]
        assert "--model" in cmd
        assert cmd[cmd.index("--model") + 1] == "moe"
        assert "You are working in python." in cmd[-1]
        assert "Read TASK.md" in cmd[-1]

    def test_builds_arbitrary_agent_name_with_omp_harness(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"pi-dense": self._profile(model="dense")},
        )
        stack = StackConfig(language="go", agent="pi-dense", framework="stdlib")
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert cmd[0] == "omp"
        assert cmd[cmd.index("--model") + 1] == "dense"
        assert "You are working in go." in cmd[-1]

    def test_design_model_overrides_profile_and_default_model(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            default_model="global",
            local_agents={"qwen-local": self._profile(model="dense")},
        )
        stack = StackConfig(
            language="python",
            agent="qwen-local",
            framework="stdlib",
            extra={"model": "moe"},
        )
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert "--model" in cmd
        assert cmd[cmd.index("--model") + 1] == "moe"
        assert "dense" not in cmd
        assert "global" not in cmd

    def test_builds_omp_command_with_profile_thinking(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"qwen-local": self._profile(thinking="minimal")},
        )
        stack = StackConfig(language="python", agent="qwen-local", framework="stdlib")
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert "--thinking" in cmd
        assert cmd[cmd.index("--thinking") + 1] == "minimal"


class TestLocalRunnerGeminiHarness:
    def _profile(self, **kwargs):
        from retort.config.schema import LocalAgentConfig

        return LocalAgentConfig(harness="gemini", **kwargs)

    def test_builds_gemini_command_with_model_factor(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"gemini": self._profile()},
        )
        stack = StackConfig(
            language="go",
            agent="gemini",
            framework="stdlib",
            extra={"model": "gemini-2.5-pro"},
        )
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert cmd[:5] == ["gemini", "--yolo", "--skip-trust", "--output-format", "json"]
        assert cmd[cmd.index("--model") + 1] == "gemini-2.5-pro"
        # The prompt is the value after --prompt, and carries the language steer.
        assert "You are working in go." in cmd[cmd.index("--prompt") + 1]
        assert "Read TASK.md" in cmd[cmd.index("--prompt") + 1]

    def test_gemini_profile_model_default_applies(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"gemini": self._profile(model="gemini-2.5-flash")},
        )
        stack = StackConfig(language="rust", agent="gemini", framework="stdlib")
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert cmd[cmd.index("--model") + 1] == "gemini-2.5-flash"

    def test_parse_gemini_usage_real_cli_shape(self):
        # The ACTUAL `gemini --output-format json` output (CLI 0.46, captured
        # from a live run): one {response, stats} object where stats.models is
        # keyed BY model name and token fields are the CLI's own names
        # (input/candidates/cached/total/thoughts) — NOT the API *TokenCount
        # names. `thoughts` (thinking tokens) bill as output.
        import json

        from retort.playpen.local_runner import (
            GEMINI_PRICING, _parse_agent_usage, _parse_gemini_usage,
        )

        out = json.dumps({
            "session_id": "abc",
            "response": "ok",
            "stats": {"models": {"gemini-2.5-flash": {
                "api": {"totalRequests": 2, "totalLatencyMs": 14038},
                "tokens": {"input": 7798, "prompt": 7798, "candidates": 1,
                           "total": 7839, "cached": 0, "thoughts": 40, "tool": 0},
            }}},
        })
        tokens, meta = _parse_gemini_usage(out)
        assert tokens == 7839                       # reported total
        assert meta["input_tokens"] == "7798"
        assert meta["output_tokens"] == "41"        # candidates(1) + thoughts(40)
        assert meta["thoughts_tokens"] == "40"
        assert meta["model"] == "gemini-2.5-flash"  # from the stats.models key
        in_rate, out_rate = GEMINI_PRICING["gemini-2.5-flash"]
        expected = (7798 * in_rate + 41 * out_rate) / 1_000_000
        assert abs(float(meta["total_cost_usd"]) - expected) < 1e-9
        assert _parse_agent_usage("gemini", out) == (tokens, meta)  # dispatch routes here

    def test_parse_gemini_usage_unknown_model_zero_cost(self):
        import json

        from retort.playpen.local_runner import _parse_gemini_usage

        out = json.dumps({"stats": {"models": {"gemini-9-ultra": {"tokens": {
            "input": 100, "candidates": 50, "total": 150,
        }}}}})
        tokens, meta = _parse_gemini_usage(out)
        assert tokens == 150
        assert meta["total_cost_usd"] == "0.0"  # unknown model -> no derived cost

    def test_parse_gemini_usage_api_name_fallback(self):
        # Robustness: if a future schema drops the stats.models nesting and uses
        # API field names, the recursive fallback still extracts tokens.
        import json

        from retort.playpen.local_runner import _parse_gemini_usage

        out = json.dumps({"usage": {
            "promptTokenCount": 1000, "candidatesTokenCount": 200, "totalTokenCount": 1200,
        }})
        tokens, meta = _parse_gemini_usage(out)
        assert tokens == 1200
        assert meta["input_tokens"] == "1000"
        assert meta["output_tokens"] == "200"

    def test_parse_gemini_usage_bad_json_safe(self):
        from retort.playpen.local_runner import _parse_gemini_usage

        assert _parse_gemini_usage("not json") == (0, {})

    def test_design_thinking_off_omits_omp_flag(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"qwen-local": self._profile(thinking="minimal")},
        )
        stack = StackConfig(
            language="python",
            agent="qwen-local",
            framework="stdlib",
            extra={"thinking": "off"},
        )
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert "--thinking" not in cmd

    def test_parse_omp_usage_from_json_events(self):
        from retort.playpen.local_runner import _parse_agent_usage

        stdout = (
            '{"type":"session","id":"s1"}\n'
            '{"type":"message_end","message":{"provider":"llama.cpp",'
            '"model":"gemma.gguf","usage":{"input":20,"output":5,'
            '"cacheRead":3,"cacheWrite":2,"totalTokens":30,'
            '"cost":{"total":0.0123}},"stopReason":"stop"}}\n'
        )

        token_count, metadata = _parse_agent_usage("omp", stdout)

        assert token_count == 30
        assert metadata["input_tokens"] == "20"
        assert metadata["output_tokens"] == "5"
        assert metadata["cache_read_input_tokens"] == "3"
        assert metadata["cache_creation_input_tokens"] == "2"
        assert metadata["total_cost_usd"] == "0.0123"
        assert metadata["provider"] == "llama.cpp"
        assert metadata["model"] == "gemma.gguf"
        assert metadata["stop_reason"] == "stop"

    def test_execute_omp_plain_output_succeeds_without_usage(self, tmp_path):
        from unittest.mock import MagicMock, patch

        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"qwen-local": self._profile()},
        )
        stack = StackConfig(language="python", agent="qwen-local", framework="stdlib")
        task = TaskSpec(name="plain", description="d", prompt="hi")
        env_id = runner.provision(stack, task)

        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = "completed\n"
        fake_result.stderr = ""
        with patch("retort.playpen.local_runner.subprocess.run", return_value=fake_result):
            artifacts = runner.execute(env_id, stack, task)

        assert artifacts.succeeded is True
        assert artifacts.stdout == "completed\n"
        assert artifacts.token_count == 0

    def test_unknown_agent_still_captures_claude_cost(self, tmp_path):
        """Regression for the PR#6 (OMP harness) cost-drop bug.

        A design that leaves the agent factor unset records agent="unknown".
        The command builder runs it as claude-code, so claude emits a cost JSON
        — but before the fix the usage parser was handed the raw "unknown"
        harness name and silently returned empty metadata, so _cost_usd/_tokens
        were dropped (only runner-measured _duration_seconds survived). This is
        exactly what wiped cost from experiments 7 and 8.
        """
        from unittest.mock import MagicMock, patch

        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(work_dir=tmp_path)
        stack = StackConfig(language="erlang", agent="unknown", framework="unknown")
        task = TaskSpec(name="plain", description="d", prompt="hi")
        env_id = runner.provision(stack, task)

        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = (
            '{"total_cost_usd": 0.42, "num_turns": 7, '
            '"usage": {"input_tokens": 100, "output_tokens": 50}}'
        )
        fake_result.stderr = ""
        with patch("retort.playpen.local_runner.subprocess.run", return_value=fake_result):
            artifacts = runner.execute(env_id, stack, task)

        assert artifacts.succeeded is True
        assert artifacts.metadata.get("total_cost_usd") == "0.42"
        assert artifacts.metadata.get("num_turns") == "7"
        assert artifacts.token_count == 150

    def test_fast_mode_doubles_reported_cost(self, tmp_path):
        """Fast mode bills at 2× but the CLI reports the standard-rate cost.

        Verified by probe: a fastMode call returns the standard-priced
        total_cost_usd, not 2×. The runner scales fast-mode runs up so the
        recorded cost matches what's actually charged (Opus-4.8 fast = $10/$50
        per Mtok vs $5/$25 standard).
        """
        from unittest.mock import MagicMock, patch

        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(work_dir=tmp_path)
        stack = StackConfig(language="go", agent="unknown", framework="unknown",
                            extra={"model": "claude-opus-4-8-fast"})
        task = TaskSpec(name="plain", description="d", prompt="hi")
        env_id = runner.provision(stack, task)

        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = '{"total_cost_usd": 0.50, "usage": {"output_tokens": 10}}'
        fake_result.stderr = ""
        with patch("retort.playpen.local_runner.subprocess.run", return_value=fake_result):
            artifacts = runner.execute(env_id, stack, task)

        # 0.50 standard-rate -> 1.00 at the 2× fast premium.
        assert artifacts.metadata.get("total_cost_usd") == "1.0"
        assert artifacts.metadata.get("fast_mode_cost_multiplier") == "2.0"

    def test_non_fast_model_cost_unchanged(self, tmp_path):
        from unittest.mock import MagicMock, patch

        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(work_dir=tmp_path)
        stack = StackConfig(language="go", agent="unknown", framework="unknown",
                            extra={"model": "claude-opus-4-8"})
        task = TaskSpec(name="plain", description="d", prompt="hi")
        env_id = runner.provision(stack, task)

        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = '{"total_cost_usd": 0.50, "usage": {"output_tokens": 10}}'
        fake_result.stderr = ""
        with patch("retort.playpen.local_runner.subprocess.run", return_value=fake_result):
            artifacts = runner.execute(env_id, stack, task)

        assert artifacts.metadata.get("total_cost_usd") == "0.5"
        assert "fast_mode_cost_multiplier" not in artifacts.metadata

    def test_omp_prompt_factor_injected(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "verbose.md").write_text("Be very explicit in your comments.")

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"qwen-local": self._profile()},
            prompts_dir=prompts_dir,
        )
        stack = StackConfig(
            language="python",
            agent="qwen-local",
            framework="stdlib",
            extra={"prompt": "verbose"},
        )
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert "Be very explicit in your comments." in cmd[-1]

    def test_omp_prompt_none_not_injected(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"qwen-local": self._profile()},
        )
        stack = StackConfig(
            language="python",
            agent="qwen-local",
            framework="stdlib",
            extra={"prompt": "none"},
        )
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        # Prompt text is the last arg; it should contain no injected content
        assert "none" not in cmd[-1]

    def test_parse_omp_usage_last_message_end_wins(self):
        from retort.playpen.local_runner import _parse_agent_usage

        # Two message_end events — the second (final) one should win.
        stdout = (
            '{"type":"message_end","message":{"provider":"llama.cpp",'
            '"model":"first.gguf","usage":{"input":10,"output":2,'
            '"totalTokens":12,"cost":{"total":0.001}},"stopReason":"stop"}}\n'
            '{"type":"message_end","message":{"provider":"mlx",'
            '"model":"final.gguf","usage":{"input":20,"output":5,'
            '"totalTokens":30,"cost":{"total":0.0123}},"stopReason":"end_turn"}}\n'
        )

        token_count, metadata = _parse_agent_usage("omp", stdout)

        assert token_count == 30
        assert metadata["provider"] == "mlx"
        assert metadata["model"] == "final.gguf"
        assert metadata["total_cost_usd"] == "0.0123"
        assert metadata["stop_reason"] == "end_turn"

    def test_parse_omp_usage_malformed_lines_skipped(self):
        from retort.playpen.local_runner import _parse_agent_usage

        stdout = (
            "not json at all\n"
            "{bad json}\n"
            '{"type":"message_end","message":{"provider":"p","model":"m",'
            '"usage":{"input":5,"output":5,"totalTokens":10,'
            '"cost":{"total":0.005}},"stopReason":"stop"}}\n'
        )

        token_count, metadata = _parse_agent_usage("omp", stdout)

        assert token_count == 10
        assert metadata["provider"] == "p"


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


class TestHarnessFollowsModel:
    """The agent is the same variable as the model: a single `model` factor
    (no separate `agent` factor) routes to the right harness."""

    def test_harness_for_model_inference(self):
        from retort.playpen.local_runner import _harness_for_model

        assert _harness_for_model("gemini-2.5-pro") == "gemini"
        assert _harness_for_model("gemini-2.5-flash") == "gemini"
        assert _harness_for_model("claude-opus-4-8") == "claude-code"
        assert _harness_for_model("claude-fable-5") == "claude-code"
        assert _harness_for_model("opus") == "claude-code"   # short alias
        assert _harness_for_model("") == "claude-code"

    def test_gemini_model_routes_to_gemini_without_agent_factor(self, tmp_path):
        # No agent factor, no local_agents profile — just model=gemini-2.5-pro.
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(work_dir=tmp_path)
        stack = StackConfig(
            language="go", agent="unknown", framework="stdlib",
            extra={"model": "gemini-2.5-pro"},
        )
        task = TaskSpec(name="t", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert cmd[:2] == ["gemini", "--yolo"]
        assert cmd[cmd.index("--model") + 1] == "gemini-2.5-pro"
        assert runner._resolve_harness(stack) == "gemini"

    def test_claude_model_routes_to_claude_code_without_agent_factor(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(work_dir=tmp_path)
        stack = StackConfig(
            language="rust", agent="unknown", framework="stdlib",
            extra={"model": "claude-opus-4-8"},
        )
        task = TaskSpec(name="t", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        assert cmd[0] == "claude"
        assert cmd[cmd.index("--model") + 1] == "claude-opus-4-8"
        assert runner._resolve_harness(stack) == "claude-code"

    def test_local_agent_profile_overrides_model_inference(self, tmp_path):
        # An explicit omp profile still wins even though the model name would
        # otherwise be claude-routed — local/custom models need the override.
        from retort.config.schema import LocalAgentConfig
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"qwen-local": LocalAgentConfig(harness="omp")},
        )
        stack = StackConfig(
            language="go", agent="qwen-local", framework="stdlib",
            extra={"model": "moe"},
        )
        assert runner._resolve_harness(stack) == "omp"


def test_model_cli_args_fast_mode_strips_suffix_and_sets_setting():
    """A '-fast' model level → base model id + fastMode setting (not a model id)."""
    from retort.playpen.local_runner import _model_cli_args
    args = _model_cli_args("opus-4.8-fast")
    assert "--model" in args
    assert args[args.index("--model") + 1] == "claude-opus-4-8"  # suffix stripped
    assert "claude-opus-4-8-fast" not in args
    assert "--settings" in args
    assert '{"fastMode": true}' in args


def test_model_cli_args_non_fast_has_no_settings():
    from retort.playpen.local_runner import _model_cli_args
    assert _model_cli_args("claude-opus-4-6") == ["--model", "claude-opus-4-6"]
    assert _model_cli_args("") == []


def test_usage_limit_detection_and_artifact_flag():
    """Usage/rate-limit signatures are recognised; ordinary failures are not."""
    from retort.playpen.local_runner import _USAGE_LIMIT_RE
    from retort.playpen.runner import RunArtifacts
    for hit in ["Claude usage limit reached", "429 Too Many Requests",
                "rate_limit_error", "your limit will reset at 3pm"]:
        assert _USAGE_LIMIT_RE.search(hit), hit
    for miss in ["compilation failed", "AssertionError: expected 3", "panic: nil"]:
        assert not _USAGE_LIMIT_RE.search(miss), miss
    assert RunArtifacts(metadata={"usage_limited": "true"}).usage_limited
    assert not RunArtifacts(metadata={}).usage_limited


class TestLocalRunnerOpencodeHarness:
    def _profile(self, **kwargs):
        from retort.config.schema import LocalAgentConfig

        return LocalAgentConfig(harness="opencode", **kwargs)

    def test_builds_opencode_command_with_model_factor(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"oc": self._profile()},
        )
        stack = StackConfig(
            language="python",
            agent="oc",
            framework="stdlib",
            extra={"model": "openrouter/z-ai/glm-5.2"},
        )
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task)

        # `--pure` is load-bearing (without it opencode hangs headless).
        assert cmd[:5] == ["opencode", "run", "--pure", "--format", "json"]
        assert cmd[cmd.index("--model") + 1] == "openrouter/z-ai/glm-5.2"
        assert "You are working in python." in cmd[-1]

    def test_builds_opencode_command_passes_workspace_dir(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"oc": self._profile(model="openrouter/z-ai/glm-5.2")},
        )
        stack = StackConfig(language="go", agent="oc", framework="stdlib")
        task = TaskSpec(name="plain", description="d", prompt="hi")

        cmd = runner._build_agent_command(stack, task, tmp_path)

        # opencode resolves its workspace from --dir, not the subprocess cwd.
        assert "--dir" in cmd
        assert cmd[cmd.index("--dir") + 1] == str(tmp_path)

    def test_opencode_profile_resolves_harness(self, tmp_path):
        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"oc": self._profile()},
        )
        stack = StackConfig(
            language="python", agent="oc", framework="stdlib",
            extra={"model": "openrouter/z-ai/glm-5.2"},
        )
        assert runner._resolve_harness(stack) == "opencode"

    def test_writes_per_workspace_opencode_config(self, tmp_path):
        import json

        from retort.playpen.local_runner import LocalRunner

        runner = LocalRunner(
            work_dir=tmp_path,
            local_agents={"oc": self._profile()},
        )
        stack = StackConfig(
            language="python", agent="oc", framework="stdlib",
            extra={"model": "openrouter/z-ai/glm-5.2"},
        )
        ws = tmp_path / "ws"
        ws.mkdir()
        runner._write_opencode_config(ws, stack)

        cfg = json.loads((ws / "opencode.json").read_text())
        # model registered under the openrouter provider, prefix stripped.
        assert "z-ai/glm-5.2" in cfg["provider"]["openrouter"]["models"]

    def test_parse_opencode_usage_sums_across_steps(self):
        from retort.playpen.local_runner import _parse_agent_usage

        # opencode emits one step_finish per assistant step carrying THAT step's
        # cost + tokens; per-run usage is the sum across steps.
        stdout = (
            '{"type":"step_start"}\n'
            '{"type":"text","part":{"text":"working"}}\n'
            '{"type":"step_finish","part":{"cost":0.001,"tokens":'
            '{"total":100,"input":80,"output":20,"reasoning":0,'
            '"cache":{"read":10,"write":5}}}}\n'
            '{"type":"step_finish","part":{"cost":0.002,"tokens":'
            '{"total":200,"input":150,"output":50,"reasoning":0,'
            '"cache":{"read":30,"write":0}}}}\n'
        )

        token_count, metadata = _parse_agent_usage("opencode", stdout)

        assert token_count == 300                                       # 100 + 200
        assert abs(float(metadata["total_cost_usd"]) - 0.003) < 1e-9    # 0.001 + 0.002
        assert metadata["input_tokens"] == "230"                        # 80 + 150
        assert metadata["output_tokens"] == "70"                        # 20 + 50
        assert metadata["cache_read_input_tokens"] == "40"              # 10 + 30
        assert metadata["cache_creation_input_tokens"] == "5"           # 5 + 0

    def test_parse_opencode_usage_malformed_lines_skipped(self):
        from retort.playpen.local_runner import _parse_agent_usage

        stdout = (
            "not json at all\n"
            "{bad json}\n"
            '{"type":"step_finish","part":{"cost":0.005,"tokens":'
            '{"total":10,"input":5,"output":5,"cache":{"read":0,"write":0}}}}\n'
        )

        token_count, metadata = _parse_agent_usage("opencode", stdout)

        assert token_count == 10
        assert metadata["total_cost_usd"] == "0.005"

    def test_parse_opencode_usage_no_steps_returns_zero(self):
        from retort.playpen.local_runner import _parse_opencode_usage

        assert _parse_opencode_usage('{"type":"step_start"}\n') == (0, {})
        assert _parse_opencode_usage("not json") == (0, {})
