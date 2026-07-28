"""Tests for evaluation judge selection and built-in harness adapters."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from retort.config.schema import EvaluationConfig, JudgeConfig, LocalAgentConfig


def test_legacy_evaluation_config_resolves_to_claude_judge():
    from retort.evaluation.judges import resolve_judge

    judge = resolve_judge(EvaluationConfig(model="haiku"), {})

    assert judge.harness == "claude-code"
    assert judge.model == "haiku"


def test_profile_judge_resolves_harness_and_model():
    from retort.evaluation.judges import resolve_judge

    config = EvaluationConfig(judge=JudgeConfig(profile="codex-judge"))
    profiles = {
        "codex-judge": LocalAgentConfig(
            harness="codex", model="gpt-5.6-terra"
        )
    }

    judge = resolve_judge(config, profiles)

    assert judge.harness == "codex"
    assert judge.model == "gpt-5.6-terra"


def test_profile_judge_can_override_its_model():
    from retort.evaluation.judges import resolve_judge

    config = EvaluationConfig(
        judge=JudgeConfig(profile="codex-judge", model="gpt-5.6-sol")
    )
    profiles = {
        "codex-judge": LocalAgentConfig(
            harness="codex", model="gpt-5.6-terra"
        )
    }

    assert resolve_judge(config, profiles).model == "gpt-5.6-sol"


def test_unknown_judge_profile_is_rejected():
    from retort.evaluation.judges import JudgeConfigurationError, resolve_judge

    config = EvaluationConfig(judge=JudgeConfig(profile="missing"))

    with pytest.raises(JudgeConfigurationError, match="missing"):
        resolve_judge(config, {})


def test_codex_judge_builds_isolated_write_command(tmp_path: Path):
    from retort.evaluation.judges import CodexJudgeRunner, JudgeSpec

    cmd = CodexJudgeRunner().build_command(
        JudgeSpec(harness="codex", model="gpt-5.6-terra"),
        tmp_path,
        "Write assessment.json.",
    )

    assert cmd[:6] == [
        "codex", "exec", "--json", "--ephemeral", "--sandbox", "workspace-write"
    ]
    assert cmd[cmd.index("--cd") + 1] == str(tmp_path)
    assert cmd[cmd.index("--model") + 1] == "gpt-5.6-terra"
    assert "--skip-git-repo-check" in cmd


def test_claude_judge_preserves_existing_skill_invocation(tmp_path: Path):
    from retort.evaluation.judges import ClaudeJudgeRunner, JudgeSpec

    cmd = ClaudeJudgeRunner().build_command(
        JudgeSpec(harness="claude-code", model="haiku"),
        tmp_path,
        "Write assessment.json.",
    )

    assert cmd[0:2] == ["claude", "-p"]
    assert cmd[cmd.index("--model") + 1] == "claude-haiku-4-5"
    assert "--dangerously-skip-permissions" in cmd


def test_judge_invocation_persists_each_attempt(tmp_path: Path):
    from retort.cli import _invoke_judge_prompt
    from retort.evaluation.judges import JudgeSpec

    judge = JudgeSpec(harness="codex", model="gpt-5.6-terra")
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="judge output", stderr="judge diagnostics"
    )

    with patch("retort.cli.subprocess.run", return_value=completed):
        assert _invoke_judge_prompt(judge, tmp_path, "Write assessment.json.") == (
            0,
            "judge outputjudge diagnostics",
        )
        assert _invoke_judge_prompt(judge, tmp_path, "Second opinion.")[0] == 0

    logs = tmp_path / "_judge"
    assert (logs / "attempt-001.stdout.log").read_text() == "judge output"
    assert (logs / "attempt-001.stderr.log").read_text() == "judge diagnostics"
    metadata = json.loads((logs / "attempt-002.json").read_text())
    assert metadata["harness"] == "codex"
    assert metadata["model"] == "gpt-5.6-terra"
    assert metadata["exit_code"] == 0
    assert metadata["duration_seconds"] >= 0
