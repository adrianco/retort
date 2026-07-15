"""Abstract playpen runner protocol and shared data types.

A PlaypenRunner provisions an isolated environment, executes an agent task,
and tears it down. Concrete implementations include DockerRunner (default)
and CloudRunner (optional).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class StackConfig:
    """Describes the technology stack for a single experiment run.

    Each field maps to a factor level from the design matrix.
    """

    language: str
    agent: str
    framework: str
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_run_config(cls, config: dict[str, str]) -> StackConfig:
        """Build from a design matrix row dict."""
        return cls(
            language=config.get("language", "unknown"),
            agent=config.get("agent", "unknown"),
            framework=config.get("framework", "unknown"),
            extra={k: v for k, v in config.items()
                   if k not in ("language", "agent", "framework")},
        )


def stack_metadata(stack: StackConfig, model: str | None = None) -> dict[str, str]:
    """Canonical ``stack.json`` payload — always records ``model``.

    Cloud runs carry the model as a ``model=`` design factor (landing in
    ``stack.extra``), so their stack.json already had it. LOCAL runs instead
    identify the model via the *agent* profile (e.g. ``agent=hermes-local``), so
    the model never reached stack.json — which surfaced downstream as ~250 blank
    ``model`` rows in master.db and forced slug-based guessing in the reporting
    layer. Callers resolve the effective model (from the agent profile, the
    ``model=`` factor, or a default) and pass it here so EVERY runner records it
    identically. ``model`` is written last so it is always present even when
    ``stack.extra`` lacks the key.
    """
    resolved = (model or stack.extra.get("model") or "").strip()
    return {
        "language": stack.language,
        "agent": stack.agent,
        "framework": stack.framework,
        **stack.extra,
        "model": resolved,
    }


@dataclass(frozen=True)
class TaskSpec:
    """A task to execute inside the playpen.

    support_dir, when set, is a directory whose contents (data files,
    supporting docs, fixtures, etc.) should be copied into the playpen
    workspace alongside TASK.md before the agent runs. Used for tasks
    where the prompt references external files — e.g. brazil-bench
    needs the kaggle CSVs from the source repo.
    """

    name: str
    description: str
    prompt: str
    validation_script: str | None = None
    timeout_minutes: int = 30
    support_dir: Path | None = None
    # Per-task agent turn cap. None ⇒ inherit from playpen.max_turns
    # (workspace-wide default). Override here for tasks that are
    # substantially bigger than the workspace's typical run — production
    # workloads frequently need 200+ turns.
    max_turns: int | None = None


@dataclass
class RunArtifacts:
    """Artifacts collected from a single playpen execution."""

    output_dir: Path | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_seconds: float = 0.0
    token_count: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def usage_limited(self) -> bool:
        """True if the agent was cut off by a usage/rate limit (not a real
        failure). The runner sets ``metadata['usage_limited']`` when the agent
        output carries a limit signature; such a cell should be re-run on resume,
        never scored as a model failure."""
        return self.metadata.get("usage_limited") == "true"

    def to_dict(self) -> dict:
        return {
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "token_count": self.token_count,
            "succeeded": self.succeeded,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@runtime_checkable
class PlaypenRunner(Protocol):
    """Protocol for playpen execution backends."""

    def provision(self, stack: StackConfig, task: TaskSpec) -> str:
        """Provision an isolated environment. Returns an environment ID."""
        ...

    def execute(self, env_id: str, stack: StackConfig, task: TaskSpec) -> RunArtifacts:
        """Execute the task in the provisioned environment."""
        ...

    def teardown(self, env_id: str) -> None:
        """Clean up the provisioned environment."""
        ...


class RunnerRegistry:
    """Registry of available PlaypenRunner implementations."""

    def __init__(self) -> None:
        self._runners: dict[str, PlaypenRunner] = {}

    def register(self, name: str, runner: PlaypenRunner) -> None:
        """Register a runner instance under the given name."""
        self._runners[name] = runner

    def get(self, name: str) -> PlaypenRunner:
        """Get a runner by name."""
        if name not in self._runners:
            raise KeyError(
                f"Unknown runner: {name!r}. "
                f"Available: {sorted(self._runners.keys())}"
            )
        return self._runners[name]

    def available(self) -> list[str]:
        """List registered runner names."""
        return sorted(self._runners.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._runners

    def __len__(self) -> int:
        return len(self._runners)


def create_default_runner_registry() -> RunnerRegistry:
    """Create a registry with built-in and plugin runners.

    The ``docker`` and ``local`` runners are always registered.
    Additional runners discovered via the ``retort.plugins`` entry-point
    group are added afterwards and may override built-ins.
    """
    from retort.playpen.docker_runner import DockerRunner
    from retort.playpen.local_runner import LocalRunner
    from retort.playpen.metaharness_runner import MetaHarnessRunner

    registry = RunnerRegistry()
    registry.register("docker", DockerRunner())
    registry.register("local", LocalRunner())
    registry.register("metaharness", MetaHarnessRunner())

    from retort.plugins import discover_runners

    for name, runner in discover_runners().items():
        registry.register(name, runner)

    return registry
