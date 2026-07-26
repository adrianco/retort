"""Judge harness adapters for Retort evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from retort.config.schema import EvaluationConfig, LocalAgentConfig
from retort.playpen.local_runner import _model_cli_args


class JudgeConfigurationError(ValueError):
    """The requested judge cannot be resolved from workspace configuration."""


@dataclass(frozen=True)
class JudgeSpec:
    harness: str
    model: str
    timeout_seconds: int = 600


class JudgeRunner(Protocol):
    def build_command(self, judge: JudgeSpec, run_dir: Path, prompt: str) -> list[str]: ...


class ClaudeJudgeRunner:
    def build_command(self, judge: JudgeSpec, run_dir: Path, prompt: str) -> list[str]:
        return [
            "claude", "-p", prompt, *_model_cli_args(judge.model),
            "--output-format", "text", "--dangerously-skip-permissions",
        ]


class CodexJudgeRunner:
    def build_command(self, judge: JudgeSpec, run_dir: Path, prompt: str) -> list[str]:
        cmd = [
            "codex", "exec", "--json", "--ephemeral", "--sandbox",
            "workspace-write", "--cd", str(run_dir), "--skip-git-repo-check",
        ]
        if judge.model:
            cmd.extend(["--model", judge.model])
        cmd.append(prompt)
        return cmd


BUILTIN_JUDGES: dict[str, JudgeRunner] = {
    "claude-code": ClaudeJudgeRunner(),
    "codex": CodexJudgeRunner(),
}


def available_judges() -> dict[str, JudgeRunner]:
    """Built-in judges plus adapters registered by Retort plugins."""
    from retort.plugins import discover_judges

    return {**BUILTIN_JUDGES, **discover_judges()}


def resolve_judge(
    evaluation: EvaluationConfig, profiles: dict[str, LocalAgentConfig]
) -> JudgeSpec:
    """Resolve the legacy Claude config or an inline/profile judge selector."""
    if evaluation.judge is None:
        return JudgeSpec(harness="claude-code", model=evaluation.model)

    config = evaluation.judge
    if config.profile:
        profile = profiles.get(config.profile)
        if profile is None:
            raise JudgeConfigurationError(
                f"judge profile {config.profile!r} is not in playpen.local_agents"
            )
        harness = profile.harness
        model = config.model or profile.model
    else:
        harness = config.harness or ""
        model = config.model
    if not model:
        raise JudgeConfigurationError(
            f"judge {harness!r} needs a model in evaluation.judge or its profile"
        )
    if harness not in available_judges():
        raise JudgeConfigurationError(f"unknown judge harness {harness!r}")
    return JudgeSpec(
        harness=harness,
        model=model,
        timeout_seconds=config.timeout_minutes * 60,
    )


def judge_runner(judge: JudgeSpec) -> JudgeRunner:
    try:
        return available_judges()[judge.harness]
    except KeyError as exc:
        raise JudgeConfigurationError(f"unknown judge harness {judge.harness!r}") from exc
