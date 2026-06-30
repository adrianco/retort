"""MetaHarness playpen runner — benchmarks an agentic-orchestration harness.

Where ``LocalRunner`` invokes a single agent CLI (claude-code / gemini / omp),
this runner invokes the **MetaHarness** agentic harness: a bounded ReAct loop
with model *routing* (a cheap default model that escalates to a frontier model
on repeated build/test failures) and optional copy-on-write (agenticow) memory.

The harness itself lives outside Retort (it is the thing being benchmarked). This
runner is the thin adapter: it provisions an isolated workspace exactly like
``LocalRunner`` (TASK.md + stack.json + git init + support files), shells out to
the harness's greenfield solver with the workspace as cwd, and collects the
token/cost telemetry the solver reports. Retort's own scorers then build, test,
and grade the workspace — this runner touches nothing in the scoring path, so a
``metaharness`` cell is directly comparable to a ``claude-code`` cell.

Selection: set ``playpen.runner: metaharness`` in workspace.yaml. The harness
solver is located via the ``METAHARNESS_SOLVER`` env var (path to the solver
entrypoint, e.g. ``…/bench/retort/greenfield-solve.mjs``). The cheap/frontier
model levels come from the ``model`` / ``escalate`` design-matrix factors (or the
``METAHARNESS_MODEL`` / ``METAHARNESS_ESCALATE`` env defaults). The OpenRouter key
stays server-side: it is read from the inherited environment and passed only to
the solver subprocess, never written into the workspace or the prompt.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from retort.playpen.local_runner import (
    _USAGE_LIMIT_RE,
    _clone_org_repo,
    _copy_support_files,
)
from retort.playpen.runner import RunArtifacts, StackConfig, TaskSpec

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek/deepseek-v4-pro"
NODE_FLAGS = ["--experimental-strip-types", "--no-warnings"]

# Short, slash-free model-factor levels → OpenRouter ids. Factor levels must be
# slash-free so the archive cell-dir naming (`model=<value>`) and the resume
# cell-name parser don't treat the provider prefix as a path separator. A level
# already containing "/" (an explicit OpenRouter id) is passed through unchanged.
_OPENROUTER_ALIASES = {
    "deepseek-v4-pro": "deepseek/deepseek-v4-pro",
    "glm-5.2": "z-ai/glm-5.2",
    "opus-4.8": "anthropic/claude-opus-4.8",
    "gpt-5.2": "openai/gpt-5.2",
}


def _resolve_openrouter_id(model_level: str) -> str:
    """Translate a slash-free model-factor level to its OpenRouter id."""
    if "/" in model_level:
        return model_level
    return _OPENROUTER_ALIASES.get(model_level, model_level)


# iteration-3 task-difficulty routing factor. The `routing` level selects the
# escalation target for the intrinsic difficulty router in the solver:
#   off  → no escalation (pure cheap model, byte-identical to iteration-2)
#   opus → escalate hard cells to anthropic/claude-opus-4.8 (frontier)
#   glm  → escalate hard cells to z-ai/glm-5.2 (stronger-cheap)
#   on   → default escalation target (opus-4.8)
# An explicit `escalate` level still works and, when present, also turns the
# difficulty router on. The router fires only on intrinsic signals (token burn /
# rewrite churn / build failures), never on gold.
_ROUTING_TARGET = {"opus": "opus-4.8", "glm": "glm-5.2", "on": "opus-4.8"}
_ROUTING_OFF = ("off", "none", "", "false")


def _resolve_routing(routing_level: str, escalate_level: str) -> tuple[str, bool]:
    """Resolve the (escalate_openrouter_id, route_difficulty) pair from factors.

    ``routing_level`` is the design-matrix ``routing`` factor; ``escalate_level``
    is the explicit ``escalate`` factor / env default. Returns the OpenRouter id
    to escalate to (``""`` when no escalation) and whether the difficulty router
    should fire.
    """
    routing = (routing_level or "off").lower()
    route_difficulty = False
    if routing not in _ROUTING_OFF:
        escalate_level = escalate_level or _ROUTING_TARGET.get(routing, "opus-4.8")
        route_difficulty = True
    elif escalate_level:
        route_difficulty = True
    escalate = _resolve_openrouter_id(escalate_level) if escalate_level else ""
    return escalate, route_difficulty


class MetaHarnessRunner:
    """Executes experiment runs by driving the MetaHarness agentic harness.

    Mirrors ``LocalRunner``'s isolation and artifact contract so Retort's
    lifecycle (provision → execute → score → teardown) and scorers work
    unchanged. The difference is *which* agent fills the workspace: an agentic
    ReAct loop with model routing, not a single CLI invocation.
    """

    def __init__(
        self,
        *,
        timeout_minutes: int = 30,
        max_turns: int = 40,
        default_model: str | None = None,
        work_dir: Path | None = None,
        solver: str | None = None,
        node_bin: str | None = None,
    ) -> None:
        self.timeout_minutes = timeout_minutes
        self.max_turns = max_turns
        self.default_model = default_model or os.environ.get("METAHARNESS_MODEL") or DEFAULT_MODEL
        self.solver = solver or os.environ.get("METAHARNESS_SOLVER")
        self.node_bin = node_bin or os.environ.get("METAHARNESS_NODE") or "node"
        import tempfile
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="retort-metaharness-"))
        self._envs: dict[str, _EnvInfo] = {}

    # -- lifecycle -----------------------------------------------------------

    def provision(self, stack: StackConfig, task: TaskSpec) -> str:
        """Create an isolated workspace with the task spec (mirrors LocalRunner)."""
        env_id = f"retort-{uuid.uuid4().hex[:12]}"
        env_dir = self.work_dir / env_id
        env_dir.mkdir(parents=True, exist_ok=True)

        if task.support_dir is not None:
            _copy_support_files(task.support_dir, env_dir)

        (env_dir / "TASK.md").write_text(task.prompt)

        stack_data: dict[str, str] = {
            "language": stack.language,
            "agent": stack.agent,
            "framework": stack.framework,
            **stack.extra,
        }
        (env_dir / "stack.json").write_text(json.dumps(stack_data))

        if not (env_dir / ".git").exists():
            org_context = stack.extra.get("org_context", "none")
            if org_context != "none":
                _clone_org_repo(env_dir, org_context)
            else:
                subprocess.run(["git", "init", "-q"], cwd=env_dir, capture_output=True)

        self._envs[env_id] = _EnvInfo(env_id=env_id, workspace=env_dir, stack=stack, task=task)
        logger.info("Provisioned metaharness env %s at %s", env_id, env_dir)
        return env_id

    def execute(self, env_id: str, stack: StackConfig, task: TaskSpec) -> RunArtifacts:
        """Run the MetaHarness greenfield solver in the workspace directory."""
        info = self._envs.get(env_id)
        if info is None:
            return RunArtifacts(stderr=f"Unknown environment: {env_id}", exit_code=1)

        if not self.solver:
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=(
                    "METAHARNESS_SOLVER is not set. Point it at the harness solver "
                    "entrypoint (e.g. .../bench/retort/greenfield-solve.mjs)."
                ),
                exit_code=1,
            )
        if not Path(self.solver).exists():
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=f"MetaHarness solver not found at {self.solver!r}",
                exit_code=1,
            )

        model = _resolve_openrouter_id(stack.extra.get("model") or self.default_model)
        effective_max_turns = task.max_turns if task.max_turns is not None else self.max_turns

        # iteration-3 task-difficulty routing factor — see `_resolve_routing`.
        routing = str(stack.extra.get("routing", "off")).lower()
        escalate_level = stack.extra.get("escalate") or os.environ.get("METAHARNESS_ESCALATE", "")
        escalate, route_difficulty = _resolve_routing(routing, escalate_level)

        cmd = [
            self.node_bin, *NODE_FLAGS, self.solver,
            "--lang", stack.language,
            "--model", model,
            "--max-steps", str(effective_max_turns),
            "--out", "metaharness-result.json",
        ]
        if escalate:
            cmd += ["--escalate", escalate]
        if route_difficulty:
            cmd.append("--route-difficulty")
        if stack.extra.get("memory", "none") not in ("none", "off", "", "false"):
            cmd.append("--memory")

        timeout_secs = self.timeout_minutes * 60
        start = time.monotonic()
        logger.info("Executing metaharness (model=%s escalate=%s) in %s", model, escalate or "-", info.workspace)

        try:
            result = subprocess.run(
                cmd,
                cwd=info.workspace,
                capture_output=True,
                text=True,
                timeout=timeout_secs,
                env=self._build_env(),
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
                stderr=f"Node runtime not found ({self.node_bin!r}): {exc}",
                exit_code=127,
            )

        elapsed = time.monotonic() - start
        token_count, cost_usd, meta = _parse_solver_telemetry(
            result.stdout or "", info.workspace / "metaharness-result.json"
        )
        metadata = {
            "total_cost_usd": str(cost_usd),
            "harness": "metaharness",
            "model": meta.get("model", model),
            "escalated": str(meta.get("escalated", False)).lower(),
            "routing": routing,
            "route_difficulty": str(route_difficulty).lower(),
            "num_turns": str(meta.get("steps", 0)),
            "llm_calls": str(meta.get("calls", 0)),
        }
        if result.returncode != 0 and _USAGE_LIMIT_RE.search((result.stderr or "") + "\n" + (result.stdout or "")):
            metadata["usage_limited"] = "true"

        return RunArtifacts(
            output_dir=info.workspace,
            stdout=(result.stdout or "")[-10000:],
            stderr=(result.stderr or "")[-5000:],
            exit_code=result.returncode,
            duration_seconds=elapsed,
            token_count=token_count,
            metadata=metadata,
        )

    def teardown(self, env_id: str) -> None:
        """Keep the workspace for scoring (mirrors LocalRunner)."""
        info = self._envs.pop(env_id, None)
        if info is not None:
            logger.info("Env %s torn down (workspace kept at %s)", env_id, info.workspace)

    def cleanup_all(self) -> None:
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)

    # -- helpers -------------------------------------------------------------

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        # If the key isn't already exported, let the solver fall back to /tmp/.orkey.
        env.setdefault("METAHARNESS_RUNNER", "1")
        return env


def _parse_solver_telemetry(stdout_text: str, result_path: Path) -> tuple[int, float, dict]:
    """Extract (tokens, cost_usd, meta) from the solver's JSON telemetry.

    The solver prints one JSON summary line on stdout and also writes
    ``metaharness-result.json`` in the workspace. Prefer the file (authoritative),
    fall back to the last parseable JSON object on stdout.
    """
    data: dict | None = None
    try:
        if result_path.exists():
            data = json.loads(result_path.read_text())
    except (ValueError, OSError):
        data = None

    if data is None:
        for line in reversed((stdout_text or "").strip().splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    break
                except ValueError:
                    continue

    if not isinstance(data, dict):
        return 0, 0.0, {}

    tokens = int(data.get("tokens", 0) or 0)
    cost = float(data.get("cost", 0.0) or 0.0)
    meta = {
        "model": data.get("model", ""),
        "escalated": bool(data.get("escalated", False)),
        "steps": int(data.get("steps", 0) or 0),
        "calls": int(data.get("calls", 0) or 0),
    }
    return tokens, cost, meta


class _EnvInfo:
    __slots__ = ("env_id", "workspace", "stack", "task")

    def __init__(self, env_id: str, workspace: Path, stack: StackConfig, task: TaskSpec) -> None:
        self.env_id = env_id
        self.workspace = workspace
        self.stack = stack
        self.task = task
