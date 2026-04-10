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


@dataclass(frozen=True)
class TaskSpec:
    """A task to execute inside the playpen."""

    name: str
    description: str
    prompt: str
    validation_script: str | None = None
    timeout_minutes: int = 30


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
