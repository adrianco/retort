"""Local playpen runner — executes agents directly on the host.

No Docker required. Each run gets an isolated temp directory.
The agent CLI is invoked with the task prompt and the output
is collected for scoring.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from retort.config.schema import LocalAgentConfig, LocalInferenceCost
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
        max_turns: int = 30,
        default_model: str | None = None,
        default_thinking: str | None = None,
        local_agents: dict[str, LocalAgentConfig] | None = None,
        work_dir: Path | None = None,
        eval_model: str | None = None,
        local_inference_cost: LocalInferenceCost | None = None,
        prompts_dir: Path | None = None,
    ) -> None:
        self.timeout_minutes = timeout_minutes
        self.max_turns = max_turns
        self.default_model = default_model
        self.default_thinking = default_thinking
        self.local_agents = local_agents or {}
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="retort-local-"))
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

        try:
            cmd = self._build_agent_command(stack, task, info.workspace)
        except ValueError as exc:
            return RunArtifacts(
                output_dir=info.workspace,
                stderr=str(exc),
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

            stdout_text = result.stdout or ""
            # The usage parser must key on the SAME harness the command builder
            # ran (claude-code / omp / gemini), else total_cost_usd/tokens are
            # silently dropped while runner-measured _duration_seconds survives
            # (the exp-7/8 bug). _resolve_harness derives it from the model, so
            # there is one source of truth for both.
            token_count, metadata = _parse_agent_usage(
                self._resolve_harness(stack), stdout_text
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
            if result.returncode != 0 and _USAGE_LIMIT_RE.search(
                (result.stderr or "") + "\n" + stdout_text
            ):
                metadata["usage_limited"] = "true"

            artifacts = RunArtifacts(
                output_dir=info.workspace,
                stdout=stdout_text[-10000:],
                stderr=result.stderr[-5000:] if result.stderr else "",
                exit_code=result.returncode,
                duration_seconds=elapsed,
                token_count=token_count,
                metadata=metadata,
            )
            if self.eval_model is not None and artifacts.succeeded:
                self._post_run_evaluate(info.workspace)
            return artifacts
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
            cmd = ["opencode", "run", "--pure", "--format", "json"]
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


def _parse_agent_usage(agent: str, stdout_text: str) -> tuple[int, dict[str, str]]:
    """Parse token/cost metadata from known local-agent output formats."""
    if agent == "claude-code":
        return _parse_claude_usage(stdout_text)
    if agent == "omp":
        return _parse_omp_usage(stdout_text)
    if agent == "opencode":
        return _parse_opencode_usage(stdout_text)
    if agent == "gemini":
        return _parse_gemini_usage(stdout_text)
    return 0, {}


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
    """Parse OMP's newline-delimited JSON events."""
    usage: dict[str, int | float | dict[str, object]] = {}
    provider = ""
    model = ""
    stop_reason = ""

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

        message_usage = message.get("usage")
        if isinstance(message_usage, dict):
            usage = message_usage

    if not usage:
        return 0, {}

    input_tokens = int(usage.get("input", 0) or 0)
    output_tokens = int(usage.get("output", 0) or 0)
    cache_read = int(usage.get("cacheRead", 0) or 0)
    cache_write = int(usage.get("cacheWrite", 0) or 0)
    fallback_total = input_tokens + output_tokens + cache_read + cache_write
    total_tokens = int(usage.get("totalTokens", fallback_total) or 0)

    cost = usage.get("cost")
    total_cost = 0.0
    if isinstance(cost, dict):
        total_cost = float(cost.get("total", 0.0) or 0.0)

    return total_tokens, {
        "input_tokens": str(input_tokens),
        "output_tokens": str(output_tokens),
        "cache_read_input_tokens": str(cache_read),
        "cache_creation_input_tokens": str(cache_write),
        "total_cost_usd": str(total_cost),
        "provider": provider,
        "model": model,
        "stop_reason": stop_reason,
    }


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
