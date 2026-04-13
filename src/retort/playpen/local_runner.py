"""Local playpen runner — executes agents directly on the host.

No Docker required. Each run gets an isolated temp directory.
The agent CLI is invoked with the task prompt and the output
is collected for scoring.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from retort.playpen.runner import PlaypenRunner, RunArtifacts, StackConfig, TaskSpec

logger = logging.getLogger(__name__)

# Agent CLI commands — maps agent name to command builder
AGENT_COMMANDS: dict[str, list[str]] = {
    "claude-code": [
        "claude", "-p", "{prompt}",
        "--output-format", "text",
        "--max-turns", "50",
    ],
}


class LocalRunner:
    """Executes experiment runs in local temp directories.

    Each run gets a fresh directory with the task spec. The configured
    agent CLI is invoked and the resulting code is left in the directory
    for scoring.
    """

    def __init__(
        self,
        *,
        timeout_minutes: int = 30,
        max_turns: int = 30,
        work_dir: Path | None = None,
    ) -> None:
        self.timeout_minutes = timeout_minutes
        self.max_turns = max_turns
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="retort-local-"))
        self._envs: dict[str, _EnvInfo] = {}

    def provision(self, stack: StackConfig, task: TaskSpec) -> str:
        """Create a workspace directory with the task spec."""
        env_id = f"retort-{uuid.uuid4().hex[:12]}"
        env_dir = self.work_dir / env_id
        env_dir.mkdir(parents=True, exist_ok=True)

        # Copy supporting files from the task's support_dir, if any. Used
        # for tasks where the prompt references external files (e.g.
        # brazil-bench needs the kaggle CSVs from the source repo). Done
        # FIRST so TASK.md/stack.json overwrite any colliding files in
        # the support tree.
        if task.support_dir is not None:
            _copy_support_files(task.support_dir, env_dir)

        # Write the task prompt (overwrites any TASK.md that came from
        # the support dir — the loader-extracted prompt wins).
        (env_dir / "TASK.md").write_text(task.prompt)

        # Write stack metadata
        (env_dir / "stack.json").write_text(
            f'{{"language": "{stack.language}", '
            f'"agent": "{stack.agent}", '
            f'"framework": "{stack.framework}"}}'
        )

        # Init git repo — many agents expect it. Skip if the support
        # files already brought a .git dir along.
        if not (env_dir / ".git").exists():
            subprocess.run(
                ["git", "init", "-q"],
                cwd=env_dir,
                capture_output=True,
            )

        self._envs[env_id] = _EnvInfo(
            env_id=env_id,
            workspace=env_dir,
            stack=stack,
            task=task,
        )

        logger.info("Provisioned local env %s at %s", env_id, env_dir)
        return env_id

    def execute(self, env_id: str, stack: StackConfig, task: TaskSpec) -> RunArtifacts:
        """Run the agent CLI in the workspace directory."""
        info = self._envs.get(env_id)
        if info is None:
            return RunArtifacts(
                stderr=f"Unknown environment: {env_id}",
                exit_code=1,
            )

        cmd = self._build_agent_command(stack, task)
        if cmd is None:
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=f"No agent command configured for: {stack.agent}",
                exit_code=1,
            )

        timeout_secs = self.timeout_minutes * 60
        start = time.monotonic()

        logger.info("Executing %s in %s", stack.agent, info.workspace)

        try:
            result = subprocess.run(
                cmd,
                cwd=info.workspace,
                capture_output=True,
                text=True,
                timeout=timeout_secs,
                env=self._build_env(stack),
            )
            elapsed = time.monotonic() - start

            # Parse token usage from JSON output
            token_count = 0
            cost_usd = 0.0
            metadata = {}
            stdout_text = result.stdout or ""
            try:
                import json as _json
                data = _json.loads(stdout_text)
                usage = data.get("usage", {})
                token_count = (
                    usage.get("input_tokens", 0)
                    + usage.get("output_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                )
                cost_usd = data.get("total_cost_usd", 0.0)
                metadata = {
                    "input_tokens": str(usage.get("input_tokens", 0)),
                    "output_tokens": str(usage.get("output_tokens", 0)),
                    "cache_read_input_tokens": str(usage.get("cache_read_input_tokens", 0)),
                    "cache_creation_input_tokens": str(usage.get("cache_creation_input_tokens", 0)),
                    "total_cost_usd": str(cost_usd),
                    "num_turns": str(data.get("num_turns", 0)),
                    "duration_api_ms": str(data.get("duration_api_ms", 0)),
                    "stop_reason": data.get("stop_reason", ""),
                }
            except (ValueError, KeyError):
                pass  # Not JSON or missing fields

            return RunArtifacts(
                output_dir=info.workspace,
                stdout=stdout_text[-10000:],
                stderr=result.stderr[-5000:] if result.stderr else "",
                exit_code=result.returncode,
                duration_seconds=elapsed,
                token_count=token_count,
                metadata=metadata,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=f"Timeout after {elapsed:.0f}s",
                exit_code=124,
                duration_seconds=elapsed,
            )
        except FileNotFoundError as exc:
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=f"Agent CLI not found: {exc}",
                exit_code=127,
            )

    def teardown(self, env_id: str) -> None:
        """Optionally clean up. We keep the workspace for scoring."""
        info = self._envs.pop(env_id, None)
        if info is not None:
            logger.info("Env %s torn down (workspace kept at %s)", env_id, info.workspace)

    def cleanup_all(self) -> None:
        """Remove the entire work directory after all scoring is done."""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)

    def _build_agent_command(self, stack: StackConfig, task: TaskSpec) -> list[str] | None:
        """Build the CLI command to invoke the agent."""
        agent = stack.agent if stack.agent != "unknown" else "claude-code"
        if agent == "claude-code":
            prompt = (
                f"You are working in {stack.language}. "
                f"Read TASK.md in the current directory and implement everything it asks for. "
                f"Write all code files to the current directory. "
                f"Make sure the code builds and tests pass."
            )

            # Check for beads/tooling factor
            tooling = stack.extra.get("tooling", "none")
            if tooling == "beads":
                prompt += (
                    " Use bd (beads) for task tracking. "
                    "Run bd init first, then bd create for each subtask, "
                    "bd update --claim to claim work, and bd close when done."
                )

            # Per-task max_turns wins over workspace-wide setting if set.
            effective_max_turns = task.max_turns if task.max_turns is not None else self.max_turns
            cmd = [
                "claude",
                "-p", prompt,
                "--output-format", "json",
                "--max-turns", str(effective_max_turns),
                "--dangerously-skip-permissions",
            ]

            # Check for model factor
            model = stack.extra.get("model", "")
            if model == "sonnet":
                cmd.extend(["--model", "sonnet"])
            elif model == "opus":
                cmd.extend(["--model", "opus"])

            return cmd

        # Other agents: return None (not implemented)
        logger.warning("Agent %r not implemented, skipping", stack.agent)
        return None

    def _build_env(self, stack: StackConfig) -> dict[str, str]:
        """Build environment variables for the agent process."""
        import os
        env = os.environ.copy()
        # Disable interactive features
        env["CLAUDE_CODE_NON_INTERACTIVE"] = "1"
        return env


def _copy_support_files(src: Path, dst: Path) -> None:
    """Copy the contents of src into dst, skipping the source's .git dir.

    Used by LocalRunner.provision to bring task support files (data
    fixtures, supporting docs, etc.) into the workspace alongside the
    prompt. The agent gets a fresh git repo (initialized later), not
    the source repo's history.
    """
    for item in src.iterdir():
        if item.name == ".git":
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


class _EnvInfo:
    """Internal tracking for a provisioned environment."""

    __slots__ = ("env_id", "workspace", "stack", "task")

    def __init__(
        self,
        env_id: str,
        workspace: Path,
        stack: StackConfig,
        task: TaskSpec,
    ) -> None:
        self.env_id = env_id
        self.workspace = workspace
        self.stack = stack
        self.task = task
