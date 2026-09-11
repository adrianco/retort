"""Docker-based playpen runner.

Provisions Docker containers for isolated experiment execution.
Uses subprocess to invoke docker commands, avoiding a hard dependency
on the Docker SDK (which may not be available in all environments).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from retort.playpen.runner import (
    RunArtifacts,
    StackConfig,
    TaskSpec,
    stack_metadata,
)

logger = logging.getLogger(__name__)

# Base images per language — overridable via workspace config
DEFAULT_IMAGES: dict[str, str] = {
    "python": "python:3.12-slim",
    "typescript": "node:20-slim",
    "go": "golang:1.22-bookworm",
    "rust": "rust:1.78-slim",
    "elixir": "elixir:1.16",
    "erlang": "erlang:26",
}

DEFAULT_IMAGE = "python:3.12-slim"


class DockerRunner:
    """Executes experiment runs inside Docker containers.

    Each run gets its own container with a mounted workspace directory.
    The agent prompt is written to a file inside the container and the
    configured agent command is executed.
    """

    def __init__(
        self,
        *,
        timeout_minutes: int = 30,
        image_overrides: dict[str, str] | None = None,
        work_dir: Path | None = None,
    ) -> None:
        self.timeout_minutes = timeout_minutes
        self.images = {**DEFAULT_IMAGES, **(image_overrides or {})}
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="retort-"))
        self._containers: dict[str, _ContainerInfo] = {}

    def provision(self, stack: StackConfig, task: TaskSpec) -> str:
        """Create a workspace directory and prepare the container."""
        env_id = f"retort-{uuid.uuid4().hex[:12]}"
        env_dir = self.work_dir / env_id
        env_dir.mkdir(parents=True, exist_ok=True)

        # Write the task prompt
        prompt_file = env_dir / "TASK.md"
        prompt_file.write_text(task.prompt)

        # Write stack metadata — via the shared helper so the model (and every
        # other factor level in stack.extra) is always recorded, consistently
        # with the local/metaharness runners.
        meta_file = env_dir / "stack.json"
        meta_file.write_text(json.dumps(stack_metadata(stack, stack.extra.get("model"))))

        image = self.images.get(stack.language, DEFAULT_IMAGE)
        self._containers[env_id] = _ContainerInfo(
            env_id=env_id,
            image=image,
            workspace=env_dir,
            stack=stack,
            task=task,
        )

        logger.info("Provisioned environment %s (image=%s)", env_id, image)
        return env_id

    def execute(self, env_id: str, stack: StackConfig, task: TaskSpec) -> RunArtifacts:
        """Run the task inside a Docker container."""
        info = self._containers.get(env_id)
        if info is None:
            return RunArtifacts(
                stderr=f"Unknown environment: {env_id}",
                exit_code=1,
            )

        docker = shutil.which("docker")
        if docker is None:
            # No simulation: an invented result is indistinguishable from a
            # real one in the scores. Fail the cell, loudly.
            return RunArtifacts(
                output_dir=info.workspace,
                stderr="docker is not on PATH; DockerRunner cannot execute "
                       "(set playpen.runner: local or install docker)",
                exit_code=1,
            )

        start = time.monotonic()
        timeout_secs = task.timeout_minutes * 60

        cmd = [
            docker, "run", "--rm",
            "--name", env_id,
            "-v", f"{info.workspace}:/workspace",
            "-w", "/workspace",
            "--memory", "2g",
            "--cpus", "2",
            info.image,
            "sh", "-c", self._build_run_command(stack, task),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_secs,
            )
            elapsed = time.monotonic() - start

            return RunArtifacts(
                output_dir=info.workspace,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_seconds=elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            # Kill the container on timeout
            subprocess.run(
                [docker, "kill", env_id],
                capture_output=True,
            )
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=f"Timeout after {elapsed:.0f}s",
                exit_code=124,
                duration_seconds=elapsed,
            )
        except OSError as exc:
            return RunArtifacts(
                stderr=f"Docker execution failed: {exc}",
                exit_code=1,
            )

    def teardown(self, env_id: str) -> None:
        """Remove the workspace directory and container metadata."""
        info = self._containers.pop(env_id, None)
        if info is not None and info.workspace.exists():
            shutil.rmtree(info.workspace, ignore_errors=True)
            logger.info("Torn down environment %s", env_id)

    @staticmethod
    def _build_run_command(stack: StackConfig, task: TaskSpec) -> str:
        """Build the shell command to execute inside the container."""
        # The actual command depends on the agent. For now, execute
        # a basic setup + validation pattern.
        parts = [
            "echo 'Retort playpen run starting'",
            "cat /workspace/TASK.md",
        ]
        if task.validation_script:
            parts.append(f"python /workspace/validate.py")
        parts.append("echo 'Retort playpen run complete'")
        return " && ".join(parts)


class _ContainerInfo:
    """Internal tracking for a provisioned container."""

    __slots__ = ("env_id", "image", "workspace", "stack", "task")

    def __init__(
        self,
        env_id: str,
        image: str,
        workspace: Path,
        stack: StackConfig,
        task: TaskSpec,
    ) -> None:
        self.env_id = env_id
        self.image = image
        self.workspace = workspace
        self.stack = stack
        self.task = task
