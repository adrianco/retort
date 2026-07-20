"""Retort CLI entry point."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import click

from retort import __version__
from retort.analysis.anova import run_all_responses, run_anova
from retort.analysis.residuals import check_residuals
from retort.design.factors import FactorRegistry
from retort.design.generator import DesignMatrix, generate_design

WORKSPACE_TEMPLATE = """\
# Retort workspace configuration
# See docs/configuration.md for full reference

experiment:
  name: __NAME__
  # visibility: public  -> runs/ and reports/web/ are git-tracked and safe to publish
  # visibility: private -> all artifacts stay local; nothing leaks
  # Default is "private" (fail-closed). Opt into public explicitly.
  visibility: __VISIBILITY__

factors:
  language:
    levels: [python, typescript, go]
  agent:
    levels: [claude-code, qwen-local, pi-dense]
  thinking:
    levels: [off, minimal]
  framework:
    levels: [fastapi, nextjs, stdlib]

responses:
  - code_quality
  - token_efficiency
  - build_time
  - test_coverage

tasks:
  - source: bundled://rest-api-crud

playpen:
  runner: docker
  replicates: 3
  timeout_minutes: 30
  local_agents:
    qwen-local:
      harness: omp
      model: moe
    pi-dense:
      harness: omp
      model: dense

design:
  screening_resolution: 3
  significance_threshold: 0.10

promotion:
  screening_to_trial: { p_value: 0.10 }
  trial_to_production: { posterior_confidence: 0.80 }

evaluation:
  enabled: true
  model: haiku
  min_severity_to_file: high
  issue_tracker: beads
"""


@click.group()
@click.version_option(version=__version__, prog_name="retort")
def main() -> None:
    """Retort — Platform Evolution Engine.

    Distill the best from the combinatorial mess.
    """


_GITIGNORE_COMMON = """\
# Retort — workspace-local state
retort.db
retort.db-journal
retort.db-shm
retort.db-wal

# Build output / vendored deps must never be committed, even inside runs/.
# (The archiver strips these too; this is defense-in-depth for public
# experiments where runs/ is tracked — node_modules in particular embeds
# third-party files that trip secret scanners.)
**/node_modules/
**/_build/
**/deps/
**/target/
**/__pycache__/
**/.cpcache/
**/.rebar3/
**/.elixir_ls/
**/erl_crash.dump
"""

_GITIGNORE_PRIVATE_EXTRA = """\

# Retort — visibility=private: keep all generated artifacts local
runs/
reports/
evaluation.md
findings.jsonl
TASK.md
"""

_GITIGNORE_PUBLIC_EXTRA = """\

# Retort — visibility=public: artifacts (runs/, reports/web/) are tracked
# Only ignore caches and intermediate scratch.
.retort-cache/
"""


def _gitignore_for(visibility: str) -> str:
    """Return the .gitignore body for a given visibility level."""
    extra = _GITIGNORE_PUBLIC_EXTRA if visibility == "public" else _GITIGNORE_PRIVATE_EXTRA
    return _GITIGNORE_COMMON + extra


def _live_context_tokens(
    workspace: Path, serving_log: Path | None, elapsed_s: float | None = None
) -> tuple[int | None, int | None]:
    """Context the in-flight run is CURRENTLY carrying, for the live monitor.

    Two sources, because agents differ in what they expose while running:

    * the agent's own stream (``_agent_stdout.log``) — Claude's ``stream-json``
      and omp's ``message_end`` both report each turn's usage as it happens;
    * the **serving log**, for agents that stream nothing to stdout while working
      (Hermes emits essentially no stdout until it exits, so its context would be
      invisible otherwise).

    Takes the LAST reading, not the max — this is "what is it carrying right now",
    which is what tells you a run is ballooning toward non-termination while you
    can still act on it.
    """
    import datetime as _dt
    import json as _json

    log = workspace / "_agent_stdout.log"
    if log.is_file():
        try:
            tail = log.read_bytes()[-400_000:].decode("utf-8", "replace")
        except OSError:
            tail = ""
        latest: int | None = None
        peak = 0
        for line in tail.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = _json.loads(line)
            except ValueError:
                continue
            u = (ev.get("message") or {}).get("usage") or {}
            if not u:
                continue
            if ev.get("type") == "assistant":  # claude stream-json
                latest = _turn_context(u)
            elif ev.get("type") == "message_end":  # omp
                latest = (
                    int(u.get("input", 0) or 0)
                    + int(u.get("cacheRead", 0) or 0)
                    + int(u.get("cacheWrite", 0) or 0)
                )
            else:
                continue
            peak = max(peak, latest)
        if latest:
            return latest, peak

    if serving_log and serving_log.is_file():
        try:
            with open(serving_log, "rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 400_000))
                tail = f.read().decode("utf-8", "replace")
        except OSError:
            return None, None
        # The serving log is SHARED by every run, so a naive max over the tail
        # reports the PREVIOUS cell's peak — a run 1 minute old was showing
        # "pk 114K" inherited from the rust cell before it. Restrict to lines
        # timestamped within this run's own window.
        since = None
        if elapsed_s:
            since = _dt.datetime.now() - _dt.timedelta(seconds=elapsed_s + 30)
        hits: list[int] = []
        for line in tail.splitlines():
            m = re.search(r"prompt:\s*(\d+)", line)
            if not m:
                continue
            if since is not None:
                ts = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                if ts:
                    try:
                        when = _dt.datetime.strptime(ts.group(1), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        when = None
                    if when is not None and when < since:
                        continue  # belongs to an earlier run
            hits.append(int(m.group(1)))
        if hits:
            return hits[-1], max(hits)
    return None, None


def _harness_failure(rep_dir: Path) -> str | None:
    """Was the agent PREVENTED from working in this archived run?

    Returns a description when the run shows a harness failure rather than a model
    failure, else None.

    The disqualifying signature is **the agent produced no source files** — a model
    that merely *can't* do the task still writes something, so writing nothing points
    at the harness (a blocked/mis-pathed file tool, or a serving layer that never
    returns tool calls). That scores a zero indistinguishable from incapability,
    which is how a harness bug once masqueraded as a language "capability wall".

    A tool **refusal** in the log is corroborating evidence, not sufficient on its
    own: a resilient model routes around a blocked ``write_file`` via the shell and
    still ships working code. Refusals are therefore only reported alongside a run
    that produced nothing.
    """
    from retort.playpen.local_runner import _TOOL_REFUSAL_RE

    _SKIP = {
        "TASK.md", "stack.json", "REQUIREMENTS.json", "_meta.json", "scores.json",
        "evaluation.md", "assessment.json", "findings.jsonl", "FEEDBACK.md",
        "_agent_stdout.log", "_agent_stderr.log", "README.md", "prompts.txt",
    }
    produced = [
        p for p in rep_dir.rglob("*")
        if p.is_file() and p.name not in _SKIP
        and not p.name.startswith(".")
        and "summary" not in p.parts and "data" not in p.parts
    ]
    if produced:
        return None  # it wrote code — judge it on the code, not the harness

    why = (
        "agent wrote NO source files — a model that cannot do the task still writes "
        "something. Suspect the harness before the model."
    )
    log = rep_dir / "_agent_stdout.log"
    if log.is_file():
        try:
            m = _TOOL_REFUSAL_RE.search(log.read_text(errors="replace"))
        except OSError:
            m = None
        if m:
            why += (
                f" Its file tool was REFUSED: {m.group(0).strip()[:80]!r} — check "
                "playpen_root (must not sit under the system temp dir)."
            )
    return why


def _ordered_runs(run_configs, reps, reload_key_fn=None):
    """Yield ``(rep, run_idx, run_config)`` in execution order.

    ``run_idx`` is always the cell's index in the design (stable labels/sharding).

    - **No reload key** (default): plain replicate-major — one full pass over
      every cell per replicate. Interrupted/sharded runs get complete factor
      coverage first at lower replication.
    - **Reload key set**: group all runs sharing a key (the reload-triggering
      ``stack`` factor) contiguously so the serving stack is (re)loaded once per
      group, keeping replicate-major *within* each group. Group order follows
      each key's first appearance in the design (so a stack-sorted design is
      honoured). Turns N_stacks × reps reloads into N_stacks.
    """
    indexed = list(enumerate(run_configs))
    if reload_key_fn is None:
        for rep in range(1, reps + 1):
            for run_idx, run_config in indexed:
                yield rep, run_idx, run_config
        return
    groups: dict = {}
    for run_idx, run_config in indexed:
        groups.setdefault(reload_key_fn(run_config), []).append((run_idx, run_config))
    for members in groups.values():
        for rep in range(1, reps + 1):
            for run_idx, run_config in members:
                yield rep, run_idx, run_config




def _init_database(db_path: Path) -> None:
    """Create and initialize the SQLite database with all tables."""
    from retort.storage.database import create_tables, get_engine

    engine = get_engine(db_path)
    create_tables(engine)
    engine.dispose()


# Paths whose contents are sensitive in private mode (must be ignored).
_PRIVATE_SENSITIVE_PATHS = (
    "runs",
    "reports",
    "evaluation.md",
    "findings.jsonl",
    "TASK.md",
)




@main.group()
def design() -> None:
    """Design matrix generation commands."""




def _load_factors(config_path: str | None) -> FactorRegistry:
    """Load factors from a YAML config file or JSON stdin."""
    if config_path is not None:
        return _load_from_yaml(config_path)
    else:
        return _load_from_stdin()


def _load_from_yaml(path: str) -> FactorRegistry:
    """Load factors from a workspace YAML file."""
    try:
        import yaml
    except ImportError:
        click.echo(
            "Error: pyyaml required for --config. Install with: pip install pyyaml",
            err=True,
        )
        sys.exit(1)

    with open(path) as f:
        data = yaml.safe_load(f)

    factors_spec = data.get("factors", {})
    if not factors_spec:
        click.echo(f"Error: no 'factors' key found in {path}", err=True)
        sys.exit(1)

    registry = FactorRegistry()
    for name, spec in factors_spec.items():
        levels = spec if isinstance(spec, list) else spec.get("levels", [])
        registry.add(name, levels)
    return registry


def _load_from_stdin() -> FactorRegistry:
    """Load factors from JSON on stdin."""
    if sys.stdin.isatty():
        click.echo(
            "Error: no --config provided and stdin is a TTY. "
            "Pipe JSON factor spec or use --config.",
            err=True,
        )
        sys.exit(1)

    data = json.load(sys.stdin)
    return FactorRegistry.from_dict(data)


@main.command("run")
@click.option(
    "--phase",
    type=click.Choice(["screening", "characterization"]),
    required=True,
    help="Experiment phase to execute.",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="Path to workspace YAML config.",
)
@click.option(
    "--task",
    "task_source",
    type=str,
    default=None,
    help="Task source URI (e.g., bundled://rest-api-crud). Defaults to first task in config.",
)
@click.option(
    "--replicates",
    type=int,
    default=None,
    help="Override number of replicates per design point.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be run without executing.",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Skip cells already completed in the workspace database. Use to continue an interrupted experiment.",
)
@click.option(
    "--retry-failed",
    is_flag=True,
    help="With --resume, also re-run `failed` DATA-POINT cells (agent completed "
         "but fell short of a gate) to re-measure them. Note: `crashed` cells "
         "(agent never completed) are ALWAYS re-run on --resume regardless.",
)
@click.option(
    "--shard",
    type=str,
    default=None,
    help=(
        "Run only a slice of the design: 'INDEX/TOTAL' (e.g. '0/4' takes the "
        "1st of 4 shards). Each (run, replicate) pair is hashed deterministically "
        "to a shard. Combine with --resume on a shared retort.db so multiple "
        "polecats can run in parallel without colliding."
    ),
)
@click.option(
    "--design",
    "design_csv",
    type=click.Path(exists=True),
    default=None,
    help=(
        "Path to a CSV design matrix produced by `retort design generate -o`. "
        "When provided, skips auto-generation and runs exactly the cells listed "
        "in the file. Use this to run a manually-trimmed fractional design. "
        "Overrides the workspace design.fraction setting."
    ),
)
@click.option(
    "--install-toolchains/--no-install-toolchains",
    "install_toolchains",
    default=None,
    help=(
        "Override playpen.auto_install_toolchains: install (or skip installing) "
        "the build/test toolchains the language factor needs (go, cargo, dotnet, "
        "…) before running. Defaults to the workspace config."
    ),
)
@click.option(
    "--repair-from",
    type=click.Path(exists=True),
    default=None,
    help=(
        "SELF-REPAIR mode. Path to a base experiment dir (or its retort.db). For "
        "each (language, replicate) cell, seed the playpen with that cell's prior "
        "attempt from the base experiment, drop in a FEEDBACK.md (requirement "
        "checklist + the prior evaluation verdict), and let the agent fix it — "
        "instead of building from scratch. Cells whose prior attempt already "
        "passed are skipped. Use a `prompt: [repair]` factor with a "
        "prompts/repair.md that tells the agent to read FEEDBACK.md and repair the "
        "existing code. Produces a normal retort.db, scored/gated like any run."
    ),
)
@click.option(
    "--no-second-chance",
    is_flag=True,
    default=False,
    help=(
        "Disable the DEFAULT self-repair second chance. By default, when a cell "
        "fails the gate (agent completed but fell short), it gets ONE repair "
        "attempt — re-seeded with its own code + FEEDBACK.md — before being "
        "recorded; a run that only passes on the second try is a `_second_try` run "
        "counted at HALF credit toward pass-proportion. Use this to turn that off "
        "(e.g. to avoid doubling paid-model cost on failures). Crashes are never "
        "second-chanced (nothing to repair); they retry via --resume."
    ),
)
def run_experiments(
    phase: str,
    config: str,
    task_source: str | None,
    replicates: int | None,
    dry_run: bool,
    resume: bool,
    retry_failed: bool,
    shard: str | None,
    design_csv: str | None,
    install_toolchains: bool | None,
    repair_from: str | None,
    no_second_chance: bool,
) -> None:
    """Execute experiment runs for a design matrix.

    Generates the design, provisions playpens, executes each run,
    scores the results, and stores everything in the workspace database.
    """
    import yaml as _yaml

    from retort.config.loader import load_workspace
    from retort.playpen.docker_runner import DockerRunner
    from retort.playpen.local_runner import LocalRunner
    from retort.playpen.runner import StackConfig, TaskSpec
    from retort.playpen.task_loader import load_task, task_requirements_path
    from retort.scoring.collector import ScoreCollector
    from retort.storage.database import create_tables, get_engine, get_session

    # Load workspace config
    workspace_config = load_workspace(config)

    # Build factor registry
    registry = FactorRegistry()
    for name, factor in workspace_config.factors.items():
        registry.add(name, factor.levels)

    if len(registry) < 2:
        raise click.ClickException("Need at least 2 factors for experiment runs.")

    # Languages whose build/test toolchain the run will need (for the preflight).
    _lang_factor = workspace_config.factors.get("language") or workspace_config.factors.get("languages")
    languages = list(_lang_factor.levels) if _lang_factor else []
    do_install_toolchains = (
        workspace_config.playpen.auto_install_toolchains
        if install_toolchains is None
        else install_toolchains
    )

    if retry_failed and not resume:
        raise click.ClickException("--retry-failed requires --resume.")

    shard_index, shard_total = _parse_shard(shard)

    # Generate (or load) design matrix
    if design_csv is not None:
        design = DesignMatrix.from_csv(design_csv, phase)
        click.echo(f"Design matrix: {design.num_runs} runs (loaded from {design_csv})")
    else:
        fraction = workspace_config.design.fraction
        design = generate_design(registry, phase, fraction=fraction)
        if fraction is not None and fraction < 1.0:
            full_n = design.full_factorial_size or design.num_runs
            click.echo(
                f"Design matrix: {design.num_runs}/{full_n} cells "
                f"({fraction:.0%} fraction, {phase})"
            )
        else:
            click.echo(f"Design matrix: {design.num_runs} runs ({phase})")

    # Resolve task
    if task_source is None:
        task_source = workspace_config.tasks[0].source
    task = load_task(task_source)
    click.echo(f"Task: {task.name}")

    # Determine replicates
    reps = replicates or workspace_config.playpen.replicates
    total_runs = design.num_runs * reps
    click.echo(f"Replicates: {reps} ({total_runs} total runs)")

    # Initialize database (needed early so --resume can inspect existing runs
    # before dry-run reports what would actually execute).
    config_dir = Path(config).resolve().parent
    db_path = config_dir / "retort.db"
    engine = get_engine(db_path)
    create_tables(engine)

    # Archive root: per-run workspaces are copied here so artifacts survive
    # /tmp cleanup and process kills.
    archive_root = config_dir / "runs"
    archive_root.mkdir(exist_ok=True)

    # Guarantee a pinned requirement checklist for the spec gate. Without it the
    # evaluate-run skill silently falls back to ad-hoc TASK.md extraction, so
    # requirement_coverage uses a varying denominator and isn't comparable
    # across runs/experiments. Copy the task's canonical REQUIREMENTS.json, or
    # generate one from the prompt (and warn) so every experiment has one.
    _ensure_requirements_json(config_dir, task, task_source, task_requirements_path)

    # Persist the design matrix so downstream `retort report effects --matrix-id`
    # can join run results back to factor levels. Idempotent on resume — looks
    # up by (matrix name + phase) and reuses if found.
    design_session = get_session(engine)
    try:
        matrix_id, run_config_to_row_id = _persist_design_matrix(
            design_session, registry, design, phase, workspace_config,
        )
        design_session.commit()
    except Exception:
        design_session.rollback()
        raise
    finally:
        design_session.close()

    # Build set of (run_config_json, replicate) pairs to skip when resuming.
    skip_keys: set[tuple[str, int]] = set()
    if resume:
        from retort.storage.models import ExperimentRun, RunStatus

        existing_session = get_session(engine)
        try:
            # Skip cells that already hold a DATA POINT: `completed` (passed) and
            # `failed` (ran to completion but fell short of a gate — a genuine
            # measurement). `crashed` rows are never skipped, so a cell whose
            # agent never completed is always re-attempted on --resume.
            # --retry-failed additionally re-runs the `failed` data points (to
            # re-measure genuine failures, e.g. after a fix or for more samples).
            statuses = [RunStatus.completed]
            if not retry_failed:
                statuses.append(RunStatus.failed)
            for row in existing_session.query(
                ExperimentRun.run_config_json, ExperimentRun.replicate
            ).filter(ExperimentRun.status.in_(statuses)).all():
                # Normalize JSON key ordering so config dicts match regardless
                # of how they were serialized originally.
                try:
                    normalized = json.dumps(json.loads(row[0]), sort_keys=True)
                except (TypeError, ValueError):
                    normalized = row[0]
                skip_keys.add((normalized, row[1]))
        finally:
            existing_session.close()
        if skip_keys:
            click.echo(f"Resume: {len(skip_keys)} run(s) already recorded — will skip.")

    if dry_run:
        click.echo("\n[dry-run] Design matrix:")
        if shard_total > 1:
            click.echo(f"Shard: {shard_index}/{shard_total} — only owned cells run.")
        will_run = 0
        will_skip = 0
        will_other_shard = 0
        for rep in range(1, reps + 1):
            for i, run_config in enumerate(design.run_configs()):
                config_key = json.dumps(run_config, sort_keys=True)
                if not _shard_owns(config_key, rep, shard_index, shard_total):
                    will_other_shard += 1
                    click.echo(f"  [shrd] Run {i+1} rep {rep}: {run_config}")
                    continue
                marker = "skip" if (config_key, rep) in skip_keys else "RUN "
                if marker == "skip":
                    will_skip += 1
                else:
                    will_run += 1
                click.echo(f"  [{marker}] Run {i+1} rep {rep}: {run_config}")
        msg = f"\nWould execute {will_run} runs ({will_skip} skipped"
        if shard_total > 1:
            msg += f", {will_other_shard} owned by other shards"
        msg += "). Exiting."
        click.echo(msg)
        if languages and workspace_config.playpen.runner == "local":
            from retort.playpen.toolchains import ensure_toolchains, format_report

            statuses = ensure_toolchains(languages, install=False)
            click.echo("\n[dry-run] Toolchain preflight (no install):")
            for line in format_report(statuses, installed_action=False):
                click.echo(line)
        engine.dispose()
        return

    # Disk-space preflight. A run writes a fresh playpen per cell (a full app +
    # its build tree — node_modules/target can be GB each) and the local serving
    # layer keeps a paged-SSD KV cache that grows to its configured cap. On a
    # near-full disk the agent's writes fail and the run scores false zeros
    # (indistinguishable from an incapable model), or oMLX degrades. Fail fast.
    import shutil as _shutil
    _playpen_root = os.path.expanduser(
        str(getattr(workspace_config.playpen, "playpen_root", "") or "~/.retort/work")
    )
    _probe = _playpen_root if os.path.isdir(_playpen_root) else os.path.expanduser("~")
    _free_gb = _shutil.disk_usage(_probe).free / 2**30
    if _free_gb < 15:
        raise click.ClickException(
            f"Low disk: only {_free_gb:.0f} GB free at {_probe}. An experiment writes "
            f"large per-cell playpens and a growing serving cache; a near-full disk scores "
            f"false zeros. Free space first (clear ~/.cache/omlx-ssd, ~/.retort/work, and "
            f"thin local snapshots: `tmutil thinlocalsnapshots / 100000000000 4`), then re-run."
        )
    if _free_gb < 40:
        click.echo(
            f"⚠️  Disk preflight: {_free_gb:.0f} GB free at {_probe} — low; a long run may "
            f"fill it (the oMLX paged-SSD cache grows to its cap). Consider clearing caches.",
            err=True,
        )
    else:
        click.echo(f"Disk preflight: {_free_gb:.0f} GB free — ok.")

    # Toolchain preflight — ensure the build/test toolchain each language factor
    # level needs is present, installing missing ones when enabled. Best-effort:
    # failures warn but never abort (scorers already skip on a missing tool), so
    # a run is never worse off than without this step.
    if languages and workspace_config.playpen.runner == "local":
        from retort.playpen.toolchains import ensure_toolchains, format_report

        if do_install_toolchains:
            click.echo("Toolchain preflight (installing missing toolchains):")
        else:
            click.echo("Toolchain preflight (check only — auto-install disabled):")
        statuses = ensure_toolchains(languages, install=do_install_toolchains)
        for line in format_report(statuses, installed_action=do_install_toolchains):
            click.echo(line)

    # Set up runner and scorer
    runner_type = workspace_config.playpen.runner
    if runner_type == "local":
        prompts_dir = config_dir / "prompts"
        stack_manager = None
        if workspace_config.playpen.stack_presets:
            from retort.playpen.stack_reload import OmlxStackManager
            registry_path = config_dir / workspace_config.playpen.stack_presets
            stack_manager = OmlxStackManager(registry_path)
        runner = LocalRunner(
            timeout_minutes=workspace_config.playpen.timeout_minutes,
            stall_minutes=workspace_config.playpen.stall_minutes,
            max_turns=workspace_config.playpen.max_turns,
            default_model=workspace_config.playpen.model,
            default_thinking=workspace_config.playpen.thinking,
            local_agents=workspace_config.playpen.local_agents,
            local_inference_cost=workspace_config.playpen.local_inference_cost,
            prompts_dir=prompts_dir if prompts_dir.is_dir() else None,
            stack_manager=stack_manager,
        )
    elif runner_type == "metaharness":
        from retort.playpen.metaharness_runner import MetaHarnessRunner
        runner = MetaHarnessRunner(
            timeout_minutes=workspace_config.playpen.timeout_minutes,
            max_turns=workspace_config.playpen.max_turns,
            default_model=workspace_config.playpen.model,
        )
    else:
        runner = DockerRunner(timeout_minutes=workspace_config.playpen.timeout_minutes)
    metric_names = [r.name for r in workspace_config.responses]
    collector = ScoreCollector(metrics=metric_names)

    # Fail fast: validate agent types before any runs start.
    if runner_type == "local":
        _supported_agents = {"claude-code", *workspace_config.playpen.local_agents}
        for _rc in design.run_configs():
            _agent = _rc.get("agent", "claude-code") or "claude-code"
            if _agent not in _supported_agents and _agent != "unknown":
                raise click.ClickException(
                    f"Agent {_agent!r} is not implemented. "
                    f"Only {sorted(_supported_agents)} are supported in this release. "
                    f"Remove or replace unsupported agent levels in your workspace config."
                )

    # Capture the FULL stack this experiment runs on — versions, model revisions,
    # sampling params, agent config, harness settings — and write it beside the
    # data. A pass-proportion is meaningless without the stack it was measured on:
    # every wrong conclusion so far (temp=1.0 sampling, the /var playpen the agent
    # couldn't write to, the omp-vs-hermes agent swap) came from a stack variable
    # nobody recorded. The manifest is a reported result, not a debug aid.
    try:
        from retort.reporting import provenance as _prov
        _presets = None
        if workspace_config.playpen.stack_presets:
            import yaml as _yaml
            _presets = (_yaml.safe_load(
                (config_dir / workspace_config.playpen.stack_presets).read_text()
            ) or {}).get("presets")
        _manifest = _prov.capture(
            repo=Path(__file__).resolve().parents[2],
            config_dir=config_dir,
            playpen_config=workspace_config.playpen,
            stack_presets=_presets,
            model_ids=[
                str(rc.get("model")) for rc in design.run_configs() if rc.get("model")
            ],
        )
        _path = _prov.write(_manifest, config_dir)
        click.echo("\nStack provenance (recorded to %s):" % _path.name)
        for _line in _prov.summarize(_manifest):
            click.echo(_line)
    except Exception as _exc:  # noqa: BLE001 — provenance must never block a run
        click.echo(f"  (provenance capture failed: {_exc})", err=True)

    click.echo(f"\nStarting experiment runs...")

    completed = 0
    failed = 0
    crashed = 0
    skipped = 0
    accumulated_cost = 0.0
    accumulated_tokens = 0
    # Harness self-check: consecutive runs where the agent wrote no files at all.
    # A blocked file tool scores false zeros that mimic a model incapability, so a
    # streak of them stops the experiment instead of poisoning the data.
    no_write_streak = 0
    no_write_abort_after = workspace_config.playpen.no_write_abort_after
    cost_limit = workspace_config.playpen.cost_limit_usd
    token_limit = workspace_config.playpen.token_limit

    # Reload-minimising order. When a cell change forces an expensive serving-
    # stack reload (a `stack` factor driving stack_presets — sampling params or,
    # later, different model weights), group all runs sharing a stack contiguously
    # so each stack loads exactly ONCE, and keep replicate-major *within* the
    # group. Without a reload cost, fall back to plain replicate-major (full
    # coverage first at lower replication). See _ordered_runs.
    _reload_key_fn = None
    if runner_type == "local" and workspace_config.playpen.stack_presets:
        _reload_key_fn = lambda rc: rc.get("stack")  # noqa: E731

    session = get_session(engine)
    try:
        # Replicate-major order: complete one full pass over every design cell
        # (full factor coverage) before starting the next replicate. So an
        # interrupted, resumed, or incrementally-sharded run yields complete
        # coverage at lower replication rather than full replication of a few
        # cells. Replicate is the outer loop; the design cells are the inner.
        # (When a reload key is set, runs are grouped by stack first — see above.)
        for rep, run_idx, run_config in _ordered_runs(
            design.run_configs(), reps, _reload_key_fn
        ):
                stack = StackConfig.from_run_config(run_config)
                config_key = json.dumps(run_config, sort_keys=True)
                label = f"[{run_idx+1}/{design.num_runs} rep {rep}/{reps}]"
                if not _shard_owns(config_key, rep, shard_index, shard_total):
                    # Belongs to a different shard. Don't even mark it skipped —
                    # another polecat will pick it up.
                    continue
                if (config_key, rep) in skip_keys:
                    click.echo(f"  {label} {stack.language}/{stack.framework}/{stack.agent} — skip (resume)")
                    skipped += 1
                    continue
                # Self-repair mode: only run cells whose prior attempt failed and
                # left code to fix; skip the rest (nothing to repair).
                repair_prior = None
                if repair_from is not None:
                    repair_prior = _repair_prior_run(repair_from, stack.language, rep)
                    if repair_prior is None:
                        click.echo(f"  {label} {stack.language}/{stack.framework}/{stack.agent} — skip (no repairable prior)")
                        skipped += 1
                        continue
                click.echo(f"  {label} {stack.language}/{stack.framework}/{stack.agent}", nl=False)

                estimated_timeout = _estimate_run_timeout(
                    session, run_config, workspace_config.playpen.timeout_minutes
                )
                if estimated_timeout != runner.timeout_minutes:
                    click.echo(f" [timeout={estimated_timeout}m]", nl=False)
                runner.timeout_minutes = estimated_timeout

                env_id = runner.provision(stack, task)
                if repair_prior is not None:
                    _seed_repair_workspace(
                        runner.work_dir / env_id, repair_prior,
                        config_dir / "REQUIREMENTS.json",
                    )
                try:
                    artifacts = runner.execute(env_id, stack, task)
                    if artifacts.usage_limited:
                        # Not a model failure — the agent never got to do the
                        # work. Leave this cell UNRECORDED so --resume re-runs it,
                        # and stop the run so the remaining cells aren't burned
                        # against the same exhausted limit. (teardown via finally)
                        click.echo(" — usage limit (not recorded)", err=True)
                        raise _UsageLimitStop()

                    # Harness self-check — STOP rather than record false zeros.
                    # A blocked file-write tool and a model that simply can't do
                    # the task are indistinguishable in the metrics (both produce
                    # no code, requirement_coverage 0). Recording those as model
                    # results is how a harness bug masquerades as a "capability
                    # wall" — it cost us ~10 experiments before it was caught.
                    #
                    # BUT only abort when the refusal actually blocked the work:
                    # the workspace must be byte-for-byte as seeded (wrote_nothing).
                    # Some agents (Hermes) emit a benign per-turn advisory —
                    # "File-mutation verifier: N file(s) were NOT modified this turn"
                    # — on any turn that happens not to write a file; that matches
                    # the refusal regex yet the run still produces a complete, passing
                    # implementation. Aborting on it discarded good 80B runs (exp-30).
                    _refusal = artifacts.metadata.get("tool_refusal")
                    if _refusal and artifacts.metadata.get("wrote_nothing") == "true":
                        raise click.ClickException(
                            f"HARNESS BROKEN — the agent's file tool was refused:\n"
                            f"    {_refusal}\n\n"
                            f"  Workspace: {artifacts.output_dir}\n"
                            f"  The agent could not write into its own playpen, so this "
                            f"run (and any like it) would score a FALSE ZERO that looks "
                            f"identical to a model that can't do the task.\n"
                            f"  Stopping so the harness can be fixed rather than "
                            f"recording garbage. Nothing was written for this cell; "
                            f"--resume will re-run it once fixed.\n"
                            f"  Known cause: playpens under a path the agent considers "
                            f"system-owned (e.g. macOS /var/folders). Playpens now live "
                            f"under ~/.retort/work."
                        )
                    if artifacts.metadata.get("wrote_nothing") == "true":
                        no_write_streak += 1
                        if (no_write_abort_after
                                and no_write_streak >= no_write_abort_after):
                            raise click.ClickException(
                                f"HARNESS SUSPECTED — {no_write_streak} consecutive runs "
                                f"wrote NO files at all.\n\n"
                                f"  Workspace: {artifacts.output_dir}\n"
                                f"  A model that can't do the task still *writes something*. "
                                f"Writing nothing, repeatedly, points at the harness (a "
                                f"blocked/mis-pathed file tool, a bad workspace, a serving "
                                f"layer that never returns tool calls) — not the model.\n"
                                f"  Stopping so it can be diagnosed rather than recording "
                                f"false zeros. Check the agent's stdout in the workspace "
                                f"(_agent_stdout.log). Set playpen.no_write_abort_after: 0 "
                                f"to disable this check."
                            )
                    else:
                        no_write_streak = 0

                    scores = collector.collect(artifacts, stack)

                    # Conformance gate: an agent-succeeded run whose tests never
                    # executed is not a valid success — record it as failed.
                    tests_failed = _tests_did_not_run(scores)

                    # Archive before teardown wipes the workspace. The spec gate
                    # below reads the archived code; the eval reads the just-
                    # computed mechanical scores from scores.json (the run isn't
                    # in the DB yet), so drop those alongside the code.
                    archived = _archive_run_workspace(
                        archive_root, run_config, rep, artifacts,
                        visibility=workspace_config.experiment.visibility,
                    )
                    if archived is not None:
                        try:
                            (archived / "scores.json").write_text(json.dumps(scores.to_dict()))
                        except OSError:
                            pass

                    # Spec-conformance gate: a second-opinion eval (judge =
                    # evaluation.model) must confirm the code implements the
                    # task's requirements. Runs only when evaluation is enabled
                    # and the run is otherwise valid (agent succeeded + tests
                    # ran). The run fails only if two independent evals both
                    # fall short of full requirement coverage.
                    spec_failed = False
                    req_cov = None
                    if (workspace_config.evaluation.enabled
                            and artifacts.succeeded and not tests_failed
                            and archived is not None):
                        try:
                            spec_verdict, req_cov = _spec_conformance_passes(
                                archived,
                                workspace_config.evaluation,
                                workspace_config.experiment.visibility,
                            )
                            # Only an explicit False (two real short opinions)
                            # fails the run; None (eval couldn't run) does not.
                            spec_failed = spec_verdict is False
                        except Exception as exc:
                            click.echo(f"  (spec gate crashed: {exc}; not gating)", err=True)

                    run_ok = artifacts.succeeded and not tests_failed and not spec_failed
                    # A run that never completed (agent crash / timeout kill /
                    # server unreachable) is not a data point — it is retried.
                    # A completed-but-gate-failed run IS a data point (progress).
                    run_crashed = not artifacts.succeeded

                    # DEFAULT self-repair: a gate-FAILURE (agent completed but fell
                    # short) gets ONE repair attempt, re-seeded with its own code +
                    # FEEDBACK.md. A crash has no artifact to repair; a --repair-from
                    # cell is already a repair. A second-try PASS is recorded like
                    # any run but flagged `_second_try` → HALF credit in analysis.
                    second_try = False
                    if (not run_ok and not run_crashed and not no_second_chance
                            and repair_from is None and archived is not None):
                        click.echo(" — 2nd chance…", nl=False)
                        # count the first attempt's spend toward the run totals
                        if artifacts.metadata:
                            try:
                                accumulated_cost += float(artifacts.metadata.get("total_cost_usd") or 0)
                            except (TypeError, ValueError):
                                pass
                        accumulated_tokens += artifacts.token_count or 0
                        prior = {"dir": archived, "status": "failed", "req_cov": req_cov}
                        env_id2 = runner.provision(stack, task)
                        try:
                            _seed_repair_workspace(
                                runner.work_dir / env_id2, prior,
                                config_dir / "REQUIREMENTS.json",
                            )
                            a2 = runner.execute(env_id2, stack, task)
                            if not a2.usage_limited:
                                s2 = collector.collect(a2, stack)
                                tf2 = _tests_did_not_run(s2)
                                arch2 = _archive_run_workspace(
                                    archive_root, run_config, rep, a2,
                                    visibility=workspace_config.experiment.visibility,
                                )
                                if arch2 is not None:
                                    try:
                                        (arch2 / "scores.json").write_text(json.dumps(s2.to_dict()))
                                    except OSError:
                                        pass
                                sf2 = False
                                rc2 = None
                                if (workspace_config.evaluation.enabled and a2.succeeded
                                        and not tf2 and arch2 is not None):
                                    try:
                                        v2, rc2 = _spec_conformance_passes(
                                            arch2, workspace_config.evaluation,
                                            workspace_config.experiment.visibility)
                                        sf2 = v2 is False
                                    except Exception as exc:
                                        click.echo(f"  (2nd-chance gate crashed: {exc})", err=True)
                                # adopt the second attempt as the recorded result
                                artifacts, scores = a2, s2
                                tests_failed, spec_failed, req_cov, archived = tf2, sf2, rc2, arch2
                                run_ok = a2.succeeded and not tf2 and not sf2
                                run_crashed = not a2.succeeded
                                second_try = True
                        finally:
                            runner.teardown(env_id2)

                    status = ("ok*" if (run_ok and second_try) else "ok" if run_ok
                              else "CRASH" if run_crashed else "FAIL")
                    score_str = ", ".join(
                        f"{k}={v:.2f}" for k, v in scores.to_dict().items()
                    )
                    token_str = ""
                    if artifacts.token_count > 0:
                        cost = artifacts.metadata.get("total_cost_usd", "0")
                        token_str = f" tokens={artifacts.token_count:,} cost=${float(cost):.4f}"
                    click.echo(f" — {status} ({artifacts.duration_seconds:.1f}s) [{score_str}]{token_str}")
                    if not artifacts.succeeded and artifacts.stderr:
                        click.echo(f"    error: {artifacts.stderr[:200]}", err=True)
                    elif tests_failed and artifacts.succeeded:
                        click.echo("    gate: tests did not run (test_coverage=0) — marked failed", err=True)
                    elif spec_failed:
                        click.echo(f"    gate: spec not met (requirement_coverage={req_cov} on two evals) — marked failed", err=True)

                    # Store results
                    _store_run_result(
                        session, run_config, phase, run_idx, rep,
                        artifacts, scores,
                        design_row_id=run_config_to_row_id.get(config_key),
                        conformance_failed=(tests_failed or spec_failed),
                        requirement_coverage=req_cov,
                        # a --repair-from cell is itself a repair (2nd attempt),
                        # so it too counts at half credit.
                        second_try=(second_try or repair_from is not None),
                    )
                    # Commit per-run so an interrupt loses at most one run.
                    session.commit()

                    if workspace_config.mlflow is not None:
                        from retort.mlflow_sink import log_run_to_mlflow
                        try:
                            log_run_to_mlflow(
                                workspace_config.mlflow,
                                workspace_config.experiment.name or "retort",
                                run_config, phase, run_idx, rep,
                                artifacts, scores,
                            )
                        except Exception as exc:
                            click.echo(f"  (mlflow log failed: {exc}; continuing)", err=True)

                    if run_ok:
                        completed += 1
                    elif run_crashed:
                        crashed += 1
                    else:
                        failed += 1

                    if artifacts.metadata:
                        try:
                            accumulated_cost += float(artifacts.metadata.get("total_cost_usd") or 0)
                        except (TypeError, ValueError):
                            pass
                    accumulated_tokens += artifacts.token_count or 0
                    if cost_limit is not None and accumulated_cost > cost_limit:
                        raise click.ClickException(
                            f"cost_limit_usd ${cost_limit:.2f} exceeded "
                            f"(accumulated ${accumulated_cost:.4f}) — aborting"
                        )
                    if token_limit is not None and accumulated_tokens > token_limit:
                        raise click.ClickException(
                            f"token_limit {token_limit:,} exceeded "
                            f"(accumulated {accumulated_tokens:,} tokens) — aborting"
                        )
                finally:
                    runner.teardown(env_id)
    except _UsageLimitStop:
        # Graceful stop: commit what finished, leave the limited + remaining
        # cells unrecorded. A plain `--resume` picks them up — no --retry-failed
        # needed, and no usage-limit casualty is mis-scored as a model failure.
        session.commit()
        click.echo(
            "\n⚠ Usage/rate limit reached — stopped cleanly. Completed cells are "
            "saved; the interrupted cell was NOT recorded. Resume with --resume "
            "once your limit resets.",
            err=True,
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

    summary = f"\nDone: {completed} completed, {failed} failed out of {total_runs}"
    if crashed:
        summary += f" ({crashed} crashed — retried on --resume)"
    if skipped:
        summary += f" ({skipped} skipped via resume)"
    click.echo(summary)


def _parse_shard(spec: str | None) -> tuple[int, int]:
    """Parse '--shard INDEX/TOTAL' into (index, total). None ⇒ (0, 1)."""
    if not spec:
        return (0, 1)
    if "/" not in spec:
        raise click.ClickException(
            f"--shard must be 'INDEX/TOTAL', got {spec!r} (e.g. '0/4')"
        )
    idx_str, _, total_str = spec.partition("/")
    try:
        idx = int(idx_str)
        total = int(total_str)
    except ValueError as exc:
        raise click.ClickException(f"--shard parts must be integers: {exc}") from None
    if total < 1:
        raise click.ClickException("--shard TOTAL must be ≥ 1")
    if idx < 0 or idx >= total:
        raise click.ClickException(f"--shard INDEX must be in [0, {total - 1}], got {idx}")
    return (idx, total)


def _repair_prior_run(base: str, language: str, replicate: int):
    """For --repair-from: find the base experiment's prior attempt for this
    (language, replicate). Returns ``{'dir', 'status', 'req_cov'}`` for a
    REPAIRABLE prior (it failed/crashed AND left a code archive), or ``None``
    when there is nothing to repair (no prior, no code, or it already passed).
    """
    import glob as _glob
    import sqlite3 as _sqlite

    base_path = Path(base)
    db_path = base_path if base_path.suffix == ".db" else base_path / "retort.db"
    runs_root = (base_path.parent if base_path.suffix == ".db" else base_path) / "runs"
    if not db_path.exists():
        return None
    con = _sqlite.connect(db_path)
    con.row_factory = _sqlite.Row
    status = None
    req_cov = None
    for r in con.execute("SELECT id, status, replicate, run_config_json FROM experiment_runs"):
        try:
            cfg = json.loads(r["run_config_json"])
        except (TypeError, ValueError):
            continue
        if cfg.get("language") != language or r["replicate"] != replicate:
            continue
        status = r["status"]
        row = con.execute(
            "SELECT value FROM run_results WHERE run_id=? AND metric_name='requirement_coverage'",
            (r["id"],),
        ).fetchone()
        req_cov = row[0] if row else None
        break
    con.close()
    if status is None:
        return None
    # already passed → nothing to repair
    if status == "completed" and req_cov is not None and abs(req_cov - 1.0) < 1e-9:
        return None
    # locate the archived code dir for this (language, replicate)
    matches = _glob.glob(str(runs_root / f"*language={language}*" / f"rep{replicate}"))
    prior_dir = next((Path(m) for m in matches if Path(m).is_dir()), None)
    if prior_dir is None:
        return None
    # must contain some source to seed
    has_code = any(
        not f.name.startswith("_")
        and f.name not in ("TASK.md", "stack.json", "scores.json", "assessment.json",
                            "evaluation.md", "findings.jsonl", "_meta.json", "REQUIREMENTS.json")
        for f in prior_dir.rglob("*") if f.is_file()
    )
    if not has_code:
        return None
    return {"dir": prior_dir, "status": status, "req_cov": req_cov}


def _seed_repair_workspace(env_dir: Path, prior, requirements_path: Path | None) -> None:
    """Seed a provisioned playpen with a prior attempt's code + a FEEDBACK.md so
    the agent repairs rather than rebuilds. TASK.md (written by provision) stays.
    """
    import shutil as _shutil

    skip = {"TASK.md", "stack.json", "scores.json", "assessment.json", "evaluation.md",
            "findings.jsonl", "_meta.json", ".coverage", "FEEDBACK.md", "REQUIREMENTS.json"}
    for item in prior["dir"].iterdir():
        if item.name in skip or item.name.startswith("_"):
            continue
        dst = env_dir / item.name
        try:
            if item.is_dir():
                _shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                _shutil.copy2(item, dst)
        except OSError:
            pass
    # Build FEEDBACK.md: the requirement checklist + the prior evaluation verdict.
    lines = [
        "# Evaluation feedback on your previous attempt",
        "",
        "A previous attempt is already in this directory. It did NOT pass an "
        "independent evaluation. Fix it.",
        "",
        "## Requirements that must ALL be met",
    ]
    reqs = {}
    if requirements_path and Path(requirements_path).exists():
        try:
            reqs = json.loads(Path(requirements_path).read_text())
        except (OSError, ValueError):
            reqs = {}
    for rq in reqs.get("requirements", []):
        lines.append(f"- [{rq.get('id','')}] {rq.get('requirement','')}"
                     + (f"  (verify: {rq['how_to_verify']})" if rq.get("how_to_verify") else ""))
    lines += ["", "## What went wrong last time"]
    if prior["status"] == "crashed":
        lines.append("- The previous run never finished a testable build. Make sure the "
                     "project builds and the tests actually run and terminate.")
    else:
        rc = f", requirement_coverage {prior['req_cov']:.2f}" if prior["req_cov"] is not None else ""
        lines.append(f"- The build/tests did not fully pass (status: {prior['status']}{rc}).")
    findings_file = prior["dir"] / "assessment.json"
    if findings_file.exists():
        try:
            for f in json.loads(findings_file.read_text()).get("top_findings", [])[:10]:
                lines.append(f"- {f.get('title') or f.get('description') or f}")
        except (OSError, ValueError):
            pass
    lines += ["", "Fix the existing code so every requirement above is met and the tests run and pass."]
    (env_dir / "FEEDBACK.md").write_text("\n".join(lines))
    if requirements_path and Path(requirements_path).exists():
        try:
            _shutil.copy2(requirements_path, env_dir / "REQUIREMENTS.json")
        except OSError:
            pass
    # Prompt-agnostic repair instruction: prepend a banner to TASK.md so the
    # agent repairs the seeded code and reads FEEDBACK.md whatever prompt the
    # experiment uses (needed for the default in-line second chance, which keeps
    # the experiment's own prompt).
    task_md = env_dir / "TASK.md"
    banner = (
        "# REPAIR TASK\n\nA previous attempt at the task below is ALREADY in this "
        "directory but did NOT pass an independent evaluation. Read `FEEDBACK.md` "
        "for exactly what was wrong, then FIX the existing code so it builds, all "
        "tests run and pass, and every requirement is met. Do NOT start over.\n\n"
        "---\n\n"
    )
    try:
        orig = task_md.read_text() if task_md.exists() else ""
        task_md.write_text(banner + orig)
    except OSError:
        pass


def _estimate_run_timeout(session, run_config: dict, fallback_minutes: int) -> int:
    """Estimate a per-run timeout from historical _duration_seconds in the DB.

    Looks at completed runs with the same factor config first; if none exist,
    falls back to completed runs sharing the same language (the dominant cost
    driver). The adaptive estimate ``ceil(max_observed * 1.5 / 60)`` only ever
    *extends* the configured budget: the result is clamped to
    ``[fallback_minutes, fallback_minutes * 3]``. It never returns less than the
    configured ``timeout_minutes`` — otherwise an early run (before any slow
    run exists to raise the ceiling) could be killed below the user's budget,
    producing a false all-zeros timeout. Returns ``fallback_minutes`` when no
    history is available.
    """
    import math

    from retort.storage.models import ExperimentRun, RunResult, RunStatus

    config_json = json.dumps(run_config, sort_keys=True)

    all_completed = (
        session.query(ExperimentRun.run_config_json, RunResult.value)
        .join(RunResult, RunResult.run_id == ExperimentRun.id)
        .filter(
            ExperimentRun.status == RunStatus.completed,
            RunResult.metric_name == "_duration_seconds",
        )
        .all()
    )

    exact = [v for cfg, v in all_completed if cfg == config_json]
    if exact:
        durations = exact
    else:
        language = run_config.get("language", "")
        durations = [
            v for cfg, v in all_completed
            if language and json.loads(cfg).get("language") == language
        ]

    if not durations:
        return fallback_minutes

    estimated = math.ceil(max(durations) * 1.5 / 60)
    # Adaptive timeout only extends: never below the configured budget, never
    # above 3x it. Clamping the lower bound to fallback_minutes (rather than 5)
    # prevents early, history-poor runs from being killed under budget.
    return max(fallback_minutes, min(estimated, fallback_minutes * 3))


def _shard_owns(config_key: str, rep: int, shard_index: int, shard_total: int) -> bool:
    """Deterministic per-(cell, replicate) sharding.

    A simple modulo over a hash of the (config, replicate) string. Stable
    across runs and across processes — every shard sees the same partition
    so two polecats with --shard 0/4 and --shard 1/4 never both pick the
    same cell.
    """
    if shard_total <= 1:
        return True
    import hashlib
    digest = hashlib.sha1(f"{config_key}#{rep}".encode()).digest()
    bucket = int.from_bytes(digest[:4], "big") % shard_total
    return bucket == shard_index


def _generate_requirements_from_prompt(task) -> dict:
    """Derive a requirement checklist from a task's prompt as a fallback.

    Extracts bullet lines ("- …") from the prompt so requirement_coverage has
    a stable, non-zero denominator even when the task ships no pinned checklist.
    This is a best-effort stand-in for a hand-authored REQUIREMENTS.json — the
    caller warns that it should be reviewed and committed.
    """
    bullets: list[str] = []
    for raw in (getattr(task, "prompt", "") or "").splitlines():
        line = raw.strip()
        if line[:1] in {"-", "*"} and len(line) > 2:
            text = line[1:].strip()
            if text and text.lower() not in {b.lower() for b in bullets}:
                bullets.append(text)
    if not bullets:
        # No bullets — fall back to the one-line description as a single item.
        desc = (getattr(task, "description", "") or "").strip().splitlines()
        bullets = [desc[0]] if desc else ["Implements the task as described."]
    return {
        "task": getattr(task, "name", "unknown"),
        "note": (
            "AUTO-GENERATED from the task prompt because the task shipped no "
            "REQUIREMENTS.json. Review and pin this checklist for a stable, "
            "comparable requirement_coverage denominator."
        ),
        "generated": True,
        "requirements": [
            {"id": f"R{i}", "requirement": b, "how_to_verify": "Derived from the task prompt."}
            for i, b in enumerate(bullets, 1)
        ],
    }


def _ensure_requirements_json(config_dir, task, task_source, requirements_path_fn) -> None:
    """Guarantee ``<experiment>/REQUIREMENTS.json`` exists before runs grade.

    Order: respect an existing file (pinned), else copy the task's canonical
    checklist, else generate one from the prompt and warn. Never raises.
    """
    import shutil

    dest = config_dir / "REQUIREMENTS.json"
    if dest.exists():
        return
    try:
        bundled = requirements_path_fn(task_source)
    except Exception:
        bundled = None
    if bundled is not None:
        try:
            shutil.copyfile(bundled, dest)
            click.echo(f"  Requirements: copied pinned checklist from {task.name} task.")
            return
        except OSError:
            pass
    # Last resort: derive from the prompt so the denominator is at least stable.
    try:
        data = _generate_requirements_from_prompt(task)
        dest.write_text(json.dumps(data, indent=2))
        click.echo(
            f"  ⚠ Requirements: no pinned REQUIREMENTS.json for task {task.name!r} — "
            f"generated {len(data['requirements'])} from the prompt. Review "
            f"{dest} and commit it for comparable scoring.",
            err=True,
        )
    except Exception as exc:
        click.echo(f"  (could not write REQUIREMENTS.json: {exc})", err=True)


# Build output / vendored dependency directories (and crash dumps) that must
# never enter a run archive — regenerable, large, and a source of committed
# secrets (node_modules fixtures) and copy failures (dangling _build symlinks).
_ARCHIVE_NOISE = {
    "node_modules", "_build", "deps", "target", "build", "dist", "vendor",
    "__pycache__", ".gradle", ".cpcache", ".rebar3", ".elixir_ls",
    ".pytest_cache", ".mypy_cache", ".git",
}


def _ignore_archive_noise(_dir: str, names: list[str]) -> set[str]:
    """`shutil.copytree` ignore callback: skip build output and vendored deps."""
    return {n for n in names if n in _ARCHIVE_NOISE or n == "erl_crash.dump"}


class _UsageLimitStop(Exception):
    """Raised mid-run when the agent hit a usage/rate limit, to stop the run
    cleanly without recording the interrupted (or remaining) cells as failures."""


def _archive_run_workspace(
    archive_root: Path,
    run_config: dict[str, str],
    replicate: int,
    artifacts,
    visibility: str = "private",
) -> Path | None:
    """Copy a run's workspace into the archive so it survives /tmp cleanup.

    Layout: <archive_root>/<sorted-factor=value-pairs>/rep<N>[ -failed]/

    Writes ``_meta.json`` next to the copied workspace so downstream tooling
    (report web, file-run-issues) can read the experiment's visibility level
    without re-parsing workspace.yaml. Returns the archived destination path
    (or None if archival was skipped or failed).
    """
    import shutil

    src = getattr(artifacts, "output_dir", None)
    if not src:
        return None
    src = Path(src)
    if not src.exists():
        return None

    cell_name = "_".join(f"{k}={v}" for k, v in sorted(run_config.items()))
    suffix = "" if artifacts.succeeded else "-failed"
    dest = archive_root / cell_name / f"rep{replicate}{suffix}"
    if dest.exists():
        # Already archived (idempotent on resume of an in-progress run).
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Archive source + tests only. Build output and vendored dependencies
        # are regenerable and actively harmful in the archive: they bloat the
        # repo, embed third-party files that trip secret scanners (e.g. a
        # password fixture inside node_modules), and contain dangling build
        # symlinks (erlang `_build`) that otherwise abort the copy. Scoring
        # already ran against the live playpen and the spec eval reads source,
        # so none of this is needed here.
        shutil.copytree(
            src, dest,
            ignore=_ignore_archive_noise,
            ignore_dangling_symlinks=True,
        )
    except Exception as exc:  # don't let archival failure abort the experiment
        click.echo(f"  (archive failed for {cell_name} rep{replicate}: {exc})", err=True)
        return None

    meta = {
        "visibility": visibility,
        "run_config": run_config,
        "replicate": replicate,
        "succeeded": artifacts.succeeded,
    }
    try:
        (dest / "_meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    except Exception as exc:
        click.echo(f"  (meta write failed for {cell_name} rep{replicate}: {exc})", err=True)
    return dest


def _find_skill(skill_name: str, start: Path | None = None) -> Path | None:
    """Locate a skill's SKILL.md by walking upward from ``start`` (or CWD).

    Skills live in ``<repo>/skills/<name>/SKILL.md``. Returns None if not found.
    """
    start = (start or Path.cwd()).resolve()
    candidates = [start, *start.parents]
    # Also try the retort package's repo root (useful when installed from source).
    try:
        import retort as _retort_pkg
        pkg_root = Path(_retort_pkg.__file__).resolve().parent.parent.parent
        candidates.append(pkg_root)
    except Exception:
        pass
    for base in candidates:
        candidate = base / "skills" / skill_name / "SKILL.md"
        if candidate.is_file():
            return candidate
    return None


def _evaluation_is_current(run_dir: Path) -> bool:
    """True if ``evaluation.md`` exists and is newer than every source file."""
    eval_path = run_dir / "evaluation.md"
    if not eval_path.is_file():
        return False
    eval_mtime = eval_path.stat().st_mtime
    ignore_dirs = {"node_modules", "target", "__pycache__", ".git", "summary"}
    ignore_names = {"evaluation.md", "findings.jsonl"}
    for root, dirs, files in os.walk(run_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            if f in ignore_names:
                continue
            p = Path(root) / f
            try:
                if p.stat().st_mtime > eval_mtime:
                    return False
            except OSError:
                continue
    return True


def _invoke_claude_skill_prompt(
    prompt: str,
    model: str,
    timeout: int = 600,
) -> tuple[int, str]:
    """Invoke claude with a pre-built prompt. Returns (exit_code, combined_output).

    Timeout defaults to 600s to accommodate chained skills (evaluate-run +
    file-run-issues) in a single call.
    """
    from retort.playpen.local_runner import _model_cli_args
    cmd = [
        "claude", "-p", prompt,
        *_model_cli_args(model),
        "--output-format", "text",
        "--dangerously-skip-permissions",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return 127, "claude CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, f"skill invocation timed out after {timeout}s"
    except Exception as exc:
        return 1, f"skill invocation failed: {exc}"


def _invoke_claude_skill(
    skill_path: Path,
    params: dict[str, str],
    model: str,
    timeout: int = 300,
) -> tuple[int, str]:
    """Invoke a claude skill via ``claude -p``. Returns (exit_code, combined_output).

    Never raises — a missing ``claude`` binary or a non-zero exit is reported
    through the returned code and stderr text so callers can log and continue.
    """
    from retort.playpen.local_runner import _model_cli_args
    param_str = " ".join(f"{k}={v}" for k, v in params.items())
    prompt = f"Follow skill at {skill_path} for {param_str}"
    cmd = [
        "claude", "-p", prompt,
        *_model_cli_args(model),
        "--output-format", "text",
        "--dangerously-skip-permissions",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return 127, "claude CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, f"skill invocation timed out after {timeout}s"
    except Exception as exc:
        return 1, f"skill invocation failed: {exc}"


def _declutter_for_eval(run_dir: Path) -> int:
    """Strip build output from an archived run before the judge reads it.

    The judge is handed the run directory to grade the *source* against a
    requirement checklist — but a scored run also contains whatever the build
    left behind. A Go cell archives a **15.7 MB compiled binary** next to 20 KB of
    source, plus SQLite WAL/SHM files, `__pycache__`, `node_modules`, `target/`.
    The judge then explores 16 MB to grade 20 KB.

    Removing it is safe (the scorer has already built and tested; these are
    outputs, not inputs) and pays twice: the eval is faster, and the judge has
    less irrelevant material to misread — this judge disagrees with itself on
    identical code (mean 0.18, max 0.92 requirement-coverage swing), and clutter
    is one plausible contributor.

    Returns the number of entries removed.
    """
    removed = 0
    _DIRS = {"__pycache__", "node_modules", "target", ".pytest_cache", ".venv",
             "build", "dist", ".gradle", ".mypy_cache", ".ruff_cache"}
    _SUFFIXES = (".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".pyc",
                 ".class", ".o", ".so", ".dylib", ".beam")
    for p in sorted(run_dir.rglob("*"), key=lambda x: -len(x.parts)):
        try:
            if p.is_dir():
                if p.name in _DIRS:
                    shutil.rmtree(p, ignore_errors=True)
                    removed += 1
                continue
            if p.name.endswith(_SUFFIXES):
                p.unlink()
                removed += 1
                continue
            # A compiled executable: no suffix, executable bit, and big. Source
            # files and scripts never look like this.
            if (
                "." not in p.name
                and p.stat().st_size > 512_000
                and os.access(p, os.X_OK)
            ):
                p.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def _run_auto_evaluation(
    run_dir: Path,
    eval_config,
    visibility: str,
    *,
    force: bool = False,
    extra_prompt: str = "",
) -> None:
    """Invoke evaluate-run + file-run-issues in a single claude call per run.

    Both skills are chained into one prompt so the subprocess starts once,
    reads context once, and writes all outputs in a single session. Never
    raises. Skips when evaluation.md is already current unless force is set.
    Private experiments are clamped to the beads tracker.
    """
    if not eval_config.enabled:
        return
    if not run_dir.is_dir():
        click.echo(f"  (evaluate: {run_dir} missing, skipping)", err=True)
        return
    if not force and _evaluation_is_current(run_dir):
        click.echo(f"  (evaluate: {run_dir.name} up-to-date, skipping)")
        return

    eval_skill = _find_skill("evaluate-run", start=run_dir)
    if eval_skill is None:
        click.echo("  (evaluate: skills/evaluate-run not found, skipping)", err=True)
        return

    # Private experiments never reach GitHub.
    tracker = eval_config.issue_tracker
    if visibility == "private" and tracker != "beads":
        tracker = "beads"

    file_skill = _find_skill("file-run-issues", start=run_dir)

    click.echo(f"  evaluating {run_dir.name} (model={eval_config.model})...")

    if file_skill is not None:
        # Chain both skills into one subprocess: one cold-start, one context load.
        prompt = (
            f"Follow skill at {eval_skill} for run_dir={run_dir}. "
            f"Then follow skill at {file_skill} for "
            f"run_dir={run_dir} tracker={tracker} "
            f"min_severity={eval_config.min_severity_to_file}."
        ) + (extra_prompt or "")
        rc, output = _invoke_claude_skill_prompt(prompt, eval_config.model)
    elif extra_prompt:
        rc, output = _invoke_claude_skill_prompt(
            f"Follow skill at {eval_skill} for run_dir={run_dir}.{extra_prompt}",
            eval_config.model,
        )
    else:
        rc, output = _invoke_claude_skill(
            eval_skill, {"run_dir": str(run_dir)}, eval_config.model
        )

    if rc != 0:
        click.echo(f"  (evaluate failed rc={rc}; continuing) {output[:200]}", err=True)


def _read_requirement_coverage(run_dir: Path) -> float | None:
    """Return the eval's requirement_coverage from assessment.json, or None if
    it isn't present/parseable (eval failed or produced no requirement count)."""
    p = run_dir / "assessment.json"
    if not p.exists():
        return None
    try:
        v = json.loads(p.read_text()).get("requirement_coverage")
        return float(v) if v is not None else None
    except (ValueError, TypeError, OSError):
        return None


def _shortfalls_claimed(run_dir: Path) -> list[dict]:
    """The requirements the FIRST opinion claimed were unmet, with its evidence.

    Read from ``assessment.json``'s ``top_findings`` — each carries the requirement
    id, what the evaluator thought was missing, and the evidence it cited.
    """
    p = run_dir / "assessment.json"
    try:
        data = json.loads(p.read_text())
    except (ValueError, OSError):
        return []
    out = []
    for f in data.get("top_findings") or []:
        if not isinstance(f, dict):
            continue
        if f.get("kind") and "requirement" not in str(f.get("kind")):
            continue  # a code-quality finding, not a claimed spec gap
        out.append({
            "id": str(f.get("id") or "?"),
            "title": str(f.get("title") or ""),
            "evidence": str(f.get("evidence") or ""),
        })
    return out


def _build_challenge(shortfalls: list[dict], coverage: float | None) -> str:
    """An 'are you sure?' prompt for the SECOND opinion.

    The second opinion exists to catch **false failures** — a complete implementation
    that the first evaluator marked short because it didn't find the code. A blind
    re-roll is a poor way to do that: it just draws another sample from a noisy judge
    (measured: mean requirement_coverage swing 0.18 between two reads of *identical*
    code, max 0.92). Re-checking the *specific* claims is both more reliable and
    cheaper — the evaluator re-examines a handful of requirements instead of
    re-grading the whole spec.

    The prompt deliberately asks it to go **looking for the implementation**, because
    that is the failure mode being guarded against. It must still be able to confirm a
    genuine gap — the gate fails on two short opinions — so it is asked for
    file:line evidence either way, not for a verdict it can hand back on vibes.
    """
    claims = "\n".join(
        f"  - {s['id']}: {s['title']}\n      first evaluator's evidence: {s['evidence']}"
        for s in shortfalls
    ) or "  (the first pass recorded no specific requirement findings)"
    return (
        "\n\nSECOND OPINION — you are RE-CHECKING a prior evaluation, not starting fresh.\n"
        f"A first evaluation scored requirement_coverage={coverage} and claimed these "
        "requirements were NOT met:\n"
        f"{claims}\n\n"
        "For EACH claim above: are you sure? Go and look for the implementation in the "
        "code before accepting that it is missing.\n"
        "  - If you FIND it, the first evaluator was wrong — say so and cite file:line.\n"
        "  - If it is genuinely absent or incomplete, confirm it and cite what you "
        "checked.\n"
        "First evaluations miss existing implementations more often than they invent "
        "them, so the burden of proof is on the claim that something is MISSING.\n"
        "Then re-score requirement_coverage over the FULL checklist and write "
        "assessment.json as usual."
    )


def _spec_conformance_passes(run_dir, eval_config, visibility) -> tuple[bool | None, float | None]:
    """Second-opinion spec gate. Returns ``(verdict, coverage)``:

    * ``True``  — a real eval found requirement_coverage == 1.0 (pass).
    * ``False`` — two real evals both fell short (genuine spec gap).
    * ``None``  — inconclusive: the eval could not run (usage limit / timeout),
      so there aren't two real opinions. The caller should retry later rather
      than record a failure — this keeps an infra hiccup from masquerading as a
      spec failure.

    A run fails only on two short opinions, so borderline judge noise on a single
    requirement can't sink a complete run while a real omission still does.

    **The second opinion is a CHALLENGE, not an independent re-roll.** It used to be
    the latter: the first eval's output was deleted and the judge graded the whole
    spec again from scratch. That is a weak way to catch a false failure, because it
    just draws another sample from a noisy judge — measured across 22 paired reads of
    *identical* code, requirement_coverage moved by a mean of 0.18 and as much as
    0.92. The second pass now receives the specific requirements the first pass
    claimed were missing, plus its evidence, and is asked to go and look for the
    implementation ("are you sure?"). Focused, so it is also cheaper.

    The trade is deliberate: independence is exchanged for a targeted verification.
    Anchoring is the risk, so the prompt puts the burden of proof on the claim that
    something is MISSING (the failure mode being guarded against) and demands
    file:line evidence either way — it can still confirm a genuine gap, which is what
    keeps a real omission failing.
    """
    reals: list[float] = []
    challenge = ""
    for attempt in (1, 2):
        # Before wiping the first opinion's output, capture WHAT it claimed was
        # missing — the second opinion re-checks those specific claims rather than
        # blindly re-rolling a noisy judge. See _build_challenge.
        if attempt == 2:
            challenge = _build_challenge(
                _shortfalls_claimed(run_dir), reals[-1] if reals else None
            )
        # Clear prior eval output, so a failed/partial eval leaves no file
        # and _read_requirement_coverage returns None (inconclusive) — never a
        # stale value from an earlier eval misread as this run's fresh result.
        for fname in ("assessment.json", "evaluation.md", "findings.jsonl"):
            try:
                (run_dir / fname).unlink()
            except (FileNotFoundError, IsADirectoryError, TypeError):
                pass
        if attempt == 1:
            # Give the judge the source, not the build output (see
            # _declutter_for_eval). Done once, before the first opinion — both
            # attempts then grade byte-identical material, which is the whole
            # point of a second opinion.
            _declutter_for_eval(run_dir)
        _run_auto_evaluation(
            run_dir, eval_config, visibility, force=True, extra_prompt=challenge
        )
        cov = _read_requirement_coverage(run_dir)
        if cov is None:
            click.echo(f"    spec gate attempt {attempt}/2: eval did not run (inconclusive)")
            continue
        reals.append(cov)
        if cov >= 1.0:
            if attempt == 2:
                click.echo("    spec gate: passed on second opinion")
            return True, cov
        click.echo(
            f"    spec gate attempt {attempt}/2: requirement_coverage={cov} (<1.0)"
        )
    if len(reals) >= 2:
        return False, max(reals)   # two real opinions, both short -> genuine fail
    if len(reals) == 1:
        return None, reals[0]      # only one real opinion (other couldn't run)
    return None, None              # no real opinions at all


def _factor_match_sql(run_config: dict, col: str = "run_config_json") -> tuple[str, list]:
    """Build a WHERE fragment matching EVERY factor in a run_config.

    Matches on every factor present in run_config — language/model/tooling AND
    any others a design adds (e.g. ``prompt``). Hardcoding only language/model/
    tooling meant a prompt-factor design (exp-13) matched all prompt variants of
    a cell and persisted to whichever row sorted first — so reevaluate/rescore
    silently mis-targeted. ``tooling`` is always included and matched as JSON
    ``null`` (``IS NULL``) when absent, since designs without a tooling factor
    (exp-7/8) store no tooling key and ``= NULL`` is never true in SQL.
    """
    clauses, params = [], []
    for factor in sorted(set(run_config) | {"tooling"}):
        val = run_config.get(factor)
        if val is None:
            clauses.append(f"json_extract({col},'$.{factor}') IS NULL")
        else:
            clauses.append(f"json_extract({col},'$.{factor}')=?")
            params.append(val)
    return " AND ".join(clauses), params


def _run_config_from_cell_name(name: str) -> dict | None:
    """Parse an archive cell-dir name into a run_config of factor values.

    Cell dirs are named ``<factor>=<value>_<factor>=<value>…`` (sorted keys,
    e.g. ``language=go_model=opus-4.8-fast_prompt=ATDD``). Generalised over ALL
    factors — not just language/model/tooling — so designs with extra factors
    (prompt, …) re-score and re-evaluate correctly. The value pattern is
    non-greedy up to the next ``_<word>=`` boundary, so values containing ``-``
    or ``.`` (``opus-4.8-fast``) parse intact. Returns None if no pairs match.
    """
    # Keys start with a letter so findall skips the ``_`` pair separators
    # (``\w`` would otherwise swallow them into the next key as ``_model``).
    pairs = re.findall(r"([A-Za-z]\w*)=(.+?)(?=_[A-Za-z]\w*=|$)", name)
    return dict(pairs) if pairs else None


def _iter_archive_cells(runs_root: Path) -> list[tuple[str, Path]]:
    """Return ``(cell_name, cell_dir)`` for every archived cell under ``runs_root``.

    A cell dir is any directory that *directly* contains a ``rep<N>`` (or
    ``rep<N>-failed``) subdir; its ``cell_name`` is the path *relative to*
    ``runs_root``. Using the relative path is what makes model ids containing
    ``/`` work: ``openrouter/anthropic/claude-opus-4.8`` nests the cell several
    directories deep (``…model=openrouter/anthropic/claude-opus-4.8_tooling=none``),
    and a plain ``runs_root.iterdir()`` stops at the first segment
    (``…model=openrouter``) — so rescore/reevaluate/evaluate found nothing and
    silently processed zero runs. For a single-segment cell name (no ``/`` in any
    factor value) this yields exactly what the old two-level walk did, so existing
    experiments are unaffected. Feed each ``cell_name`` to
    ``_run_config_from_cell_name`` (its value pattern already spans ``/``).
    """
    cells: list[tuple[str, Path]] = []
    for dirpath, dirnames, _files in os.walk(runs_root):
        d = Path(dirpath)
        # A cell dir is one with a "rep…" child — same loose test the callers use
        # to pick rep dirs (rep0, rep1, rep1-failed, and fixtures like rep-0).
        rep_children = [n for n in dirnames if n.startswith("rep")]
        if rep_children:
            cells.append((str(d.relative_to(runs_root)), d))
            # A rep dir holds source, not further cells — don't descend into it.
            dirnames[:] = [n for n in dirnames if n not in rep_children]
    return cells


def _run_row_exists(db_path, run_config: dict, replicate: int) -> bool:
    """True if ANY experiment_runs row matches these factors+replicate.

    Distinguishes an archive that maps to a real DB row (regardless of status)
    from an ORPHAN whose factors match nothing — the signature of broken
    cell-name parsing / factor matching (which silently dropped 33/36 cells of a
    prompt-factor experiment before the parser was generalised).
    """
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            f"SELECT 1 FROM experiment_runs WHERE replicate=? AND {where} LIMIT 1",
            (replicate, *params)).fetchone()
    finally:
        con.close()
    return row is not None


def _eval_tooling_preflight(eval_model: str, runs_root: Path) -> tuple[bool, str]:
    """Confirm the second-opinion eval tooling is actually usable before a batch.

    Checks (a) the evaluate-run skill is discoverable and (b) the judge model
    answers a trivial prompt. Returns (ok, message). Catches the silent-failure
    class where reevaluate "succeeds" but the judge never ran (CLI missing,
    model unreachable, usage exhausted) — persisting nothing while reporting
    success.
    """
    import subprocess

    from retort.playpen.local_runner import _find_skill_path, _model_cli_args
    shown = eval_model or "latest (CLI default)"
    start = next((r for c in runs_root.iterdir() if c.is_dir()
                  for r in c.iterdir() if r.is_dir()), runs_root)
    if _find_skill_path("evaluate-run", start=start) is None:
        return False, "evaluate-run skill not found (cannot grade requirement_coverage)"
    try:
        proc = subprocess.run(
            ["claude", "-p", "Reply with exactly: OK", *_model_cli_args(eval_model),
             "--output-format", "text", "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=90,
        )
    except FileNotFoundError:
        return False, "claude CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return False, f"judge model {shown} did not respond within 90s"
    if proc.returncode != 0:
        return False, (f"judge model {shown} probe failed "
                       f"(exit {proc.returncode}): {proc.stderr.strip()[:140]}")
    if "OK" not in (proc.stdout or ""):
        return False, f"judge model {shown} returned no usable output"
    return True, f"judge {shown} reachable, evaluate-run skill present"


def _run_has_requirement_coverage(db_path, run_config: dict, replicate: int) -> bool:
    """True if the matching completed run already has a requirement_coverage row."""
    import sqlite3
    where, params = _factor_match_sql(run_config, "er.run_config_json")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT 1 FROM run_results rr JOIN experiment_runs er ON er.id=rr.run_id "
            "WHERE rr.metric_name='requirement_coverage' AND er.replicate=? "
            f"AND {where} LIMIT 1",
            (replicate, *params),
        ).fetchone()
    except sqlite3.OperationalError:
        row = None
    con.close()
    return row is not None


def _run_completed_exists(db_path, run_config: dict, replicate: int) -> bool:
    """True if a *completed* run matches these factors+replicate. A clean rep
    dir whose DB run is `failed` (or absent) can never receive coverage, so the
    re-evaluator skips it instead of burning evals on it every pass."""
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT 1 FROM experiment_runs WHERE replicate=? AND status='completed' "
            f"AND {where} LIMIT 1",
            (replicate, *params),
        ).fetchone()
    except sqlite3.OperationalError:
        row = None
    con.close()
    return row is not None


def _persist_requirement_coverage(db_path, run_config: dict, replicate: int,
                                  coverage: float | None) -> bool:
    """Upsert requirement_coverage onto the matching latest completed run.

    Non-destructive: only adds/replaces the requirement_coverage metric; never
    touches the run's status. Matches by factors + replicate (robust to JSON key
    order). Returns True if a run was found and updated.
    """
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id FROM experiment_runs WHERE replicate=? AND status='completed' "
        f"AND {where} ORDER BY finished_at DESC", (replicate, *params),
    ).fetchall()
    if not rows:
        con.close()
        return False
    run_id = rows[0][0]
    cur.execute("DELETE FROM run_results WHERE run_id=? AND metric_name='requirement_coverage'",
                (run_id,))
    if coverage is not None:
        cur.execute("INSERT INTO run_results (run_id, metric_name, value) VALUES (?,?,?)",
                    (run_id, "requirement_coverage", float(coverage)))
    con.commit()
    con.close()
    return True


def _persist_rescore(db_path, run_config: dict, replicate: int,
                     scores: dict[str, float]) -> str | None:
    """Write re-scored mechanical metrics onto the latest matching run.

    Updates the scorer metrics in-place (preserving the ``_``-prefixed telemetry
    and requirement_coverage), then reclassifies status via the conformance gate
    — a run whose tests now execute (``test_coverage`` > 0) becomes ``completed``;
    one that doesn't becomes ``failed``. Matches by factors + replicate across
    *any* status (so a false-failed run can be recovered). Returns the new status
    string, or None if no matching run was found.
    """
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        f"SELECT id FROM experiment_runs WHERE replicate=? AND {where} "
        "ORDER BY finished_at DESC", (replicate, *params),
    ).fetchall()
    if not rows:
        con.close()
        return None
    run_id = rows[0][0]
    for name, value in scores.items():
        cur.execute("UPDATE run_results SET value=? WHERE run_id=? AND metric_name=?",
                    (float(value), run_id, name))
        if cur.rowcount == 0:
            cur.execute("INSERT INTO run_results (run_id, metric_name, value) VALUES (?,?,?)",
                        (run_id, name, float(value)))
    new_status = "completed" if scores.get("test_coverage", 0.0) > 0.0 else "failed"
    cur.execute(
        "UPDATE experiment_runs SET status=?, error_message=? WHERE id=?",
        (new_status, None if new_status == "completed"
         else "tests did not run (test_coverage=0)", run_id),
    )
    con.commit()
    con.close()
    return new_status


def _persist_metric_values(db_path, run_config: dict, replicate: int,
                           scores: dict[str, float]) -> bool:
    """Update only the named metrics on the latest matching run; no status change.

    For fixing a non-gating scorer gap (e.g. maintainability) on a passing run
    without re-running its (possibly un-rebuildable) tests. Returns True if a
    matching run was found.
    """
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    row = cur.execute(
        f"SELECT id FROM experiment_runs WHERE replicate=? AND {where} "
        "ORDER BY finished_at DESC", (replicate, *params)).fetchone()
    if not row:
        con.close()
        return False
    run_id = row[0]
    for name, value in scores.items():
        cur.execute("UPDATE run_results SET value=? WHERE run_id=? AND metric_name=?",
                    (float(value), run_id, name))
        if cur.rowcount == 0:
            cur.execute("INSERT INTO run_results (run_id, metric_name, value) VALUES (?,?,?)",
                        (run_id, name, float(value)))
    con.commit()
    con.close()
    return True


def _persist_design_matrix(
    session,
    registry,
    design,
    phase: str,
    workspace_config,
) -> tuple[int, dict[str, int]]:
    """Persist the generated design matrix + factor levels to the database.

    Returns (matrix_id, mapping from sorted-json-config-key to row_id).

    Idempotent: a matrix with a matching (name, phase) is reused, with its
    rows looked up rather than re-created. This keeps repeated `retort run`
    invocations from accumulating duplicate matrices.
    """
    from retort.storage.models import (
        DesignMatrix,
        DesignMatrixCell,
        DesignMatrixRow,
        FactorLevel,
        LifecyclePhase,
    )

    name = workspace_config.experiment.name or "experiment"
    matrix_name = f"{name}-{phase}"
    phase_enum = LifecyclePhase(phase) if not isinstance(phase, LifecyclePhase) else phase

    # Look up an existing matrix with the same (name, phase). On resume this
    # avoids spawning a new matrix per run.
    matrix = (
        session.query(DesignMatrix)
        .filter(DesignMatrix.name == matrix_name, DesignMatrix.phase == phase_enum)
        .one_or_none()
    )
    if matrix is None:
        matrix = DesignMatrix(name=matrix_name, phase=phase_enum)
        session.add(matrix)
        session.flush()

    # Ensure all (factor_name, level_name) pairs exist as FactorLevel rows.
    level_lookup: dict[tuple[str, str], int] = {}
    for factor in registry.factors:
        for level in factor.levels:
            existing = (
                session.query(FactorLevel)
                .filter(
                    FactorLevel.factor_name == factor.name,
                    FactorLevel.level_name == level,
                )
                .one_or_none()
            )
            if existing is None:
                existing = FactorLevel(factor_name=factor.name, level_name=level)
                session.add(existing)
                session.flush()
            level_lookup[(factor.name, level)] = existing.id

    # Build the row index → row_id map. Skip rows that already exist (resume).
    config_to_row_id: dict[str, int] = {}
    for row_idx, run_config in enumerate(design.run_configs()):
        existing_row = (
            session.query(DesignMatrixRow)
            .filter(
                DesignMatrixRow.matrix_id == matrix.id,
                DesignMatrixRow.row_index == row_idx,
            )
            .one_or_none()
        )
        if existing_row is None:
            existing_row = DesignMatrixRow(matrix_id=matrix.id, row_index=row_idx)
            session.add(existing_row)
            session.flush()
            for factor_name, level_name in run_config.items():
                level_id = level_lookup.get((factor_name, level_name))
                if level_id is None:
                    # Factor or level not in registry — skip silently.
                    continue
                session.add(DesignMatrixCell(
                    row_id=existing_row.id, factor_level_id=level_id,
                ))
        else:
            # Reusing a row from a prior run (resume). Verify its persisted
            # factors match this config. Rows are keyed by POSITION, so if the
            # supplied --design's row order has drifted from the matrix, mapping
            # this config onto the existing row would silently overwrite a
            # DIFFERENT cell's runs via the uq_run_replicate constraint — the
            # row-index collision that clobbered 30 runs in exp-15 when a new
            # --design reused run indices 0-9 that already held other models.
            existing_factors = dict(
                session.query(FactorLevel.factor_name, FactorLevel.level_name)
                .join(
                    DesignMatrixCell,
                    DesignMatrixCell.factor_level_id == FactorLevel.id,
                )
                .filter(DesignMatrixCell.row_id == existing_row.id)
                .all()
            )
            mismatch = {
                fn: (lv, run_config.get(fn))
                for fn, lv in existing_factors.items()
                if run_config.get(fn) != lv
            }
            if mismatch:
                raise click.ClickException(
                    f"--design row {row_idx} already exists in matrix "
                    f"'{matrix_name}' with factors {existing_factors}, but the "
                    f"supplied design maps a different cell onto it (differs on "
                    f"{mismatch}). Refusing to overwrite: a --design CSV's row "
                    f"order must match the persisted matrix. Give new cells "
                    f"non-overlapping run indices, or use a fresh experiment."
                )

        config_to_row_id[json.dumps(run_config, sort_keys=True)] = existing_row.id

    return matrix.id, config_to_row_id


def _tests_did_not_run(scores) -> bool:
    """A run whose tests never executed (``test_coverage == 0``) is not a valid
    success: it offers no proof the code works. Returns True when a
    ``test_coverage`` score is present and zero, so callers can mark the run
    ``failed`` rather than recording a zero-scored "completion". Returns False
    when test_coverage isn't among the responses (no gate to apply).
    """
    for s in getattr(scores, "scores", []):
        if s.metric_name == "test_coverage":
            return s.value == 0.0
    return False


def _store_run_result(
    session,
    run_config: dict[str, str],
    phase: str,
    run_idx: int,
    replicate: int,
    artifacts,
    scores,
    design_row_id: int | None = None,
    conformance_failed: bool = False,
    requirement_coverage: float | None = None,
    second_try: bool = False,
) -> None:
    """Store a run and its scores in the database.

    Status is three-way: a run whose agent never completed (``artifacts.succeeded``
    is False — CLI error, timeout kill, server unreachable) is ``crashed`` and is
    retried on ``--resume``. A run whose agent completed but that ``conformance_failed``
    (tests did not run, or the spec gate judged it short) is ``failed`` — a VALID
    data point that counts as progress and is not retried by default. Otherwise it
    is ``completed``. ``requirement_coverage``, when the spec eval produced one, is
    persisted as a metric so the eval's verdict feeds the scored data.
    """
    from retort.storage.models import (
        ExperimentRun,
        RunResult,
        RunStatus,
    )
    from datetime import datetime, timezone

    # Three-way outcome:
    #   crashed   — the agent did not complete (CLI error / timeout kill / server
    #               unreachable): no scoreable result → retried on --resume.
    #   failed    — the agent completed but the run fell short of a gate (tests
    #               did not run, or spec eval judged it incomplete): a VALID data
    #               point → counts as progress, not retried by default.
    #   completed — the agent completed and passed every gate.
    if not artifacts.succeeded:
        status = RunStatus.crashed
    elif conformance_failed:
        status = RunStatus.failed
    else:
        status = RunStatus.completed

    # Resume + retry-failed: a failed ExperimentRun for this same
    # (design_row_id, replicate) already exists. The unique constraint on
    # (design_row_id, replicate) blocks a fresh insert, so delete the
    # superseded row + its results first. design_row_id is None for runs
    # that predate matrix persistence; in that case match by run_config.
    if design_row_id is not None:
        existing = (session.query(ExperimentRun)
                    .filter_by(design_row_id=design_row_id, replicate=replicate)
                    .all())
    else:
        existing = (session.query(ExperimentRun)
                    .filter(
                        ExperimentRun.replicate == replicate,
                        ExperimentRun.run_config_json == json.dumps(run_config),
                    )
                    .all())
    for old in existing:
        session.query(RunResult).filter_by(run_id=old.id).delete()
        session.delete(old)
    if existing:
        session.flush()

    run = ExperimentRun(
        design_row_id=design_row_id,
        replicate=replicate,
        status=status,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        error_message=(
            artifacts.stderr if not artifacts.succeeded
            else "tests did not run (test_coverage=0)" if conformance_failed
            else None
        ),
        run_config_json=json.dumps(run_config),
    )

    session.add(run)
    session.flush()  # Get the run ID

    for score in scores.scores:
        result = RunResult(
            run_id=run.id,
            metric_name=score.metric_name,
            value=score.value,
        )
        session.add(result)

    # The spec eval's verdict, when one was produced, is a first-class metric.
    if requirement_coverage is not None:
        session.add(RunResult(
            run_id=run.id,
            metric_name="requirement_coverage",
            value=float(requirement_coverage),
        ))

    # Persist non-scorer telemetry as RunResult rows too. Underscore prefix
    # marks them as side-channel data (vs. configured response metrics) so
    # downstream tools (analyze, web report) can choose to surface or hide
    # them. Without this, token/cost/duration are visible only at run-time
    # and lost forever. Stored for EVERY run — including `failed` and `crashed`
    # — even when zero, so a failure always records how long it took and how
    # many tokens it burned (a $0/0-token crash is itself a diagnostic signal).
    if artifacts.duration_seconds is not None:
        session.add(RunResult(
            run_id=run.id,
            metric_name="_duration_seconds",
            value=float(artifacts.duration_seconds),
        ))
    if artifacts.token_count is not None:
        session.add(RunResult(
            run_id=run.id,
            metric_name="_tokens",
            value=float(artifacts.token_count),
        ))
    # Peak context: the largest prompt the model was fed during this run. `_tokens`
    # is the run's TOTAL spend; this is its high-water CONTEXT mark — a different
    # question, and the one that says whether the context window is sized right.
    _peak = (artifacts.metadata or {}).get("max_context_tokens")
    if _peak:
        try:
            session.add(RunResult(
                run_id=run.id,
                metric_name="_max_context_tokens",
                value=float(_peak),
            ))
        except (TypeError, ValueError):
            pass
    # Flag a run that only reached its outcome on the self-repair SECOND attempt.
    # A second-try PASS counts at HALF credit toward pass-proportion in analysis;
    # the raw scores stay at their true final values.
    if second_try:
        session.add(RunResult(
            run_id=run.id,
            metric_name="_second_try",
            value=1.0,
        ))
    cost_str = artifacts.metadata.get("total_cost_usd") if artifacts.metadata else None
    if cost_str:
        try:
            # Attach OpenRouter reconcile provenance so validate_openrouter_spend.py
            # can cross-check this run's omp-reported cost against the billing API
            # (/api/v1/generation per id). Present only on OpenRouter-routed runs;
            # None otherwise so non-OpenRouter rows stay clean.
            reconcile = {
                k: artifacts.metadata[k]
                for k in (
                    "openrouter_generation_ids",
                    "upstream_provider",
                    "omp_cost_sum_all_turns",
                    "omp_assistant_turns",
                )
                if artifacts.metadata and k in artifacts.metadata
            }
            session.add(RunResult(
                run_id=run.id,
                metric_name="_cost_usd",
                value=float(cost_str),
                metadata_json=json.dumps(reconcile) if reconcile else None,
            ))
        except (TypeError, ValueError):
            pass
    turns_str = artifacts.metadata.get("num_turns") if artifacts.metadata else None
    if turns_str:
        try:
            turns_val = float(turns_str)
            if turns_val > 0:
                session.add(RunResult(
                    run_id=run.id,
                    metric_name="_turns",
                    value=turns_val,
                ))
        except (TypeError, ValueError):
            pass




@main.group()
def report() -> None:
    """Analysis and reporting commands."""






@main.group()
def plugin() -> None:
    """Plugin management commands."""


@main.group()
def export() -> None:
    """Export experiment data for downstream analysis."""


@main.group()
def tasks() -> None:
    """Task registry commands (the task sources retort can run)."""










def _etime_to_seconds(etime: str) -> float | None:
    """Parse BSD/GNU ps etime ([[dd-]hh:]mm:ss) into seconds."""
    etime = etime.strip()
    if not etime:
        return None
    days = 0
    if "-" in etime:
        d, etime = etime.split("-", 1)
        if not d.isdigit():
            return None
        days = int(d)
    parts = etime.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    secs = 0
    for n in nums:
        secs = secs * 60 + n
    return float(days * 86400 + secs)


def _discover_active_runs(db_path: Path) -> list[dict]:
    """Best-effort list of in-flight agent runs for this experiment.

    Finds ``retort run`` processes referencing this experiment directory, then
    their ``claude`` agent children, and reads each child's playpen
    ``stack.json`` (cell) plus ``ps`` elapsed time. Returns [] when it can't
    determine them (no process access / not the run host). Local-only.
    """
    import json as _json
    import os
    import subprocess

    # Agent CLIs retort shells out to. The active job is one of these — NOT just
    # `claude`: a local-model cell runs `omp`/`hermes`/`gemini`/`opencode`, so
    # keying only on `claude` showed nothing while a local model was working and
    # only lit up during the (claude) spec-gate eval.
    _AGENT_BINS = ("claude", "omp", "hermes", "gemini", "opencode")

    def _run(args: list[str]) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=5)
        except Exception:  # noqa: BLE001 - best-effort; never fail the monitor
            return None

    exp = db_path.resolve().parent.name
    # Match both invocation styles: the `retort run ... <exp>` console script and
    # the `python -c '...main()' run ... <exp>` form (used by sharded runners).
    r = _run(["pgrep", "-f", f"run .*{exp}"])
    if r is None or r.returncode not in (0, 1):
        return []
    # Launchers that sit BETWEEN `retort run` and the agent, so the agent is a
    # grandchild rather than a direct child (e.g. `uv run … hermes`, an
    # `env`-shebang shim, a direnv/nix wrapper). Descend through these when a
    # direct child is one of them — otherwise a wrapped agent shows nothing in the
    # live monitor even though it is working.
    _WRAPPERS = {"uv", "uvx", "env", "poetry", "pdm", "direnv", "nix"}

    def _agent_candidate_pids(parent: str, depth: int = 0) -> list[str]:
        ch = _run(["pgrep", "-P", parent])
        if ch is None or depth > 4:
            return []
        out: list[str] = []
        for cpid in ch.stdout.split():
            psc = _run(["ps", "-o", "command=", "-p", cpid])
            cmd0 = psc.stdout.strip() if psc else ""
            first = os.path.basename(cmd0.split()[0]) if cmd0 else ""
            if first in _WRAPPERS:
                out.extend(_agent_candidate_pids(cpid, depth + 1))
            else:
                out.append(cpid)
        return out

    active: list[dict] = []
    seen: set[str] = set()
    for rpid in r.stdout.split():
        for cpid in _agent_candidate_pids(rpid):
            psc = _run(["ps", "-o", "command=", "-p", cpid])
            cmd = psc.stdout.strip() if psc else ""
            if not cmd:
                continue
            # Which agent CLI is this child? Check the basename of the first two
            # argv tokens — the binary is either the program itself (`claude`,
            # `omp`, `gemini`) or the script run by an interpreter (a pip/npm
            # entry point like `Python .../bin/hermes` or `node .../opencode`).
            # Scanning only the first two tokens avoids matching an agent name
            # that merely appears inside the prompt text.
            tokens = cmd.split()
            candidates = {os.path.basename(t) for t in tokens[:2]}
            agent_bin = next((b for b in _AGENT_BINS if b in candidates), None)
            if agent_bin is None:
                continue
            # The spec-gate eval is a `claude` child WITHOUT `--max-turns` (the
            # claude-code *agent* always passes --max-turns). Any local-agent CLI
            # child (omp/hermes/…) is the job itself, never the eval.
            evaluating = agent_bin == "claude" and "--max-turns" not in cmd
            lf = _run(["lsof", "-a", "-p", cpid, "-d", "cwd", "-Fn"])
            cwd = ""
            if lf is not None:
                for line in lf.stdout.splitlines():
                    if line.startswith("n"):
                        cwd = line[1:]
                        break
            if not cwd or cwd in seen:
                continue
            seen.add(cwd)
            # Which CELL is this process working on? The agent runs *in* the playpen,
            # so its cwd holds stack.json. The spec-gate EVALUATOR does not — it is a
            # claude process launched elsewhere, carrying the cell only as
            # `run_dir=<archived run dir>` in its prompt. Without this it rendered as
            # a bare "?", which is useless precisely when a long eval is the thing
            # holding the experiment up.
            cell_dir = Path(cwd)
            if not (cell_dir / "stack.json").is_file():
                m = re.search(r"run_dir=(\S+)", cmd)
                if m:
                    # The path is embedded in prose, so it picks up trailing
                    # sentence punctuation — strip it, or stack.json is never found
                    # and the label degrades to the raw archive dir name.
                    cell_dir = Path(m.group(1).rstrip('"\'.,;:)'))
            label = "?"
            try:
                sj = _json.loads((cell_dir / "stack.json").read_text())
                # Prefer the short stack-preset id over the full model id: a cell
                # carrying both (a stack-preset sweep) would otherwise render as
                # `rust/mlxlocal/Qwen3.6-35B-A3B/...`, where the model id's own
                # slashes masquerade as extra factors. Fall back to the model's
                # last path segment when there is no preset.
                fields = ("language", "stack", "agent", "tooling", "prompt")
                if "stack" not in sj:
                    fields = ("language", "model", "agent", "tooling", "prompt")
                label = "/".join(
                    str(sj[k]).rsplit("/", 1)[-1]
                    for k in fields
                    if k in sj and str(sj[k]) not in ("", "unknown")
                )
            except Exception:  # noqa: BLE001
                pass
            if label == "?" and cell_dir != Path(cwd):
                # No stack.json (an archive predating it) — the path still names the
                # cell: .../runs/<cell>/rep2 → "<cell> rep2".
                label = f"{cell_dir.parent.name} {cell_dir.name}"
            et = _run(["ps", "-o", "etime=", "-p", cpid])
            elapsed = _etime_to_seconds(et.stdout) if et else None
            # Serving log (if this experiment drives a local server via stack
            # presets) — the only place a non-streaming agent's context is visible.
            _serving_log = None
            try:
                import yaml as _yaml
                _sp = db_path.parent / "stacks.yaml"
                if _sp.is_file():
                    _lg = ((_yaml.safe_load(_sp.read_text()) or {})
                           .get("serving", {}) or {}).get("log")
                    if _lg:
                        _serving_log = Path(_lg)
            except Exception:  # noqa: BLE001 — the monitor must never break a run
                _serving_log = None
            # Do NOT attribute the served model's context to the EVALUATOR. The
            # judge is a separate cloud model; reading the serving log for it just
            # reports the last local run's context (we were showing a stale
            # "ctx 37K (pk 114K)" against an opus judge that never touched it).
            _ctx_now, _ctx_peak = (
                (None, None) if evaluating
                else _live_context_tokens(Path(cwd), _serving_log, elapsed)
            )
            # Is this the self-repair SECOND CHANCE? A repair playpen is seeded with
            # FEEDBACK.md (the requirement checklist + the prior evaluation verdict);
            # a first attempt never has one. Without this the monitor shows the same
            # cell "evaluating" with a reset clock and it reads as a stuck loop.
            _second = (cell_dir / "FEEDBACK.md").is_file() or (
                Path(cwd) / "FEEDBACK.md"
            ).is_file()
            active.append(
                {
                    "label": label,
                    "replicate": None,
                    "elapsed_s": elapsed,
                    "evaluating": evaluating,
                    "second_try": _second,
                    "context_tokens": _ctx_now,
                    "context_peak": _ctx_peak,
                }
            )
    return active


def _run_in_flight(db_path: Path) -> bool:
    """True if a ``retort run`` process is still working on this experiment.

    The `--watch` loop uses this rather than ``snapshot.is_done`` to decide when
    to stop: a *failed* cell counts as a terminal data point, so `is_done` goes
    True during a ``--resume --retry-failed`` pass (or any run whose DB looks
    fully measured) even while `retort run` is actively re-running cells — which
    made `--watch` exit mid-run. The run process, by contrast, is alive for the
    whole experiment (between cells and during the spec-gate eval too), so it is
    the correct "still going" signal. Best-effort: returns False if it can't tell.
    """
    import subprocess

    parts = db_path.resolve().parts
    # Match on the experiment slug (…/experiment-NN-slug/…) so we don't pick up a
    # DIFFERENT experiment's run just because both share a task-dir name (bookshop).
    slug = next((p for p in reversed(parts) if p.startswith("experiment-")), None)
    pattern = f"run .*{re.escape(slug)}" if slug else f"run .*{re.escape(db_path.resolve().parent.name)}"
    try:
        r = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True, timeout=5)
    except Exception:  # noqa: BLE001 — best-effort; never break the monitor
        return False
    return r.returncode == 0 and bool(r.stdout.strip())




if __name__ == "__main__":
    main()


# --- extracted command modules (import LAST: main + all helpers are defined above) ---
from retort.commands import scoring  # noqa: E402
from retort.commands import reporting  # noqa: E402,F401
from retort.commands import utility  # noqa: E402,F401
from retort.commands import workspace  # noqa: E402,F401
from retort.commands import analysis  # noqa: E402,F401
from retort.commands import monitoring  # noqa: E402,F401
from retort.commands.scoring import (  # noqa: E402,F401  backward-compat re-exports
    evaluate, reevaluate, rescore, diagnose, recover, _nonpassing_languages,
)
