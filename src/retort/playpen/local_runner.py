"""Local playpen runner — executes agents directly on the host.

No Docker required. Each run gets an isolated temp directory.
The agent CLI is invoked with the task prompt and the output
is collected for scoring.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from retort.config.schema import LocalAgentConfig, LocalInferenceCost
from retort.playpen.runner import PlaypenRunner, RunArtifacts, StackConfig, TaskSpec

logger = logging.getLogger(__name__)

# Files/dirs that are seeded into the workspace (task spec, support data, the
# agent's own telemetry) rather than produced by the agent. Excluded from the
# progress fingerprint so the stall detector keys on the agent *writing code*.
_PROGRESS_SKIP_DIRS = {".git", "data", "__pycache__", "node_modules", "target", ".venv"}
_PROGRESS_SKIP_FILES = {
    "_agent_stdout.log", "_agent_stderr.log", ".hermes_usage.json",
    "TASK.md", "stack.json", "README.md", "prompts.txt",
}


def _playpen_root() -> Path:
    """Root for playpen workspaces — under $HOME, never the system temp dir.

    Agents refuse to write into paths they consider system-owned (macOS
    ``mkdtemp`` returns ``/var/folders/...``, and ``/var`` trips Hermes'
    sensitive-path guard). Keeping playpens under ``~/.retort/work`` lets the
    agent's normal file tools work.
    """
    root = Path.home() / ".retort" / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _progress_fingerprint(workspace: Path) -> tuple[int, int, int]:
    """(file_count, total_size, max_mtime_ns) over agent-produced files.

    A change in this fingerprint between polls means the agent wrote or grew a
    file — i.e. it is making productive progress. Seeded/support files and the
    agent's own logs are excluded so provisioning doesn't read as progress.
    """
    count = 0
    size = 0
    mtime_ns = 0
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in _PROGRESS_SKIP_DIRS]
        for name in files:
            if name in _PROGRESS_SKIP_FILES or name.endswith((".stdout", ".stderr")):
                continue
            try:
                st = (Path(root) / name).stat()
            except OSError:
                continue
            count += 1
            size += st.st_size
            if st.st_mtime_ns > mtime_ns:
                mtime_ns = st.st_mtime_ns
    return count, size, mtime_ns


def _kill_proc_tree(proc: subprocess.Popen) -> None:
    """SIGTERM then SIGKILL the process's whole session (agent + children)."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue


def _run_with_progress_guard(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    hard_wall_secs: int,
    stall_secs: int,
    poll_secs: int = 15,
) -> tuple[int, str, str, float, str | None]:
    """Run ``cmd`` under two independent limits, returning
    ``(returncode, stdout, stderr, elapsed, kill_reason)``.

    - **hard wall** (``hard_wall_secs``): an absolute backstop set high, so
      genuinely slow-but-productive work is allowed to finish. ``kill_reason`` →
      ``"hard_wall"``.
    - **stall** (``stall_secs``, 0 disables): kill early when the run makes NO
      progress for this long — neither new agent output nor any workspace file
      change. This is the *unproductive loop / hang* guard, so a stuck run dies
      in minutes instead of burning the whole wall. ``kill_reason`` → ``"stall"``.

    A run that streams output or keeps writing files resets the stall clock every
    poll, so long single-turn generation is never mistaken for a stall.
    """
    out_path = cwd / "_agent_stdout.log"
    err_path = cwd / "_agent_stderr.log"
    reason: str | None = None
    with open(out_path, "wb") as out_f, open(err_path, "wb") as err_f:
        proc = subprocess.Popen(
            cmd, cwd=cwd, env=env, stdout=out_f, stderr=err_f,
            start_new_session=True,
        )
        start = time.monotonic()
        last_progress = start
        last_signal: tuple[int, int, int, int] = (0, 0, 0, 0)
        while True:
            try:
                proc.wait(timeout=poll_secs)
                break  # exited on its own
            except subprocess.TimeoutExpired:
                pass
            now = time.monotonic()
            try:
                out_sz = out_path.stat().st_size + err_path.stat().st_size
            except OSError:
                out_sz = 0
            fp = _progress_fingerprint(cwd)
            cur = (out_sz, *fp)
            if cur != last_signal:
                last_progress = now
                last_signal = cur
            if now - start > hard_wall_secs:
                reason = "hard_wall"
                break
            if stall_secs and (now - last_progress) > stall_secs:
                reason = "stall"
                break
        if reason:
            _kill_proc_tree(proc)
    elapsed = time.monotonic() - start
    try:
        stdout_text = out_path.read_text(errors="replace")
    except OSError:
        stdout_text = ""
    try:
        stderr_text = err_path.read_text(errors="replace")
    except OSError:
        stderr_text = ""
    rc = proc.returncode if proc.returncode is not None else 124
    return rc, stdout_text, stderr_text, elapsed, reason

# Agent CLI commands — maps agent name to command builder
AGENT_COMMANDS: dict[str, list[str]] = {
    "claude-code": [
        "claude", "-p", "{prompt}",
        "--output-format", "text",
        "--max-turns", "50",
    ],
}

# Short aliases track the latest stable release; versioned aliases (e.g. "opus-4.6") pin to a specific release.
MODEL_ALIASES: dict[str, str] = {
    # Short aliases — update when a new model generation ships
    "opus": "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
    # Versioned aliases — never change; enable cross-version comparisons
    "opus-4.6": "claude-opus-4-6",
    "opus-4.7": "claude-opus-4-7",
    "opus-4.8": "claude-opus-4-8",
    "sonnet-4.5": "claude-sonnet-4-5",
    "sonnet-4.6": "claude-sonnet-4-6",
    "sonnet-5": "claude-sonnet-5",
    "sonnet5": "claude-sonnet-5",
    "haiku-4.5": "claude-haiku-4-5",
    "fable-5": "claude-fable-5",
    # Fast-mode variant: a "<id>-fast" model level runs the same model with
    # Claude Code fast mode on (faster output) — handled in _build_agent_command.
    "opus-4.8-fast": "claude-opus-4-8-fast",
}


# Signatures an agent CLI emits when it's cut off by a usage / rate limit (a
# 5-hour or weekly cap, a 429, exhausted quota). A run that ends this way did NOT
# fail on the model's merits — it never got to do the work — so the caller treats
# it as "not attempted" (re-run on resume) rather than scoring it as a failure.
_USAGE_LIMIT_RE = re.compile(
    r"usage limit|rate.?limit|limit reached|limit will reset|too many requests"
    r"|\b429\b|insufficient.*quota|quota.*exceeded|/upgrade to increase",
    re.IGNORECASE,
)

# An agent whose file-writing tool is BLOCKED produces no code and scores a false
# zero — indistinguishable, in the metrics, from a model that simply can't do the
# task. That cost us ~10 experiments: playpens lived under macOS /var/folders, and
# Hermes refuses to write to anything under /var ("Refusing to write to sensitive
# system path"), so 41/48 runs in exp-27 were quietly fighting the harness.
# Detect it and stop the experiment rather than record garbage.
_TOOL_REFUSAL_RE = re.compile(
    r"Refusing to (?:write|create|modify)[^\n]{0,160}"
    r"|File-mutation verifier:[^\n]{0,160}NOT modified[^\n]{0,80}"
    r"|(?:permission denied|read-only file system)[^\n]{0,80}",
    re.IGNORECASE,
)


def _model_cli_args(model_level: str) -> list[str]:
    """``claude`` CLI args selecting a model factor/level.

    Returns ``--model <id>`` plus the fast-mode ``--settings`` when the level
    carries a ``-fast`` suffix. Fast mode is a Claude Code *setting*, not a
    distinct model ID, so the suffix is stripped and ``{"fastMode": true}`` is
    passed instead. Shared by the agent run and the second-opinion eval so both
    drive fast-mode models the same way. Empty input → no args.
    """
    if not model_level:
        return []
    resolved = MODEL_ALIASES.get(model_level, model_level)
    extra: list[str] = []
    if resolved.endswith("-fast"):
        resolved = resolved[: -len("-fast")]
        extra = ["--settings", '{"fastMode": true}']
    return ["--model", resolved, *extra]


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
        stall_minutes: int = 0,
        max_turns: int = 30,
        default_model: str | None = None,
        default_thinking: str | None = None,
        local_agents: dict[str, LocalAgentConfig] | None = None,
        work_dir: Path | None = None,
        eval_model: str | None = None,
        local_inference_cost: LocalInferenceCost | None = None,
        prompts_dir: Path | None = None,
        stack_manager: "OmlxStackManager | None" = None,
    ) -> None:
        self.timeout_minutes = timeout_minutes
        # Stall guard: kill a run that makes no progress for this many minutes
        # (0 disables). Lets a high timeout_minutes be a backstop for slow-but-
        # productive work while unproductive loops still die fast.
        self.stall_minutes = stall_minutes
        # Reloads the local serving stack (oMLX model + sampling params) when a
        # cell's model factor names a different stack preset — the model-
        # selection point of a within-experiment sampling/quant sweep.
        self.stack_manager = stack_manager
        self.max_turns = max_turns
        self.default_model = default_model
        self.default_thinking = default_thinking
        self.local_agents = local_agents or {}
        # Playpens live under $HOME, NOT the system temp dir. On macOS mkdtemp()
        # lands in /var/folders/..., and agents' safety guards classify anything
        # under /var as a "sensitive system path" — Hermes then REFUSES every
        # write_file into the workspace ("Refusing to write to sensitive system
        # path: app.py"). A resilient model routes around it via the shell (burning
        # turns); a less resilient one writes nothing at all and scores a false
        # zero. This silently depressed every local Hermes run (41/48 in exp-27,
        # 6/6 in exp-26) until it was caught in exp-28.
        self.work_dir = work_dir or Path(tempfile.mkdtemp(
            prefix="retort-local-", dir=_playpen_root()
        ))
        self._envs: dict[str, _EnvInfo] = {}
        # When set, invoke evaluate-run skill after each successful run.
        self.eval_model = eval_model
        # When set, compute run cost from hardware model instead of agent-reported cost.
        self.local_inference_cost = local_inference_cost
        # Directory containing named prompt files (<name>.md) for the prompt factor.
        # None means prompt injection is disabled (factor absent or always "none").
        self.prompts_dir = prompts_dir

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

        # Write stack metadata — include all factor levels so evaluate-run
        # has full context (model, tooling, etc. alongside language/agent).
        stack_data: dict[str, str] = {
            "language": stack.language,
            "agent": stack.agent,
            "framework": stack.framework,
            **stack.extra,
        }
        (env_dir / "stack.json").write_text(json.dumps(stack_data))

        # Init git repo — many agents expect it. Skip if the support
        # files already brought a .git dir along.
        if not (env_dir / ".git").exists():
            org_context = stack.extra.get("org_context", "none")
            if org_context != "none":
                _clone_org_repo(env_dir, org_context)
            else:
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
            # Snapshot the seeded workspace so execute() can tell whether the
            # agent wrote ANYTHING (see the no-write harness check).
            seed_fp=_progress_fingerprint(env_dir),
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

        # Model-selection point: if this cell names a different serving-stack
        # preset (model weights / sampling params) than is currently loaded,
        # reload it before running. No-op when the preset is unchanged, so a
        # design sorted by preset reloads only at each boundary. The preset is a
        # dedicated ``stack`` factor — NOT ``model``, which the CLI passes to the
        # agent as the served model id.
        if self.stack_manager is not None:
            preset = stack.extra.get("stack")
            try:
                self.stack_manager.ensure(preset)
            except Exception as exc:  # never let a reload error abort the run silently
                return RunArtifacts(
                    output_dir=info.workspace,
                    stderr=f"Stack reload failed for preset {preset!r}: {exc}",
                    exit_code=1,
                )

        try:
            cmd = self._build_agent_command(stack, task, info.workspace)
        except ValueError as exc:
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=str(exc),
                exit_code=1,
            )

        env = self._build_env(stack)
        if self._resolve_harness(stack) == "opencode":
            self._write_opencode_config(info.workspace, stack)
            env["OPENCODE_DB"] = str(self._opencode_db_path(info.workspace))

        hard_wall_secs = self.timeout_minutes * 60
        stall_secs = self.stall_minutes * 60  # 0 ⇒ stall guard disabled

        # Cursor into the serving log, so we can measure THIS run's peak context.
        log_mark = (
            self.stack_manager.log_offset() if self.stack_manager is not None else None
        )

        logger.info("Executing %s in %s", stack.agent, info.workspace)

        try:
            # Run under the progress guard: a high hard wall lets slow-but-
            # productive work finish, while the stall guard kills a run that
            # makes no progress (no new output, no file writes) — an
            # unproductive loop or hang — in minutes instead of the whole wall.
            returncode, stdout_text, stderr_text, elapsed, kill_reason = (
                _run_with_progress_guard(
                    cmd,
                    cwd=info.workspace,
                    env=env,
                    hard_wall_secs=hard_wall_secs,
                    stall_secs=stall_secs,
                )
            )

            if kill_reason is not None:
                # Killed by a guard. The workspace still holds whatever code the
                # agent wrote, so it is scored downstream; the run is recorded
                # as crashed (exit 124) with a reason for post-hoc diagnosis.
                if kill_reason == "stall":
                    msg = (
                        f"Killed after {elapsed:.0f}s — stalled "
                        f"(no progress for {self.stall_minutes}m, unproductive loop)"
                    )
                else:
                    msg = f"Timeout after {elapsed:.0f}s (hard wall)"
                return RunArtifacts(
                    output_dir=info.workspace,
                    stderr=(stderr_text[-5000:] + "\n" + msg) if stderr_text else msg,
                    exit_code=124,
                    duration_seconds=elapsed,
                    metadata={"kill_reason": kill_reason},
                )

            # stdout/stderr already streamed to _agent_stdout.log/_agent_stderr.log
            # by the guard (same files _persist_agent_output would write), so a
            # failed run stays diagnosable after the workspace is archived.
            # The usage parser must key on the SAME harness the command builder
            # ran (claude-code / omp / gemini / hermes), else total_cost_usd/tokens
            # are silently dropped while runner-measured _duration_seconds survives
            # (the exp-7/8 bug). _resolve_harness derives it from the model, so
            # there is one source of truth for both.
            token_count, metadata = _parse_agent_usage(
                self._resolve_harness(stack), stdout_text, info.workspace
            )
            cost_usd = _parse_float(metadata.get("total_cost_usd"), 0.0)

            # Fast mode bills at 2× but the CLI reports the standard-rate cost —
            # scale it up so the recorded cost is what's actually charged.
            if cost_usd > 0.0 and _is_fast_mode_model(stack.extra.get("model", "")):
                cost_usd *= FAST_MODE_COST_MULTIPLIER
                metadata["total_cost_usd"] = str(cost_usd)
                metadata["fast_mode_cost_multiplier"] = str(FAST_MODE_COST_MULTIPLIER)

            # For local models, compute hardware cost when agent doesn't report API cost.
            if cost_usd == 0.0 and self.local_inference_cost is not None and elapsed > 0:
                cost_usd = self.local_inference_cost.cost_for_run(elapsed)
                metadata["total_cost_usd"] = str(cost_usd)
                if token_count > 0:
                    ept = self.local_inference_cost.effective_cost_per_token(token_count, elapsed)
                    metadata["effective_cost_per_token"] = str(ept)

            # A usage/rate-limit cutoff is not a model failure — flag it so the
            # caller leaves the cell unrecorded (re-run on resume) instead of
            # scoring an incomplete workspace as a failure.
            if returncode != 0 and _USAGE_LIMIT_RE.search(
                stderr_text + "\n" + stdout_text
            ):
                metadata["usage_limited"] = "true"

            # Harness self-check. Neither of these is a *model* result:
            #   tool_refusal  — the agent's file tool was actively blocked.
            #   wrote_nothing — the workspace is byte-for-byte as seeded.
            # Both score a false zero that is indistinguishable from "the model
            # can't do it", so the caller stops the experiment instead of
            # recording garbage (see the no-write check in the run loop).
            refusal = _TOOL_REFUSAL_RE.search(stdout_text + "\n" + stderr_text)
            if refusal:
                metadata["tool_refusal"] = refusal.group(0).strip()[:200]
            final_fp = _progress_fingerprint(info.workspace)
            metadata["files_written"] = str(max(0, final_fp[0] - info.seed_fp[0]))
            if final_fp == info.seed_fp:
                metadata["wrote_nothing"] = "true"

            # Peak context this run actually needed — the largest prompt the model
            # was fed. Says whether a big context window is earning its keep, and
            # a ballooning context is a leading indicator of a non-terminating run.
            if log_mark is not None and self.stack_manager is not None:
                peak = self.stack_manager.peak_prompt_tokens(log_mark)
                if peak:
                    metadata["max_context_tokens"] = str(peak)

            artifacts = RunArtifacts(
                output_dir=info.workspace,
                stdout=stdout_text[-10000:],
                stderr=stderr_text[-5000:] if stderr_text else "",
                exit_code=returncode,
                duration_seconds=elapsed,
                token_count=token_count,
                metadata=metadata,
            )
            if self.eval_model is not None and artifacts.succeeded:
                self._post_run_evaluate(info.workspace)
            return artifacts
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

    def _load_prompt_file(self, prompt_level: str) -> str:
        """Load and return the text for a named prompt level.

        Raises FileNotFoundError with a clear message if the file is missing,
        so misconfigured experiments fail immediately rather than silently
        running without the intended prompt.
        """
        if self.prompts_dir is None:
            raise FileNotFoundError(
                f"prompt factor level {prompt_level!r} requires a prompts directory, "
                f"but none was configured. Create prompts/{prompt_level}.md next to workspace.yaml."
            )
        path = self.prompts_dir / f"{prompt_level}.md"
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {path}\n"
                f"Create prompts/{prompt_level}.md next to workspace.yaml to define this prompt level."
            )
        return path.read_text().strip()

    # opencode tools, granted "allow" so headless runs never auto-deny a tool call.
    _OPENCODE_PERMISSION_TOOLS = ("read", "edit", "glob", "grep", "list", "bash", "task")

    def _write_opencode_config(self, workspace: Path, stack: StackConfig) -> None:
        """Register this run's model + grant permissions in a per-workspace ``opencode.json``.

        opencode validates model ids against its catalog, which ``--pure`` disables;
        a project ``opencode.json`` under ``--dir`` registers the model explicitly
        (the omp ``models.yml`` analog).

        It also grants permissions so the autonomous run isn't auto-denied (the
        headless equivalent of omp/gemini ``--yolo``). The decisive one is
        **``external_directory``**: opencode's default policy is
        ``external_directory: "*" -> ask`` (allowed only for its own tmp/project
        paths), and it treats retort's ``/var/folders/.../<ws>`` workspace as
        *external* — so workspace file access is auto-DENIED in headless and the
        agent aborts mid-task with no code (an intermittent ~10-27% no-code failure,
        root-caused from the recorded sessions + ``--print-logs``). Granting
        ``external_directory: {"*": "allow"}`` (plus the tools) fixes it. Written
        per-workspace so runs are self-contained and never touch a global config.
        """
        model = self._model_for(stack)
        if not model or model == "none":
            return
        prefix = "openrouter/"
        bare = model[len(prefix):] if model.startswith(prefix) else model
        permission: dict[str, object] = {
            t: "allow" for t in self._OPENCODE_PERMISSION_TOOLS
        }
        permission["external_directory"] = {"*": "allow"}
        config = {
            "$schema": "https://opencode.ai/config.json",
            "permission": permission,
            "provider": {"openrouter": {"models": {bare: {}}}},
        }
        (workspace / "opencode.json").write_text(json.dumps(config))

    def _opencode_db_path(self, workspace: Path) -> Path:
        """Per-run SQLite db path for opencode (set via ``OPENCODE_DB``).

        opencode stores all sessions in one shared db under its data dir (default
        ``~/.local/share/opencode/opencode.db``). Concurrent ``opencode run`` processes
        contend on that single db and a fraction fail to start — controlled A/B at
        concurrency 10: shared db 6/10 vs isolated db 10/10, bails failing ~0.4s at
        startup (db-lock contention). ``OPENCODE_DB=<abs path>`` relocates **only the
        db** per run (verified against the binary + empirically); unlike
        ``XDG_DATA_HOME`` it does NOT move ``auth.json`` or config, so no seeding is
        needed and other XDG tools are unaffected. ``OPENCODE_DATA_DIR`` does NOT work
        for this (it's ignored for the db path — the db stays in the default location).
        Also keeps retort out of the user's personal opencode history. The db sits
        beside (not inside) the workspace so it isn't scored/archived; ``cleanup_all``
        reclaims it.

        Note: db isolation fixes only the *startup-lock* concurrency mode and the
        history pollution. A separate intermittent failure (mid-task abort, no code)
        occurs even at concurrency 1, so opencode still needs low concurrency
        (<=3-4 shards) and a tight timeout.
        """
        data_dir = workspace.parent / f"{workspace.name}.ocdata"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "opencode.db"

    def _build_agent_command(
        self, stack: StackConfig, task: TaskSpec, workspace: Path | None = None
    ) -> list[str] | None:
        """Build the CLI command to invoke the agent for this stack.

        The harness follows from the model — the agent is the *same variable* as
        the model, not a separate factor: a `gemini-*` model runs via the Gemini
        CLI, any Claude id via claude-code. So a single `model` factor with mixed
        Claude/Gemini levels routes correctly with no separate `agent` factor.
        An explicit ``local_agents`` profile (omp/custom) overrides the inference.
        """
        harness = self._resolve_harness(stack)
        if harness == "claude-code":
            prompt_level = stack.extra.get("prompt", "none")
            prompt_injection = self._load_prompt_file(prompt_level) if prompt_level != "none" else ""
            prompt = _build_agent_prompt(stack, prompt_injection)

            # Per-task max_turns wins over workspace-wide setting if set.
            effective_max_turns = task.max_turns if task.max_turns is not None else self.max_turns
            cmd = [
                "claude",
                "-p", prompt,
                "--output-format", "json",
                "--max-turns", str(effective_max_turns),
                "--dangerously-skip-permissions",
            ]

            # Resolve model alias → versioned ID (+ fast-mode setting if any).
            cmd.extend(_model_cli_args(stack.extra.get("model", "")))

            return cmd

        if harness == "omp":
            cmd = [
                "omp",
                "-p",
                "--no-session",
                "--mode",
                "json",
            ]

            # Bound the agent, mirroring the claude-code `--max-turns` cap. omp
            # runs until the model stops calling tools; a slow local model that
            # over-iterates (never emitting a final answer) would otherwise run
            # until retort's hard subprocess timeout — which *kills* omp and
            # discards its stdout, so the completed workspace is never scored
            # (it just records "Timeout after Ns", all-zero). `--max-time` makes
            # omp self-terminate gracefully a bit *before* that hard wall, so its
            # output is captured and the code it produced gets built/tested/gated.
            graceful_secs = max(60, self.timeout_minutes * 60 - 120)
            cmd.extend(["--max-time", str(graceful_secs)])

            model = self._model_for(stack)
            if model and model != "none":
                cmd.extend(["--model", model])

            thinking = self._thinking_for(stack)
            if thinking:
                cmd.extend(["--thinking", thinking])

            prompt_level = stack.extra.get("prompt", "none")
            prompt_injection = self._load_prompt_file(prompt_level) if prompt_level != "none" else ""
            cmd.append(_build_agent_prompt(stack, prompt_injection))
            return cmd

        if harness == "hermes":
            # NousResearch Hermes in headless one-shot mode: reads the prompt via
            # `-z`, runs in the playpen cwd, auto-approves tools with `--yolo`.
            # Token/cost telemetry is written to `--usage-file` (Hermes has no
            # JSON usage on stdout), so the parser reads that file, not stdout.
            # Provider + model resolve from ~/.hermes/config.yaml (an
            # openai-compatible `providers.<id>` entry pointing at the local
            # server); the model factor level is passed explicitly with `-m`.
            usage_path = workspace / ".hermes_usage.json"
            cmd = [
                "hermes",
                "--usage-file", str(usage_path),
                "--yolo",
            ]
            model = self._model_for(stack)
            if model and model != "none":
                # Hermes resolves a bare `-m <model>` to no provider ("No LLM
                # provider configured") — it needs the provider explicitly. Encode
                # the profile model as "provider/model" (as omp does) and split it
                # into `--provider <p> -m <m>`; a bare id (no slash) relies on the
                # config's default_provider.
                if "/" in model:
                    provider, model_id = model.split("/", 1)
                    cmd.extend(["--provider", provider, "-m", model_id])
                else:
                    cmd.extend(["-m", model])
            prompt_level = stack.extra.get("prompt", "none")
            prompt_injection = self._load_prompt_file(prompt_level) if prompt_level != "none" else ""
            cmd.extend(["-z", _build_agent_prompt(stack, prompt_injection)])
            return cmd

        if harness == "gemini":
            # Google's Gemini CLI in headless mode: reads TASK.md from the
            # playpen cwd, implements it in place, emits one JSON object.
            # `--yolo` auto-approves tool calls (the non-interactive equivalent
            # of claude's --dangerously-skip-permissions); `--skip-trust` trusts
            # the playpen for this session, else gemini downgrades yolo to its
            # interactive "default" approval mode in an untrusted folder and the
            # run fails (FatalUntrustedWorkspaceError). Auth comes from
            # GEMINI_API_KEY / GOOGLE_API_KEY / ADC / OAuth in the inherited env.
            cmd = ["gemini", "--yolo", "--skip-trust", "--output-format", "json"]

            model = self._model_for(stack)
            if model and model != "none":
                cmd.extend(["--model", model])

            prompt_level = stack.extra.get("prompt", "none")
            prompt_injection = self._load_prompt_file(prompt_level) if prompt_level != "none" else ""
            cmd.extend(["--prompt", _build_agent_prompt(stack, prompt_injection)])
            return cmd

        if harness == "opencode":
            # opencode headless. `--pure` is REQUIRED: without it a plugin hangs
            # the run indefinitely. --pure also disables env-key auth and the
            # models.dev catalog, so auth lives in ~/.local/share/opencode/auth.json
            # and the model is registered in opencode.json (the omp models.yml
            # analog). opencode resolves its workspace from `--dir`, NOT the
            # subprocess cwd, so pass it explicitly. `--format json` streams
            # step_finish events whose part.{cost,tokens} _parse_opencode_usage sums.
            # `--print-logs` sends opencode's internal logs (permission evaluations,
            # step loop, errors) to stderr — separate from the json stdout — so a
            # failed run's persisted _agent_stderr.log shows WHY it failed.
            cmd = ["opencode", "run", "--pure", "--print-logs", "--format", "json"]
            if workspace is not None:
                cmd.extend(["--dir", str(workspace)])

            model = self._model_for(stack)
            if model and model != "none":
                cmd.extend(["--model", model])

            prompt_level = stack.extra.get("prompt", "none")
            prompt_injection = self._load_prompt_file(prompt_level) if prompt_level != "none" else ""
            cmd.append(_build_agent_prompt(stack, prompt_injection))
            return cmd

        # Unreachable: _resolve_harness returns claude-code / omp / gemini / opencode.
        raise ValueError(
            f"No command builder for harness {harness!r} "
            f"(agent={stack.agent!r}, model={self._model_for(stack)!r})."
        )

    def _model_for(self, stack: StackConfig) -> str:
        """Return design-matrix model, profile default, then playpen default."""
        profile = self.local_agents.get(stack.agent)
        profile_model = profile.model if profile is not None else None
        return str(stack.extra.get("model") or profile_model or self.default_model or "")

    def _thinking_for(self, stack: StackConfig) -> str:
        """Return design-matrix thinking, profile default, then playpen default."""
        profile = self.local_agents.get(stack.agent)
        profile_thinking = profile.thinking if profile is not None else None
        thinking = stack.extra.get("thinking") or profile_thinking or self.default_thinking or ""
        if str(thinking).lower() in {"", "none", "default", "off", "false"}:
            return ""
        return str(thinking)

    def _resolve_harness(self, stack: StackConfig) -> str:
        """Resolve which agent harness runs this stack — the single source of
        truth for both command building and usage parsing.

        Precedence: an explicit ``local_agents`` profile (omp/custom) wins; then
        an explicit built-in agent name; otherwise the harness is inferred from
        the model, so the agent is the *same variable* as the model and a lone
        `model` factor with mixed Claude/Gemini levels routes with no `agent`
        factor at all.
        """
        profile = self.local_agents.get(stack.agent)
        if profile is not None:
            return profile.harness
        if stack.agent in ("claude-code", "gemini", "omp", "opencode"):
            return stack.agent
        return _harness_for_model(self._model_for(stack))

    def _build_env(self, stack: StackConfig) -> dict[str, str]:
        """Build environment variables for the agent process."""
        import os
        env = os.environ.copy()
        # Disable interactive features
        env["CLAUDE_CODE_NON_INTERACTIVE"] = "1"
        return env

    def _post_run_evaluate(self, run_dir: Path) -> None:
        """Invoke the evaluate-run skill on a completed workspace.

        Produces evaluation.md and findings.jsonl in run_dir. Never raises;
        failures are logged and skipped. Does NOT call file-run-issues —
        findings.jsonl is consumed by the scorer, not the issue tracker.
        """
        skill = _find_skill_path("evaluate-run", start=run_dir)
        if skill is None:
            logger.debug("evaluate-run skill not found, skipping post-run evaluation")
            return

        prompt = f"Follow skill at {skill} for run_dir={run_dir}"
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, *_model_cli_args(self.eval_model or ""),
                 "--output-format", "text", "--dangerously-skip-permissions"],
                cwd=run_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                logger.warning("evaluate-run exited %d: %s", proc.returncode, proc.stderr[:200])
        except FileNotFoundError:
            logger.warning("claude CLI not found, skipping evaluate-run")
        except subprocess.TimeoutExpired:
            logger.warning("evaluate-run timed out after 300s for %s", run_dir.name)
        except Exception as exc:
            logger.warning("evaluate-run error for %s: %s", run_dir.name, exc)


def _find_skill_path(skill_name: str, start: Path) -> Path | None:
    """Walk upward from start to locate skills/<name>/SKILL.md."""
    for base in [start, *start.parents]:
        candidate = base / "skills" / skill_name / "SKILL.md"
        if candidate.is_file():
            return candidate
    return None


def _build_agent_prompt(stack: StackConfig, prompt_injection: str = "") -> str:
    """Build the common implementation prompt used by local coding agents."""
    prompt = (
        f"You are working in {stack.language}. "
        f"Read TASK.md in the current directory and implement everything it "
        f"asks for. "
        f"Write all code files to the current directory. "
        f"Make sure the code builds and tests pass."
    )

    tooling = stack.extra.get("tooling", "none")
    if tooling == "beads":
        prompt += (
            " Use bd (beads) for task tracking. "
            "Run bd init first, then bd create for each subtask, "
            "bd update --claim to claim work, and bd close when done."
        )

    if prompt_injection:
        prompt += " " + prompt_injection

    return prompt


def _persist_agent_output(workspace: Path, stdout: str, stderr: str) -> None:
    """Write the agent's raw stdout/stderr into the run dir for post-hoc diagnosis.

    The full ``--format json`` / ``--mode json`` stream and stderr are often the
    only record of WHY an agent run failed (a denied tool permission, an empty
    model response, a hung step). Persisted as ``_agent_stdout.log`` /
    ``_agent_stderr.log`` (underscore-prefixed ``.log`` so scorers ignore them);
    the workspace is the archive, so these survive into ``runs/.../repN/``.
    """
    try:
        (workspace / "_agent_stdout.log").write_text(stdout)
        (workspace / "_agent_stderr.log").write_text(stderr)
    except OSError:
        logger.debug("Failed to persist agent output in %s", workspace)


def _parse_agent_usage(
    agent: str, stdout_text: str, workspace: Path | None = None
) -> tuple[int, dict[str, str]]:
    """Parse token/cost metadata from known local-agent output formats."""
    if agent == "claude-code":
        return _parse_claude_usage(stdout_text)
    if agent == "omp":
        return _parse_omp_usage(stdout_text)
    if agent == "opencode":
        return _parse_opencode_usage(stdout_text)
    if agent == "gemini":
        return _parse_gemini_usage(stdout_text)
    if agent == "hermes":
        # Hermes writes telemetry to a --usage-file in the playpen, not stdout.
        return _parse_hermes_usage(workspace)
    return 0, {}


def _parse_hermes_usage(workspace: Path | None) -> tuple[int, dict[str, str]]:
    """Read Hermes' ``--usage-file`` JSON (.hermes_usage.json) from the playpen.

    Fields: input_tokens / output_tokens / total_tokens / estimated_cost_usd /
    completed / failed. Local inference reports a null cost, so cost falls back
    to 0 (the runner then applies any configured hardware-cost model).
    """
    if workspace is None:
        return 0, {}
    path = workspace / ".hermes_usage.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return 0, {}
    total = data.get("total_tokens")
    if total is None:
        total = (data.get("input_tokens") or 0) + (data.get("output_tokens") or 0)
    metadata: dict[str, str] = {}
    cost = data.get("estimated_cost_usd")
    metadata["total_cost_usd"] = str(cost if cost is not None else 0.0)
    if data.get("model"):
        metadata["model"] = str(data["model"])
    return int(total or 0), metadata


def _parse_float(value: str | None, default: float) -> float:
    """Parse a float metadata field without letting bad telemetry abort a run."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Claude Code **fast mode** (the `/fast` toggle / fastMode setting) is billed at
# exactly 2× the standard per-token rate for Opus 4.8 (input $5→$10, output
# $25→$50 per Mtok; cache rates scale the same), per the 4.8 announcement:
# https://www.anthropic.com/news/claude-opus-4-8
# BUT the CLI's reported `total_cost_usd` computes at the STANDARD rate — verified
# by probe: a fast-mode call reports the standard-priced figure, not 2×. So to
# record the cost the user is actually billed, multiply fast-mode runs by this.
FAST_MODE_COST_MULTIPLIER = 2.0


def _is_fast_mode_model(model: str) -> bool:
    """True if a model factor selects Claude Code fast mode (a `-fast` suffix)."""
    if not model:
        return False
    return MODEL_ALIASES.get(model, model).endswith("-fast")


def _harness_for_model(model: str) -> str:
    """Infer the agent harness from the model id — the agent follows from the
    model, so a single `model` factor selects both. A `gemini-*` id runs via the
    Gemini CLI; every Claude id (claude-*/opus/sonnet/haiku/fable, including the
    short aliases) runs via claude-code. Local/omp models are not name-inferable,
    so they route via an explicit ``local_agents`` profile instead of this rule.
    """
    resolved = MODEL_ALIASES.get(model, model)
    if resolved.startswith("gemini") or resolved.startswith("models/gemini"):
        return "gemini"
    return "claude-code"


def _parse_claude_usage(stdout_text: str) -> tuple[int, dict[str, str]]:
    """Parse Claude Code's single JSON object output."""
    try:
        data = json.loads(stdout_text)
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
            "cache_creation_input_tokens": str(
                usage.get("cache_creation_input_tokens", 0)
            ),
            "total_cost_usd": str(cost_usd),
            "num_turns": str(data.get("num_turns", 0)),
            "duration_api_ms": str(data.get("duration_api_ms", 0)),
            "stop_reason": data.get("stop_reason", ""),
        }
        return token_count, metadata
    except (ValueError, KeyError):
        return 0, {}


def _parse_omp_usage(stdout_text: str) -> tuple[int, dict[str, str]]:
    """Parse OMP's newline-delimited JSON events.

    omp emits one ``message_end`` per assistant turn, each carrying *that turn's*
    usage (not a running total). Per-run cost and tokens are therefore the **sum
    across turns** — taking only the final turn (the old "last-wins" behaviour)
    badly under-counts a multi-turn agentic run. Observed on a 14-turn run: the
    final turn was $0.0097 but the summed cost was $0.1399 (-93%), and the sum
    matched OpenRouter's billed ``/generation`` total exactly.

    For OpenRouter-routed runs we also capture each call's ``responseId`` and the
    ``upstreamProvider`` so spend can be reconciled per run against the billing
    API. These extra fields appear only when present, so local/offline omp runs
    are unchanged in shape. ``omp_cost_sum_all_turns`` mirrors ``total_cost_usd``
    (kept as explicit provenance for the reconcile/validator).
    """
    provider = ""
    model = ""
    stop_reason = ""
    response_ids: list[str] = []
    upstreams: list[str] = []
    input_sum = output_sum = cache_read_sum = cache_write_sum = 0
    total_tokens_sum = 0
    cost_sum = 0.0
    assistant_turns = 0

    for line in stdout_text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue

        message = event.get("message")
        if not isinstance(message, dict):
            continue
        if event.get("type") != "message_end":
            continue

        provider = str(message.get("provider") or provider)
        model = str(message.get("model") or model)
        stop_reason = str(message.get("stopReason") or stop_reason)

        rid = message.get("responseId")
        if rid and (not response_ids or response_ids[-1] != str(rid)):
            response_ids.append(str(rid))
        upstream = message.get("upstreamProvider")
        if upstream and str(upstream) not in upstreams:
            upstreams.append(str(upstream))

        usage = message.get("usage")
        if isinstance(usage, dict):
            assistant_turns += 1
            t_in = int(usage.get("input", 0) or 0)
            t_out = int(usage.get("output", 0) or 0)
            t_cr = int(usage.get("cacheRead", 0) or 0)
            t_cw = int(usage.get("cacheWrite", 0) or 0)
            input_sum += t_in
            output_sum += t_out
            cache_read_sum += t_cr
            cache_write_sum += t_cw
            total_tokens_sum += int(usage.get("totalTokens", t_in + t_out + t_cr + t_cw) or 0)
            turn_cost = usage.get("cost")
            if isinstance(turn_cost, dict):
                cost_sum += float(turn_cost.get("total", 0.0) or 0.0)

    if assistant_turns == 0:
        return 0, {}

    metadata = {
        "input_tokens": str(input_sum),
        "output_tokens": str(output_sum),
        "cache_read_input_tokens": str(cache_read_sum),
        "cache_creation_input_tokens": str(cache_write_sum),
        "total_cost_usd": str(cost_sum),
        "provider": provider,
        "model": model,
        "stop_reason": stop_reason,
    }
    # OpenRouter reconciliation hooks — present only on OpenRouter-routed runs.
    if response_ids:
        metadata["openrouter_generation_ids"] = ",".join(response_ids)
        metadata["omp_assistant_turns"] = str(assistant_turns)
        metadata["omp_cost_sum_all_turns"] = str(cost_sum)
    if upstreams:
        metadata["upstream_provider"] = ",".join(upstreams)
    return total_tokens_sum, metadata


# Gemini API pricing, USD per 1M tokens (input, output), base context tier.
# The Gemini CLI reports token counts but NOT a dollar cost, so retort computes
# it from these. Verify/adjust against current Google pricing before trusting
# the cost column — these are the published base-tier rates, not tiered by
# context length or cached-token discounts.
GEMINI_PRICING: dict[str, tuple[float, float]] = {
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}


def _parse_opencode_usage(stdout_text: str) -> tuple[int, dict[str, str]]:
    """Parse opencode's ``--format json`` event stream.

    opencode emits newline-delimited JSON events; each assistant step ends with a
    ``step_finish`` event whose ``part`` carries that step's ``cost`` (USD) and
    ``tokens`` ({total, input, output, reasoning, cache:{read,write}}). Per-run
    usage is the **sum across steps** (like omp sums per-turn). opencode reports its
    own dollar cost, so — unlike omp — no ``/generation`` reconcile is needed; it
    also does not surface an OpenRouter generation id, so none is recorded.
    """
    input_sum = output_sum = cache_read_sum = cache_write_sum = 0
    total_tokens_sum = 0
    cost_sum = 0.0
    steps = 0
    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(event, dict) or event.get("type") != "step_finish":
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            continue
        steps += 1
        cost_sum += _parse_float(str(part.get("cost", 0.0)), 0.0)
        tokens = part.get("tokens")
        if isinstance(tokens, dict):
            input_sum += int(tokens.get("input", 0) or 0)
            output_sum += int(tokens.get("output", 0) or 0)
            total_tokens_sum += int(tokens.get("total", 0) or 0)
            cache = tokens.get("cache")
            if isinstance(cache, dict):
                cache_read_sum += int(cache.get("read", 0) or 0)
                cache_write_sum += int(cache.get("write", 0) or 0)

    if steps == 0:
        return 0, {}

    return total_tokens_sum, {
        "input_tokens": str(input_sum),
        "output_tokens": str(output_sum),
        "cache_read_input_tokens": str(cache_read_sum),
        "cache_creation_input_tokens": str(cache_write_sum),
        "total_cost_usd": str(cost_sum),
    }


def _find_first(data: object, keys: tuple[str, ...]) -> object:
    """Depth-first search a nested dict/list for the first of `keys` present."""
    if isinstance(data, dict):
        for k in keys:
            if k in data and not isinstance(data[k], (dict, list)):
                return data[k]
        for v in data.values():
            found = _find_first(v, keys)
            if found is not None:
                return found
    elif isinstance(data, list):
        for v in data:
            found = _find_first(v, keys)
            if found is not None:
                return found
    return None


def _parse_gemini_usage(stdout_text: str) -> tuple[int, dict[str, str]]:
    """Parse the Gemini CLI's JSON output (`--output-format json`).

    Verified against Gemini CLI 0.46, which emits one object:
        {"response": ..., "stats": {"models": {"<model>": {"tokens": {
            "input"/"prompt", "candidates", "thoughts", "cached", "total", ...}}}}}
    The model name is the stats.models KEY. Token field names are the CLI's own
    (input/candidates/cached/total/thoughts), NOT the API's *TokenCount names.
    `thoughts` (thinking tokens) bill as output, so they're folded into the
    output total for cost. The CLI reports no dollar cost, so it is derived from
    GEMINI_PRICING (0.0 if the model is unknown — the caller then falls back to
    the hardware-cost path or records no cost).
    """
    try:
        data = json.loads(stdout_text)
    except ValueError:
        return 0, {}
    if not isinstance(data, dict):
        return 0, {}

    # Locate the per-model tokens block (and the model name, which is its key).
    model = ""
    tokens: dict = {}
    models = (data.get("stats") or {}).get("models") if isinstance(data.get("stats"), dict) else None
    if isinstance(models, dict) and models:
        model = next(iter(models))
        entry = models[model]
        if isinstance(entry, dict) and isinstance(entry.get("tokens"), dict):
            tokens = entry["tokens"]

    def _tok(keys: tuple[str, ...]) -> int:
        # Prefer the located tokens block; fall back to a recursive search so a
        # future CLI schema shift (or API-style names) still yields numbers.
        src = tokens if tokens else data
        return int(_parse_float(str(_find_first(src, keys)), 0.0))

    input_tokens = _tok(("input", "prompt", "promptTokenCount", "input_tokens"))
    answer_tokens = _tok(("candidates", "candidatesTokenCount", "output_tokens", "output"))
    thoughts_tokens = _tok(("thoughts",))
    output_tokens = answer_tokens + thoughts_tokens  # thinking tokens bill as output
    cached_tokens = _tok(("cached", "cachedContentTokenCount", "cached_tokens"))
    total_field = _tok(("total", "totalTokenCount", "total_tokens"))
    total_tokens = total_field or (input_tokens + output_tokens + cached_tokens)

    if not model:
        model_val = _find_first(data, ("model", "modelVersion"))
        model = model_val if isinstance(model_val, str) else ""

    # Prefer a CLI-reported cost if one ever appears; else derive from pricing.
    cost = _parse_float(str(_find_first(data, ("total_cost_usd", "cost"))), 0.0)
    if cost == 0.0:
        rate = GEMINI_PRICING.get(model) or GEMINI_PRICING.get(MODEL_ALIASES.get(model, model))
        if rate is not None:
            cost = (input_tokens * rate[0] + output_tokens * rate[1]) / 1_000_000

    return total_tokens, {
        "input_tokens": str(input_tokens),
        "output_tokens": str(output_tokens),
        "thoughts_tokens": str(thoughts_tokens),
        "cache_read_input_tokens": str(cached_tokens),
        "cache_creation_input_tokens": "0",
        "total_cost_usd": str(cost),
        "model": model,
    }


def _clone_org_repo(env_dir: Path, repo_url: str) -> None:
    """Shallow-clone a repo into env_dir to establish org context.

    The workspace gets a .git dir with a remote pointing to the given repo,
    which causes SessionStart hooks that gate on org membership to fire.
    Only the .git metadata is kept; the cloned working tree is discarded.
    """
    clone_dir = env_dir / ".org-clone-tmp"
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", repo_url, str(clone_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning(
            "Failed to clone %s for org_context (%s), falling back to git init",
            repo_url, exc,
        )
        subprocess.run(["git", "init", "-q"], cwd=env_dir, capture_output=True)
        return
    if result.returncode != 0:
        logger.warning(
            "Failed to clone %s for org_context, falling back to git init: %s",
            repo_url, result.stderr[:200],
        )
        subprocess.run(["git", "init", "-q"], cwd=env_dir, capture_output=True)
        return

    clone_git = clone_dir / ".git"
    if clone_git.exists():
        shutil.move(str(clone_git), str(env_dir / ".git"))
    shutil.rmtree(clone_dir, ignore_errors=True)

    logger.info("Cloned %s for org_context in %s", repo_url, env_dir)


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

    __slots__ = ("env_id", "workspace", "stack", "task", "seed_fp")

    def __init__(
        self,
        env_id: str,
        workspace: Path,
        stack: StackConfig,
        task: TaskSpec,
        seed_fp: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        self.env_id = env_id
        self.workspace = workspace
        self.stack = stack
        self.task = task
        # Fingerprint of the workspace as SEEDED (task spec + support files), taken
        # before the agent runs. If it is unchanged afterwards, the agent wrote
        # nothing at all — which usually means its file tool was blocked, not that
        # the model was useless. See _TOOL_REFUSAL_RE.
        self.seed_fp = seed_fp
