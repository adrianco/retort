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


@main.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Overwrite existing directory")
@click.option(
    "--visibility",
    type=click.Choice(["public", "private"]),
    default="private",
    show_default=True,
    help="public = artifacts safe to publish; private = local-only (fail-closed default).",
)
def init(name: str, force: bool, visibility: str):
    """Initialize a new Retort workspace.

    Creates a workspace directory with a config template, a visibility-aware
    .gitignore, and an initialized SQLite database.
    """
    workspace = Path(name).resolve()

    if workspace.exists() and not force:
        raise click.ClickException(
            f"Directory {name!r} already exists. Use --force to overwrite."
        )

    if workspace.exists() and force:
        shutil.rmtree(workspace)

    workspace.mkdir(parents=True, exist_ok=True)

    # Write config template
    config_path = workspace / "workspace.yaml"
    config_path.write_text(
        WORKSPACE_TEMPLATE.replace("__NAME__", name).replace("__VISIBILITY__", visibility)
    )

    # Write visibility-aware .gitignore
    gitignore_path = workspace / ".gitignore"
    gitignore_path.write_text(_gitignore_for(visibility))

    # Initialize database
    db_path = workspace / "retort.db"
    _init_database(db_path)

    click.echo(f"Initialized Retort workspace in {workspace}")
    click.echo(f"  Config:     {config_path}")
    click.echo(f"  Gitignore:  {gitignore_path} (visibility={visibility})")
    click.echo(f"  Database:   {db_path}")
    if visibility == "private":
        click.echo("  Visibility: PRIVATE — runs/, reports/, evaluations stay local.")
    else:
        click.echo("  Visibility: PUBLIC — runs/ and reports/web/ are git-tracked.")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  cd {name}")
    click.echo("  # Edit workspace.yaml to define your factors and responses")
    click.echo("  retort design generate --phase screening")


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


@main.command("visibility-check")
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="Path to workspace YAML config.",
)
def visibility_check(config: str) -> None:
    """Audit which workspace artifacts would be published vs kept local.

    Reads ``experiment.visibility`` from the workspace config, then walks
    the workspace directory and reports each notable artifact as PUBLISHED
    or LOCAL based on .gitignore rules. Exits non-zero if a private-mode
    workspace would publish a sensitive path.
    """
    from retort.config.loader import load_workspace

    cfg = load_workspace(config)
    workspace_dir = Path(config).resolve().parent
    visibility = cfg.experiment.visibility

    click.echo(f"Workspace:  {workspace_dir}")
    click.echo(f"Visibility: {visibility}")
    click.echo()

    gitignore_path = workspace_dir / ".gitignore"
    ignored_lines: set[str] = set()
    if gitignore_path.is_file():
        for line in gitignore_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ignored_lines.add(line.rstrip("/"))

    leaks: list[str] = []
    for entry in sorted(workspace_dir.iterdir()):
        name = entry.name
        if name in {".git", ".gitignore", "workspace.yaml"}:
            continue
        ignored = name in ignored_lines or f"{name}/" in ignored_lines or name.rstrip("/") in ignored_lines
        status = "LOCAL " if ignored else "PUBLISH"
        click.echo(f"  {status}  {name}")
        if visibility == "private" and not ignored and name in _PRIVATE_SENSITIVE_PATHS:
            leaks.append(name)

    if leaks:
        click.echo()
        click.echo(
            f"ERROR: visibility=private but these sensitive paths are NOT gitignored: {leaks}",
            err=True,
        )
        click.echo("Add them to .gitignore before committing.", err=True)
        raise click.ClickException("private workspace would leak sensitive artifacts")


@main.group()
def design() -> None:
    """Design matrix generation commands."""


@design.command("generate")
@click.option(
    "--phase",
    type=click.Choice(["screening", "characterization"]),
    required=True,
    help="Experiment phase (screening = Resolution III, characterization = Resolution IV).",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=None,
    help="Path to workspace YAML config. If omitted, reads factors from stdin as JSON.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output CSV path. Defaults to stdout.",
)
def design_generate(phase: str, config: str | None, output: str | None) -> None:
    """Generate a fractional factorial design matrix.

    Reads factor definitions and produces a design matrix for the given phase.
    Without --config, reads a JSON dict of {factor_name: [levels]} from stdin.
    When workspace.yaml contains ``design.fraction``, the generated matrix is
    automatically reduced to that fraction of the full factorial.
    """
    import math

    registry = _load_factors(config)

    if len(registry) < 2:
        click.echo("Error: need at least 2 factors for design generation.", err=True)
        sys.exit(1)

    # Honour design.fraction from workspace config when available
    fraction: float | None = None
    if config is not None:
        from retort.config.loader import load_workspace
        ws = load_workspace(config)
        fraction = ws.design.fraction

    result = generate_design(registry, phase, fraction=fraction)

    full_n = result.full_factorial_size or math.prod(f.num_levels for f in registry.factors)
    frac_label = f"{result.num_runs}/{full_n}" if result.num_runs != full_n else f"{full_n} (full factorial)"

    if output:
        result.to_csv(output)
        click.echo(f"Design matrix written to {output} ({result.num_runs} runs, {frac_label})")
    else:
        # Summary to stderr so it doesn't pollute a piped CSV
        click.echo(f"# {result.num_runs} runs — {frac_label}", err=True)
        click.echo(result.matrix.to_csv(index_label="run"))


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
                    _refusal = artifacts.metadata.get("tool_refusal")
                    if _refusal:
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


def _run_auto_evaluation(
    run_dir: Path,
    eval_config,
    visibility: str,
    *,
    force: bool = False,
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
        )
        rc, output = _invoke_claude_skill_prompt(prompt, eval_config.model)
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


def _spec_conformance_passes(run_dir, eval_config, visibility) -> tuple[bool | None, float | None]:
    """Second-opinion spec gate. Returns ``(verdict, coverage)``:

    * ``True``  — a real eval found requirement_coverage == 1.0 (pass).
    * ``False`` — two independent real evals both fell short (genuine spec gap).
    * ``None``  — inconclusive: the eval could not run (usage limit / timeout),
      so there aren't two real opinions. The caller should retry later rather
      than record a failure — this keeps an infra hiccup from masquerading as a
      spec failure.

    A run fails only on two real short opinions, so borderline judge noise on a
    single requirement can't sink a complete run while a real omission still does.
    """
    reals: list[float] = []
    for attempt in (1, 2):
        # Clear prior eval output FIRST, so a failed/partial eval leaves no file
        # and _read_requirement_coverage returns None (inconclusive) — never a
        # stale value from an earlier eval misread as this run's fresh result.
        for fname in ("assessment.json", "evaluation.md", "findings.jsonl"):
            try:
                (run_dir / fname).unlink()
            except (FileNotFoundError, IsADirectoryError, TypeError):
                pass
        _run_auto_evaluation(run_dir, eval_config, visibility, force=True)
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


@main.command()
@click.argument("stack_id")
@click.option(
    "--from",
    "from_phase",
    type=click.Choice(["screening", "trial", "production"]),
    required=True,
    help="Current lifecycle phase of the stack.",
)
@click.option(
    "--to",
    "to_phase",
    type=click.Choice(["trial", "production", "retired"]),
    required=True,
    help="Target lifecycle phase.",
)
@click.option(
    "--evidence",
    type=str,
    default=None,
    help='JSON object of evidence metrics, e.g. \'{"p_value": 0.05}\'.',
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to workspace YAML config for gate thresholds.",
)
def promote(
    stack_id: str,
    from_phase: str,
    to_phase: str,
    evidence: str | None,
    config_path: str | None,
) -> None:
    """Evaluate a promotion gate and report whether a stack passes.

    Example::

        retort promote my-stack --from screening --to trial \\
            --evidence '{"p_value": 0.05}' --config workspace.yaml
    """
    from retort.config.schema import PromotionConfig
    from retort.promotion.gates import evaluate_gate

    # Determine the gate name from the transition.
    gate_name = f"{from_phase}_to_{to_phase}"
    valid_gates = {"screening_to_trial", "trial_to_production", "production_to_retired"}
    if gate_name not in valid_gates:
        raise click.ClickException(
            f"Invalid transition: {from_phase} → {to_phase}. "
            f"Valid transitions: screening→trial, trial→production, production→retired."
        )

    # Parse evidence.
    if evidence is None:
        evidence_dict: dict[str, float] = {}
    else:
        try:
            evidence_dict = json.loads(evidence)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in --evidence: {exc}") from exc

    # Load promotion config from workspace YAML or use defaults.
    if config_path is not None:
        try:
            import yaml
        except ImportError:
            raise click.ClickException(
                "pyyaml required for --config. Install with: pip install pyyaml"
            )
        with open(config_path) as f:
            data = yaml.safe_load(f)
        promo_data = data.get("promotion", {})
        promo_config = PromotionConfig(**promo_data)
    else:
        promo_config = PromotionConfig()

    result = evaluate_gate(gate_name, evidence_dict, promo_config)

    if result.passed:
        click.echo(f"PASS: {stack_id} may advance {from_phase} → {to_phase}")
    else:
        click.echo(f"FAIL: {stack_id} does not pass {from_phase} → {to_phase}")
    click.echo(f"  {result.detail}")


@main.group()
def report() -> None:
    """Analysis and reporting commands."""


@report.command("effects")
@click.option(
    "--db",
    type=click.Path(exists=True),
    required=True,
    help="Path to the retort SQLite database.",
)
@click.option(
    "--matrix-id",
    type=int,
    required=True,
    help="ID of the design matrix to analyze.",
)
@click.option(
    "--metric",
    type=str,
    required=True,
    help="Response metric name to compute effects for.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json", "csv", "html"]),
    default="text",
    help="Output format (default: text).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path. Defaults to stdout.",
)
def report_effects(
    db: str, matrix_id: int, metric: str, fmt: str, output: str | None
) -> None:
    """Compute and display main effects and interaction plots.

    Analyzes completed experiment runs for a design matrix, computing
    the mean response per level of each factor (main effects) and per
    level-pair of each factor combination (interaction effects).
    """
    from retort.reporting.effects import compute_effects
    from retort.reporting.export import to_csv, to_json, to_text
    from retort.storage.database import get_engine, get_session_factory

    engine = get_engine(Path(db))
    session_factory = get_session_factory(engine)
    session = session_factory()

    try:
        effects = compute_effects(session, matrix_id, metric)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None
    finally:
        session.close()
        engine.dispose()

    if fmt == "json":
        rendered = to_json(effects)
    elif fmt == "csv":
        rendered = to_csv(effects)
    elif fmt == "html":
        from retort.reporting.export import to_html

        rendered = to_html(effects)
    else:
        rendered = to_text(effects)

    if output:
        Path(output).write_text(rendered)
        click.echo(f"Report written to {output}")
    else:
        click.echo(rendered)


@report.command("dashboard")
@click.option(
    "--db",
    type=click.Path(exists=True),
    required=True,
    help="Path to the retort SQLite database.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path. Defaults to stdout.",
)
def report_dashboard(db: str, fmt: str, output: str | None) -> None:
    """Show full workspace status dashboard.

    Displays active experiments, lifecycle states, budget usage,
    and recent promotions in a single overview.
    """
    from retort.reporting.dashboard import build_dashboard, render_json, render_text
    from retort.storage.database import get_engine, get_session_factory

    engine = get_engine(Path(db))
    session_factory = get_session_factory(engine)
    session = session_factory()

    try:
        report_data = build_dashboard(session)
    finally:
        session.close()
        engine.dispose()

    if fmt == "json":
        rendered = render_json(report_data)
    else:
        rendered = render_text(report_data)

    if output:
        Path(output).write_text(rendered)
        click.echo(f"Dashboard written to {output}")
    else:
        click.echo(rendered)


@report.command("wardley")
@click.option(
    "--db",
    type=click.Path(exists=True),
    required=True,
    help="Path to the retort SQLite database.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path. Defaults to stdout.",
)
def report_wardley(db: str, fmt: str, output: str | None) -> None:
    """Show Wardley map overlay of stack evolution stages.

    Visualizes where each stack sits on the Wardley evolution axis
    (Genesis → Custom-Built → Product → Commodity) based on its
    current lifecycle phase.
    """
    from retort.reporting.wardley import build_wardley_map, render_json, render_text
    from retort.storage.database import get_engine, get_session_factory

    engine = get_engine(Path(db))
    session_factory = get_session_factory(engine)
    session = session_factory()

    try:
        report_data = build_wardley_map(session)
    finally:
        session.close()
        engine.dispose()

    if fmt == "json":
        rendered = render_json(report_data)
    else:
        rendered = render_text(report_data)

    if output:
        Path(output).write_text(rendered)
        click.echo(f"Wardley map written to {output}")
    else:
        click.echo(rendered)


@report.command("pareto")
@click.option(
    "--data",
    type=click.Path(exists=True),
    required=True,
    help="CSV file with factor + response columns (output of `retort export csv`).",
)
@click.option(
    "--metric",
    "metrics",
    multiple=True,
    required=True,
    help=(
        "Response metric(s) to optimize. Repeat for multi-objective. Prefix "
        "with '-' to minimize (e.g. -_cost_usd). Default direction: maximize."
    ),
)
@click.option(
    "--group-by",
    "group_by",
    multiple=True,
    default=("language", "model", "tooling"),
    show_default=True,
    help=(
        "Factor columns identifying a stack. Rows with the same group_by "
        "values are aggregated by mean before Pareto ranking."
    ),
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def report_pareto(
    data: str,
    metrics: tuple[str, ...],
    group_by: tuple[str, ...],
    fmt: str,
) -> None:
    """Compute Pareto-optimal stacks across multiple objectives.

    Identifies stacks that aren't dominated on any combination of the
    requested metrics. Useful when picking a stack involves trade-offs
    (high quality vs low cost vs fast). Cost-like metrics should be
    minimized — prefix with '-' to flip their direction.

    \b
    Example: highest quality at lowest cost across all stacks
        retort report pareto --data combined.csv \\
            --metric code_quality --metric -_cost_usd

    \b
    Multi-objective with all telemetry:
        retort report pareto --data combined.csv \\
            --metric code_quality --metric -_cost_usd \\
            --metric -_duration_seconds --metric -_tokens
    """
    import json as _json
    import pandas as pd

    from retort.analysis.pareto import pareto_analysis

    df = pd.read_csv(data)

    # Parse metric directions: '-name' = minimize → flip sign
    metric_specs = []
    for m in metrics:
        if m.startswith("-"):
            metric_specs.append((m[1:], -1.0))
        else:
            metric_specs.append((m, +1.0))

    missing = [m for m, _ in metric_specs if m not in df.columns]
    if missing:
        raise click.ClickException(f"Metrics not in data: {missing}")
    missing_g = [g for g in group_by if g not in df.columns]
    if missing_g:
        raise click.ClickException(f"Group_by columns not in data: {missing_g}")

    # Aggregate to one row per stack (mean of each metric)
    metric_cols = [m for m, _ in metric_specs]
    agg = df.groupby(list(group_by), dropna=False)[metric_cols].mean().reset_index()
    # Drop stacks with NaN in any metric (incomplete data)
    agg = agg.dropna(subset=metric_cols)
    if agg.empty:
        raise click.ClickException("No stacks have data for all requested metrics.")

    # Apply direction flips for minimization
    values = agg[metric_cols].to_numpy(dtype=float)
    signs = [s for _, s in metric_specs]
    for i, s in enumerate(signs):
        values[:, i] = values[:, i] * s

    labels = [
        " · ".join(f"{g}={agg.iloc[i][g]}" for g in group_by)
        for i in range(len(agg))
    ]
    result = pareto_analysis(labels, values, [m for m, _ in metric_specs])

    if fmt == "json":
        out = {
            "frontier": [
                {
                    "label": result.labels[i],
                    "rank": int(result.ranks[i]),
                    "values": {
                        m: float(agg.iloc[i][m])  # original-direction values
                        for m, _ in metric_specs
                    },
                }
                for i in range(len(result.labels))
            ],
            "metrics": [{"name": m, "minimize": s < 0} for m, s in metric_specs],
        }
        click.echo(_json.dumps(out, indent=2))
        return

    # Text rendering: rank-sorted with frontier highlighted
    click.echo(f"Pareto analysis on {len(agg)} stacks:")
    click.echo("Objectives:")
    for m, s in metric_specs:
        click.echo(f"  {'minimize' if s < 0 else 'maximize'} {m}")
    click.echo("")
    header = f"{'rank':>4}  " + "  ".join(f"{m:>14}" for m, _ in metric_specs) + "  stack"
    click.echo(header)
    click.echo("-" * (len(header) + 30))

    order = sorted(range(len(result.labels)), key=lambda i: (result.ranks[i], result.labels[i]))
    for i in order:
        marker = "★" if result.ranks[i] == 0 else " "
        vals = "  ".join(f"{agg.iloc[i][m]:>14.4f}" for m, _ in metric_specs)
        click.echo(f"{marker} {int(result.ranks[i]):>2}  {vals}  {result.labels[i]}")
    click.echo("")
    click.echo(f"Pareto frontier (★, rank 0): {int((result.ranks == 0).sum())} stack(s)")


@report.command("aliasing")
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=None,
    help="Path to workspace YAML config. If omitted, reads factors from stdin as JSON.",
)
@click.option(
    "--phase",
    type=click.Choice(["screening", "characterization"]),
    default="screening",
    show_default=True,
    help="Design phase (screening = Resolution III, characterization = Resolution IV).",
)
@click.option(
    "--max-order",
    type=int,
    default=3,
    show_default=True,
    help="Maximum interaction order to analyse (1=main only, 2=+2FI, 3=+3FI).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path. Defaults to stdout.",
)
def report_aliasing(
    config: str | None,
    phase: str,
    max_order: int,
    fmt: str,
    output: str | None,
) -> None:
    """Inspect the aliasing / confounding structure of a fractional factorial design.

    Shows which effects are aliased (confounded) with one another for
    a given set of factors and design resolution. This helps determine
    which effects can be independently estimated.

    Example::

        retort report aliasing --config workspace.yaml --phase screening
    """
    from retort.design.aliasing import compute_aliasing
    from retort.reporting.aliasing_report import render_json, render_text

    registry = _load_factors(config)

    if len(registry) < 2:
        click.echo("Error: need at least 2 factors for aliasing analysis.", err=True)
        sys.exit(1)

    report_data = compute_aliasing(registry, phase, max_order=max_order)

    if fmt == "json":
        rendered = render_json(report_data)
    else:
        rendered = render_text(report_data)

    if output:
        Path(output).write_text(rendered)
        click.echo(f"Aliasing report written to {output}")
    else:
        click.echo(rendered)


@main.command()
@click.option(
    "--factor",
    type=str,
    required=True,
    help="Name of the factor gaining a new level (e.g., 'agent').",
)
@click.option(
    "--level",
    type=str,
    required=True,
    help="New level value to add (e.g., 'new-agent-v1').",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="Path to workspace YAML config.",
)
@click.option(
    "--phase",
    type=click.Choice(["screening", "characterization"]),
    default="screening",
    show_default=True,
    help="Design phase for augmentation.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write augmentation rows to CSV file.",
)
@click.option(
    "--nrestarts",
    type=int,
    default=40,
    show_default=True,
    help="Number of optimizer restarts for D-optimal generation.",
)
def intake(
    factor: str,
    level: str,
    config_path: str,
    phase: str,
    output: str | None,
    nrestarts: int,
) -> None:
    """Ingest a new candidate (factor level) and generate augmentation runs.

    When a new candidate appears (e.g., a new AI agent ships), this command
    triggers D-optimal augmentation to extend the existing design matrix
    with the minimum new runs needed.

    Example::

        retort intake --factor agent --level "new-agent-v1"
    """
    from retort.scheduler.intake import intake_candidate, load_existing_design

    registry, existing_design = load_existing_design(config_path, phase)

    try:
        result = intake_candidate(
            factor_name=factor,
            new_level=level,
            registry=registry,
            existing_design=existing_design,
            nrestarts=nrestarts,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None
    except ImportError as exc:
        raise click.ClickException(str(exc)) from None

    click.echo(f"Intake: {factor}={level}")
    click.echo(f"  Stack ID:     {result.stack_id}")
    click.echo(f"  Lifecycle:    {result.lifecycle_state}")
    click.echo(f"  D-efficiency: {result.augmentation.d_efficiency:.6f}")
    click.echo(f"  New runs:     {result.num_new_runs}")
    click.echo(f"  Total design: {result.augmentation.full_design.num_runs} runs")

    if result.num_new_runs > 0:
        click.echo(f"\nAugmentation rows:")
        click.echo(result.new_rows.to_string(index=False))

    if output:
        result.new_rows.to_csv(output, index=False)
        click.echo(f"\nAugmentation rows written to {output}")


@main.command()
@click.option(
    "--data",
    type=click.Path(exists=True),
    required=True,
    help="CSV file with factor columns and response columns.",
)
@click.option(
    "--responses",
    "-r",
    multiple=True,
    required=True,
    help="Response column name(s) to analyse. Repeat for multiple.",
)
@click.option(
    "--factors",
    "-f",
    multiple=True,
    default=None,
    help="Factor column name(s). If omitted, all non-response columns are used.",
)
@click.option(
    "--interactions/--no-interactions",
    default=False,
    help="Include two-factor interactions in the model.",
)
@click.option(
    "--significance",
    type=float,
    default=0.10,
    show_default=True,
    help="P-value threshold for significance.",
)
@click.option(
    "--residuals/--no-residuals",
    "show_residuals",
    default=False,
    help="Run residual diagnostics on each model.",
)
@click.option(
    "--transform",
    type=click.Choice(["log", "none"]),
    default="log",
    show_default=True,
    help=(
        "Response transform before fitting. 'log' (default) fits a "
        "multiplicative model — the typical shape for tokens, cost, "
        "duration, error counts. Use 'none' for an additive/classical "
        "ANOVA when you have a real reason."
    ),
)
@click.option(
    "--predict/--no-predict",
    default=False,
    help=(
        "Predict response values + 95% CI for unmeasured factor combinations. "
        "Useful for fractional designs where most cells weren't run."
    ),
)
def analyze(
    data: str,
    responses: tuple[str, ...],
    factors: tuple[str, ...],
    interactions: bool,
    significance: float,
    show_residuals: bool,
    transform: str,
    predict: bool,
) -> None:
    """Analyse experimental results using ANOVA.

    Reads a CSV of experiment data and runs Type II ANOVA for each response
    metric, reporting which factors have statistically significant effects.
    Defaults to log-transformed responses (multiplicative model).
    """
    import pandas as pd

    df = pd.read_csv(data)

    factor_list = list(factors) if factors else None
    response_list = list(responses)

    missing = [r for r in response_list if r not in df.columns]
    if missing:
        click.echo(f"Error: response columns not found in data: {missing}", err=True)
        sys.exit(1)

    results = run_all_responses(
        df,
        responses=response_list,
        factors=factor_list,
        include_interactions=interactions,
        significance=significance,
        transform=transform,
    )

    for resp_name, result in results.items():
        click.echo(f"\n{'='*60}")
        click.echo(f"Response: {resp_name}    transform: {result.transform}")
        click.echo(f"R² = {result.r_squared:.4f}  Adj R² = {result.adj_r_squared:.4f}")
        click.echo(f"{'='*60}")
        click.echo(result.anova_table.to_string())
        if result.significant_factors:
            click.echo(
                f"\nSignificant (p < {significance}): "
                + ", ".join(result.significant_factors)
            )
        else:
            click.echo(f"\nNo factors significant at p < {significance}")

        if show_residuals:
            diag = check_residuals(result.model, resp_name)
            click.echo(f"\n{diag.summary()}")

        if predict:
            from retort.analysis.predict import predict_unmeasured, render_predictions
            preds = predict_unmeasured(result, df, factor_list)
            click.echo(f"\n--- Predictions for unmeasured cells ---")
            click.echo(render_predictions(preds, transform=result.transform))


@main.group()
def plugin() -> None:
    """Plugin management commands."""


@plugin.command("list")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
def plugin_list(fmt: str) -> None:
    """List installed retort plugins and their contributions."""
    from retort.plugins import get_plugin_manager, discover_scorers, discover_runners

    pm = get_plugin_manager()
    scorers = discover_scorers(pm)
    runners = discover_runners(pm)

    if fmt == "json":
        data = {
            "scorers": [s.name for s in scorers],
            "runners": list(runners.keys()),
        }
        click.echo(json.dumps(data, indent=2))
        return

    # Text format
    click.echo("Scorers:")
    if scorers:
        for s in scorers:
            click.echo(f"  {s.name} (plugin)")
    else:
        click.echo("  (no plugin scorers)")

    click.echo("\nRunners:")
    if runners:
        for name in sorted(runners.keys()):
            click.echo(f"  {name} (plugin)")
    else:
        click.echo("  (no plugin runners)")

    # Show built-in counts
    from retort.scoring.registry import create_default_registry
    from retort.playpen.runner import create_default_runner_registry

    scorer_reg = create_default_registry()
    runner_reg = create_default_runner_registry()

    click.echo(f"\nTotal scorers: {len(scorer_reg)} ({len(scorers)} from plugins)")
    click.echo(f"Total runners: {len(runner_reg)} ({len(runners)} from plugins)")


@plugin.command("show")
@click.argument("name")
def plugin_show(name: str) -> None:
    """Show details for a specific scorer or runner.

    NAME is a scorer or runner name (e.g. 'build_time' or 'docker').
    """
    from retort.scoring.registry import create_default_registry
    from retort.playpen.runner import create_default_runner_registry

    scorer_reg = create_default_registry()
    runner_reg = create_default_runner_registry()

    if name in scorer_reg:
        scorer = scorer_reg.get(name)
        click.echo(f"Scorer: {scorer.name}")
        click.echo(f"  Type:   {type(scorer).__qualname__}")
        click.echo(f"  Module: {type(scorer).__module__}")
        doc = type(scorer).__doc__
        if doc:
            click.echo(f"  Description: {doc.strip().splitlines()[0]}")
        return

    if name in runner_reg:
        runner = runner_reg.get(name)
        click.echo(f"Runner: {name}")
        click.echo(f"  Type:   {type(runner).__qualname__}")
        click.echo(f"  Module: {type(runner).__module__}")
        doc = type(runner).__doc__
        if doc:
            click.echo(f"  Description: {doc.strip().splitlines()[0]}")
        return

    raise click.ClickException(
        f"No scorer or runner named {name!r}. "
        f"Available scorers: {scorer_reg.available()}, "
        f"runners: {runner_reg.available()}"
    )


@main.group()
def export() -> None:
    """Export experiment data for downstream analysis."""


@export.command("csv")
@click.option(
    "--db",
    type=click.Path(exists=True),
    required=True,
    help="Path to the retort SQLite database.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output CSV path. Defaults to stdout.",
)
@click.option(
    "--include-failed",
    is_flag=True,
    default=False,
    help="Include failed runs (with NaN scores) in the export.",
)
def export_csv(db: str, output: str | None, include_failed: bool) -> None:
    """Export experiment_runs + run_results to a flat CSV.

    Joins the per-run factor configuration (parsed from run_config_json) with
    each metric's score, producing the wide-format CSV that ``retort analyze``
    consumes. Useful when the design matrix wasn't persisted at run time
    (older runs) or when you want to feed the data into another tool.
    """
    import csv as _csv
    import io
    import sys

    from retort.storage.database import get_engine, get_session_factory
    from retort.storage.models import ExperimentRun, RunResult, RunStatus

    engine = get_engine(Path(db))
    session_factory = get_session_factory(engine)
    session = session_factory()

    try:
        runs_query = session.query(ExperimentRun)
        if not include_failed:
            runs_query = runs_query.filter(ExperimentRun.status == RunStatus.completed)
        runs = runs_query.all()
        if not runs:
            raise click.ClickException("No runs to export.")

        # Collect factor names + metric names across all runs.
        factor_names: set[str] = set()
        metric_names: set[str] = set()
        rows: list[dict[str, str | float | int]] = []

        # Pre-load all results to avoid N+1.
        all_results = session.query(RunResult).all()
        results_by_run: dict[int, list[RunResult]] = {}
        for r in all_results:
            results_by_run.setdefault(r.run_id, []).append(r)

        for run in runs:
            try:
                cfg = json.loads(run.run_config_json or "{}")
            except (TypeError, ValueError):
                cfg = {}
            row: dict[str, str | float | int] = {
                "run_id": run.id,
                "replicate": run.replicate,
                "status": run.status.value if hasattr(run.status, "value") else str(run.status),
            }
            for k, v in cfg.items():
                row[k] = v
                factor_names.add(k)
            for res in results_by_run.get(run.id, []):
                row[res.metric_name] = res.value
                metric_names.add(res.metric_name)
            rows.append(row)

        # Stable column order: meta, then factors (sorted), then metrics (sorted).
        columns = (
            ["run_id", "replicate", "status"]
            + sorted(factor_names)
            + sorted(metric_names)
        )

        buf = io.StringIO()
        writer = _csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

        rendered = buf.getvalue()
    finally:
        session.close()
        engine.dispose()

    if output:
        Path(output).write_text(rendered)
        click.echo(f"Wrote {len(rows)} rows to {output}", err=True)
    else:
        sys.stdout.write(rendered)


@export.command("merge")
@click.argument("inputs", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output CSV path. Defaults to stdout.",
)
@click.option(
    "--tag-column",
    type=str,
    default="experiment",
    show_default=True,
    help="Name of the column added to distinguish rows by source.",
)
def export_merge(inputs: tuple[str, ...], output: str | None, tag_column: str) -> None:
    """Combine multiple per-experiment CSVs into one wide CSV.

    Each input is supplied as ``label=path/to/runs.csv``. The label is
    written into a new column named by ``--tag-column`` (default
    ``experiment``). All input columns are unioned; missing columns
    fill with empty strings. Suitable for cross-experiment ANOVA.

    Example (combine experiment-1 + experiment-2 for a task-factored
    ANOVA):

    \b
        retort export merge \\
            rest-api-crud=experiment-1/reports/runs.csv \\
            brazil-bench=experiment-2/reports/runs.csv \\
            --tag-column task -o combined.csv

        retort analyze --data combined.csv -r code_quality \\
            -f language -f model -f tooling -f task --interactions
    """
    import csv as _csv
    import io
    import sys

    parsed: list[tuple[str, Path]] = []
    for spec in inputs:
        if "=" not in spec:
            raise click.ClickException(
                f"Each input must be label=path, got {spec!r}. "
                "Example: rest-api-crud=experiment-1/reports/runs.csv"
            )
        label, _, path_str = spec.partition("=")
        path = Path(path_str)
        if not path.exists():
            raise click.ClickException(f"Input not found: {path}")
        parsed.append((label, path))

    # First pass: collect the union of all columns.
    all_columns: list[str] = [tag_column]
    seen_columns: set[str] = {tag_column}
    rows_by_label: list[tuple[str, list[dict[str, str]]]] = []
    for label, path in parsed:
        with path.open() as f:
            reader = _csv.DictReader(f)
            file_rows = list(reader)
            rows_by_label.append((label, file_rows))
            for col in reader.fieldnames or []:
                if col not in seen_columns:
                    all_columns.append(col)
                    seen_columns.add(col)

    buf = io.StringIO()
    writer = _csv.DictWriter(buf, fieldnames=all_columns, extrasaction="ignore")
    writer.writeheader()
    total = 0
    for label, file_rows in rows_by_label:
        for row in file_rows:
            row[tag_column] = label
            writer.writerow(row)
            total += 1

    rendered = buf.getvalue()
    if output:
        Path(output).write_text(rendered)
        click.echo(
            f"Merged {len(parsed)} input(s), {total} row(s), {len(all_columns)} column(s) -> {output}",
            err=True,
        )
    else:
        sys.stdout.write(rendered)


@main.group()
def tasks() -> None:
    """Task registry commands (the task sources retort can run)."""


@tasks.command("list")
@click.option(
    "--format", "fmt", type=click.Choice(["text", "json"]),
    default="text", show_default=True,
)
def tasks_list(fmt: str) -> None:
    """List registered tasks and their canonical source URIs.

    Bundled tasks live in this repo (``bundled://``); others load from a GitHub
    or git repo (``github://``). Reference a task by bare name (``--task
    brazil-bench`` / ``source: brazil-bench``) or by explicit URI.
    """
    from retort.playpen.task_loader import list_registered_tasks

    rows = list_registered_tasks()
    if not rows:
        raise click.ClickException("No tasks registered (tasks/registry.yaml missing or empty).")

    if fmt == "json":
        click.echo(json.dumps(
            [
                {
                    "name": t.name,
                    "source": t.source,
                    "kind": t.kind,
                    "description": t.description,
                }
                for t in rows
            ],
            indent=2,
        ))
        return

    name_w = max([len(t.name) for t in rows] + [len("NAME")])
    src_w = max([len(t.source) for t in rows] + [len("SOURCE")])
    click.echo(f"{'NAME':<{name_w}}  {'SOURCE':<{src_w}}  TYPE")
    for t in rows:
        click.echo(f"{t.name:<{name_w}}  {t.source:<{src_w}}  {t.kind}")


@tasks.command("show")
@click.argument("name")
def tasks_show(name: str) -> None:
    """Show a registered task's resolved source, fallback, and description."""
    from retort.playpen.task_loader import list_registered_tasks, resolve_task_source

    for t in list_registered_tasks():
        if t.name == name:
            click.echo(f"name:        {t.name}")
            click.echo(f"source:      {t.source}")
            click.echo(f"type:        {t.kind}")
            if t.description:
                click.echo(f"description: {t.description}")
            return
    # Not registered — still resolve so explicit URIs / bundled dirs work.
    try:
        click.echo(f"resolves to: {resolve_task_source(name)}")
    except ValueError as exc:
        raise click.ClickException(str(exc))


@main.command("aggregate")
@click.option(
    "--experiments-dir", "experiments_dir",
    type=click.Path(exists=True, file_okay=False), default=".",
    show_default=True,
    help="Directory containing experiment-*/ subdirs.",
)
@click.option(
    "--out", "out_path", type=click.Path(), default="master.db",
    show_default=True, help="Master SQLite DB to (re)build.",
)
@click.option(
    "--csv", "csv_path", type=click.Path(), default=None,
    help="Also write the wide table as CSV to this path.",
)
def aggregate(experiments_dir: str, out_path: str, csv_path: str | None) -> None:
    """Combine every experiment's retort.db into one master results table.

    Builds a single wide, tidy `runs` table (one row per run, tagged with
    experiment + task, a column per metric) across all experiment-*/retort.db,
    so cross-experiment analysis works as the program grows. Rebuilt from
    scratch each run — re-run it after a re-evaluation pass to pick up new
    metrics like requirement_coverage.
    """
    from retort.analysis.aggregate import build_master_db, write_csv

    root = Path(experiments_dir)
    n = build_master_db(root, Path(out_path))
    click.echo(f"Aggregated {n} runs from {root}/experiment-*/retort.db -> {out_path}")
    if csv_path:
        write_csv(root, Path(csv_path))
        click.echo(f"Wrote CSV -> {csv_path}")


@main.command("maturity")
@click.option(
    "--db",
    type=click.Path(exists=True),
    required=True,
    help="Path to the retort SQLite database.",
)
@click.option(
    "--metric",
    type=str,
    default="code_quality",
    show_default=True,
    help="Headline metric whose level/variance dominates score components.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path. Defaults to stdout.",
)
@click.option(
    "--stack",
    type=str,
    default=None,
    help="Filter to a specific stack signature (sorted-json) or substring.",
)
def maturity(db: str, metric: str, fmt: str, output: str | None, stack: str | None) -> None:
    """Score each stack's maturity from the run database.

    A *stack* is a unique factor combination. Maturity is a composite of
    replicate agreement, completion rate, headline-metric level, and
    replicate coverage. Use to find candidates for promotion to the next
    lifecycle phase (see retort promote).
    """
    from retort.analysis.maturity import (
        compute_stack_maturity, render_json, render_text,
    )
    from retort.storage.database import get_engine, get_session_factory

    engine = get_engine(Path(db))
    session = get_session_factory(engine)()
    try:
        report = compute_stack_maturity(session, headline_metric=metric)
    finally:
        session.close()
        engine.dispose()

    if stack:
        # Match against either the raw signature (sorted-json) or the
        # human-friendly "factor=value" representation.
        def _matches(r):
            human = ", ".join(f"{k}={v}" for k, v in r.factors.items())
            return stack in r.stack_signature or stack in human
        report = [r for r in report if _matches(r)]

    if not report:
        raise click.ClickException(
            "No stacks matched. Check --db points at a populated retort.db, "
            "and that --stack filter (if any) matches an actual signature."
        )

    rendered = render_json(report) if fmt == "json" else render_text(report)
    if output:
        Path(output).write_text(rendered)
        click.echo(f"Wrote maturity report ({len(report)} stacks) to {output}", err=True)
    else:
        click.echo(rendered)


@main.command("evaluate")
@click.argument("run_dirs", nargs=-1, type=click.Path(exists=True, file_okay=False))
@click.option(
    "--experiment-dir",
    "experiment_dir",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Evaluate all runs in <EXPERIMENT_DIR>/runs/.",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="Path to workspace YAML config (for model + tracker settings).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-run evaluation even if evaluation.md is up-to-date.",
)
@click.option(
    "--workers",
    default=4,
    show_default=True,
    type=int,
    help="Parallel evaluation workers.",
)
def evaluate(
    run_dirs: tuple[str, ...],
    experiment_dir: str | None,
    config: str,
    force: bool,
    workers: int,
) -> None:
    """Evaluate run archives via the evaluate-run skill.

    Pass one or more RUN_DIRS, or use --experiment-dir to bulk-evaluate
    all runs in <EXPERIMENT_DIR>/runs/.  Use --force to re-run evaluations
    whose evaluation.md is already up-to-date.

    Use this for manual or retroactive evaluation of runs that predate
    auto-evaluation, or to re-evaluate after updating the skill.
    """
    import concurrent.futures
    from retort.config.loader import load_workspace

    if experiment_dir and run_dirs:
        raise click.UsageError("Pass either RUN_DIRS or --experiment-dir, not both.")
    if not experiment_dir and not run_dirs:
        raise click.UsageError("Provide at least one RUN_DIR or use --experiment-dir.")

    workspace_config = load_workspace(config)
    eval_cfg = workspace_config.evaluation
    if not eval_cfg.enabled:
        click.echo("evaluation.enabled=false in config, but running on manual request.")

    targets: list[Path]
    if experiment_dir:
        runs_root = Path(experiment_dir) / "runs"
        if not runs_root.is_dir():
            raise click.ClickException(f"No runs/ directory found in {experiment_dir}")
        # Cell dirs nest under runs/ (deeper when a model id contains '/'), and
        # each holds rep dirs with the actual code. _iter_archive_cells finds the
        # leaf cell dirs regardless of depth; a rep dir's name starts with "rep".
        targets = sorted(
            rep
            for _cell_name, cell in _iter_archive_cells(runs_root)
            for rep in cell.iterdir() if rep.is_dir() and rep.name.startswith("rep")
        )
        if not targets:
            raise click.ClickException(f"No rep directories found under {runs_root}")
        click.echo(f"Evaluating {len(targets)} run(s) in {runs_root} with {workers} workers", err=True)
    else:
        targets = [Path(d) for d in run_dirs]

    visibility = workspace_config.experiment.visibility

    def _eval_one(run_dir: Path) -> None:
        _run_auto_evaluation(run_dir, eval_cfg, visibility, force=force)

    if workers <= 1 or len(targets) == 1:
        for t in targets:
            _eval_one(t)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_eval_one, t): t for t in targets}
            for fut in concurrent.futures.as_completed(futures):
                exc = fut.exception()
                if exc:
                    click.echo(f"  (worker error for {futures[fut].name}: {exc})", err=True)


@main.command("reevaluate")
@click.option(
    "--experiment-dir", "experiment_dir", required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Experiment dir (uses its runs/ archives and retort.db).",
)
@click.option(
    "--config", type=click.Path(exists=True), default=None,
    help="Workspace YAML (defaults to <experiment-dir>/workspace.yaml).",
)
@click.option(
    "--eval-model", default="", show_default="latest (no --model passed)",
    help="Judge model for the second-opinion spec eval. Default: unset — the "
         "claude CLI picks its most recent model, so this tracks new releases "
         "automatically. Pass an explicit id to pin one.",
)
@click.option("--workers", default=2, show_default=True, type=int)
@click.option("--languages", help="Comma-separated language filter (default: all).")
@click.option(
    "--force", is_flag=True,
    help="Re-evaluate runs that already have requirement_coverage.",
)
def reevaluate(experiment_dir, config, eval_model, workers, languages, force):
    """Re-evaluate archived runs with the second-opinion spec eval, persisting
    requirement_coverage into the experiment's retort.db.

    Non-destructive: adds/updates the requirement_coverage metric only — run
    status is left unchanged (apply the conformance gate separately if you want
    to reclassify). Resumable: skips runs that already have a coverage value
    unless --force. Use after `retort aggregate` to refresh the master DB.
    """
    import concurrent.futures
    import re
    from retort.config.loader import load_workspace

    exp = Path(experiment_dir)
    db_path = exp / "retort.db"
    if not db_path.exists():
        raise click.ClickException(f"No retort.db in {experiment_dir}")
    cfg_path = config or (exp / "workspace.yaml")
    workspace_config = load_workspace(str(cfg_path))
    eval_cfg = workspace_config.evaluation.model_copy(
        update={"enabled": True, "model": eval_model}
    )
    visibility = workspace_config.experiment.visibility

    runs_root = exp / "runs"

    # Preflight: confirm the eval tooling actually works before spending a batch,
    # so a broken judge / missing skill fails loudly instead of silently
    # persisting nothing and reporting success.
    ok, msg = _eval_tooling_preflight(eval_model, runs_root)
    if not ok:
        raise click.ClickException(
            f"Eval tooling preflight FAILED: {msg}. "
            "Fix the judge model/skill before re-evaluating (nothing was changed)."
        )
    click.echo(f"Eval preflight OK — {msg}")

    reps = sorted(
        rep
        for _cell_name, cell in _iter_archive_cells(runs_root)
        for rep in cell.iterdir()
        if rep.is_dir() and rep.name.startswith("rep") and not rep.name.endswith("-failed")
    )
    lang_filter = {s.strip() for s in languages.split(",")} if languages else None
    work = []
    skipped = 0
    orphaned: list[str] = []   # archives whose factors match NO db row
    incomplete = 0             # real row, but not completed (legit skip)
    already = 0                # already has coverage (legit skip)
    for rep in reps:
        # The cell dir name (language=X_model=Y[_prompt=Z…]) is the
        # authoritative factor source and matches what's stored in
        # run_config_json. Use the path relative to runs_root, not just
        # rep.parent.name, so a model id with '/' (which nests the cell) is
        # reconstructed whole. Older experiments' stack.json omit `model`, so
        # deriving factors from stack.json silently fails to match the DB row.
        run_config = _run_config_from_cell_name(str(rep.parent.relative_to(runs_root)))
        if not run_config:
            sj = rep / "stack.json"
            if not sj.exists():
                continue
            try:
                cfg = json.loads(sj.read_text())
            except (ValueError, OSError):
                # A malformed/empty stack.json must not kill the whole batch.
                skipped += 1
                click.echo(f"  (skipping {rep.parent.name}/{rep.name}: unreadable stack.json)", err=True)
                continue
            run_config = {k: cfg.get(k) for k in ("language", "model", "tooling")
                          if cfg.get(k) is not None}
        if lang_filter and run_config.get("language") not in lang_filter:
            continue
        m = re.search(r"rep(\d+)", rep.name)
        replicate = int(m.group(1)) if m else 1
        if not _run_completed_exists(db_path, run_config, replicate):
            # No completed DB row to attach coverage to. Distinguish a genuinely
            # incomplete run (a failed/running row exists) from an ORPHAN whose
            # factors match nothing — the latter means cell parsing/matching is
            # broken and the eval is silently skipping real runs.
            if _run_row_exists(db_path, run_config, replicate):
                incomplete += 1
            else:
                orphaned.append(f"{rep.parent.name}/{rep.name}")
            continue
        if not force and _run_has_requirement_coverage(db_path, run_config, replicate):
            already += 1
            continue
        work.append((rep, run_config, replicate))

    click.echo(
        f"Re-evaluating {len(work)} run(s) in {experiment_dir} "
        f"(judge={eval_model}, {workers} workers, second-opinion)"
    )

    def _eval(item):
        rep, run_config, replicate = item
        passed, cov = _spec_conformance_passes(rep, eval_cfg, visibility)
        return (rep, run_config, replicate, passed, cov)

    # Persist each result the moment its eval finishes (in the main thread, so
    # the DB write is serial/safe), rather than batching at the end. The covered
    # count then climbs run-by-run, and a mid-pass crash keeps what was done.
    counts = {"persisted": 0, "inconclusive": 0, "done": 0}

    def _handle(result):
        rep, run_config, replicate, verdict, cov = result
        counts["done"] += 1
        label = f"{rep.parent.name}/{rep.name}"
        if verdict is None:
            # Eval couldn't run (usage limit / timeout). Don't persist — leave
            # the run uncovered so a later resume re-evaluates it cleanly.
            counts["inconclusive"] += 1
            click.echo(f"  {label}: inconclusive (eval didn't run) — retry later")
            return
        if _persist_requirement_coverage(db_path, run_config, replicate, cov):
            counts["persisted"] += 1
        click.echo(f"  {label}: ReqCov={cov} [{'PASS' if verdict else 'fail'}]")

    if workers <= 1:
        for w in work:
            _handle(_eval(w))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for fut in concurrent.futures.as_completed([pool.submit(_eval, w) for w in work]):
                exc = fut.exception()
                if exc:
                    click.echo(f"  (worker error: {exc})", err=True)
                else:
                    _handle(fut.result())

    persisted, inconclusive = counts["persisted"], counts["inconclusive"]
    # Fold any WAL back into the .db so readers (aggregate) + git see a clean file.
    import sqlite3
    cx = sqlite3.connect(db_path)
    cx.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cx.close()
    msg = f"Persisted requirement_coverage for {persisted}/{counts['done']} runs."
    if inconclusive:
        msg += f" {inconclusive} inconclusive (usage limit/timeout) — re-run to finish."
    click.echo(msg)

    # Health verdict: surface when the eval tooling silently did little/nothing,
    # rather than reporting success on an empty pass.
    click.echo(
        f"Eval health: {len(reps)} archived runs | matched {len(work) + already + incomplete} "
        f"(evaluated {len(work)}, already-covered {already}, incomplete {incomplete}) "
        f"| orphaned {len(orphaned)}"
    )
    problems = []
    if orphaned:
        ex = ", ".join(orphaned[:3]) + ("…" if len(orphaned) > 3 else "")
        problems.append(
            f"{len(orphaned)} archived run(s) matched NO database row — cell-name "
            f"parsing / factor matching is broken, real runs were skipped (e.g. {ex})"
        )
    if work and persisted == 0:
        problems.append(
            f"evaluated {len(work)} run(s) but persisted 0 coverage values — the "
            f"judge tooling produced nothing usable"
        )
    elif work and inconclusive == len(work):
        problems.append(
            f"all {len(work)} evals were inconclusive (the judge never ran)"
        )
    if problems:
        for p in problems:
            click.echo(f"  ✗ EVAL TOOLING PROBLEM: {p}", err=True)
        raise click.ClickException(
            "Eval tooling did not work correctly — see the problems above. "
            "requirement_coverage is unreliable until they are fixed."
        )


@main.command("rescore")
@click.option("--experiment-dir", "experiment_dir", required=True,
              type=click.Path(exists=True, file_okay=False),
              help="Experiment directory containing retort.db and runs/.")
@click.option("--config", type=click.Path(exists=True, dir_okay=False),
              help="Workspace YAML (defaults to <experiment-dir>/workspace.yaml).")
@click.option("--languages", help="Comma-separated language filter (default: all).")
@click.option("--only-failed", is_flag=True,
              help="Only re-score runs currently marked failed.")
@click.option("--metrics", "metrics_only",
              help="Re-score ONLY these metrics (comma-separated), computed "
                   "directly without the test-coverage gate and leaving status "
                   "unchanged. Use to fix a non-gating scorer gap (e.g. "
                   "maintainability) on already-passing runs whose trimmed "
                   "archives can no longer rebuild.")
@click.option("--workers", default=4, show_default=True, type=int)
@click.option("--dry-run", is_flag=True, help="Report changes without writing.")
def rescore(experiment_dir, config, languages, only_failed, metrics_only, workers, dry_run):
    """Re-score archived runs with the current scorers (DB + scores.json).

    Use after fixing or upgrading a scorer: re-runs the mechanical metrics
    against each archived run and writes the corrected values to retort.db
    (preserving the ``_``-prefixed telemetry and requirement_coverage) AND to the
    archive's ``scores.json`` (which the spec eval reads — keeping them in sync).
    Reclassifies status via the conformance gate: a run whose tests now execute
    (test_coverage > 0) becomes ``completed``. Run ``retort reevaluate`` afterward
    to refresh requirement_coverage, then ``retort aggregate``. Idempotent.

    With ``--metrics``, only the named metrics are recomputed (directly, no gate)
    and status is left untouched — the right tool when a passing run's archive
    was trimmed and can't rebuild, but a static metric (maintainability) needs a
    corrected value.
    """
    import concurrent.futures
    import re
    import sqlite3
    from retort.config.loader import load_workspace
    from retort.playpen.runner import RunArtifacts, StackConfig
    from retort.scoring.collector import ScoreCollector
    from retort.scoring.registry import create_default_registry

    subset = [s.strip() for s in metrics_only.split(",")] if metrics_only else None
    _registry = create_default_registry() if subset else None

    exp = Path(experiment_dir)
    db_path = exp / "retort.db"
    if not db_path.exists():
        raise click.ClickException(f"No retort.db in {experiment_dir}")
    cfg_path = config or (exp / "workspace.yaml")
    workspace_config = load_workspace(str(cfg_path))
    metrics = subset if subset else [r.name for r in workspace_config.responses]
    collector = None if subset else ScoreCollector(metrics=metrics)
    lang_filter = {s.strip() for s in languages.split(",")} if languages else None

    def _telemetry(run_config, replicate):
        where, params = _factor_match_sql(run_config)
        con = sqlite3.connect(db_path)
        row = con.execute(
            f"SELECT id, status FROM experiment_runs WHERE replicate=? AND {where} "
            "ORDER BY finished_at DESC", (replicate, *params)).fetchone()
        tele = {}
        if row:
            tele = dict(con.execute(
                "SELECT metric_name, value FROM run_results WHERE run_id=? "
                "AND metric_name LIKE '\\_%' ESCAPE '\\'", (row[0],)).fetchall())
        con.close()
        return (row[1] if row else None), tele

    runs_root = exp / "runs"
    work = []
    for cell_name, cell in sorted(_iter_archive_cells(runs_root)):
        run_config = _run_config_from_cell_name(cell_name)
        if not run_config:
            continue
        if lang_filter and run_config.get("language") not in lang_filter:
            continue
        for rep in sorted(cell.iterdir()):
            if not rep.is_dir() or not rep.name.startswith("rep") or rep.name.endswith("-failed"):
                continue
            m = re.search(r"rep(\d+)", rep.name)
            replicate = int(m.group(1)) if m else 1
            status, tele = _telemetry(run_config, replicate)
            if status is None:
                continue
            if only_failed and status != "failed":
                continue
            work.append((rep, run_config, replicate, tele))

    click.echo(f"Re-scoring {len(work)} run(s) in {experiment_dir} "
               f"(metrics={','.join(metrics)}, {workers} workers"
               f"{', dry-run' if dry_run else ''})")

    def _score(item):
        rep, run_config, replicate, tele = item
        stack = StackConfig(
            language=run_config["language"], agent=run_config.get("agent", "unknown"),
            framework=run_config.get("framework", "none"),
            extra={"tooling": run_config["tooling"]} if "tooling" in run_config else {})
        artifacts = RunArtifacts(
            output_dir=rep, stdout="", stderr="", exit_code=0,
            duration_seconds=tele.get("_duration_seconds", 0.0),
            token_count=int(tele.get("_tokens", 0) or 0), metadata={})
        if subset:
            # Direct per-scorer computation — no test-coverage gate, so a static
            # metric still gets a real value on an archive that can't rebuild.
            scores = {}
            for m in subset:
                if m in _registry:
                    try:
                        scores[m] = _registry.get(m).score(artifacts, stack)
                    except Exception:
                        scores[m] = 0.0
        else:
            scores = {s.metric_name: s.value for s in collector.collect(artifacts, stack).scores}
        return (rep, run_config, replicate, scores)

    counts = {"updated": 0, "recovered": 0, "done": 0}

    def _handle(result):
        rep, run_config, replicate, scores = result
        counts["done"] += 1
        tc = scores.get("test_coverage")
        label = f"{rep.parent.name}/{rep.name}"
        if dry_run:
            click.echo(f"  [dry] {label}: " + " ".join(f"{k}={v:.2f}" for k, v in scores.items()))
            return
        if subset:
            # Update only the named metrics; leave status and other metrics alone.
            _persist_metric_values(db_path, run_config, replicate, scores)
            try:
                sj = rep / "scores.json"
                existing = json.loads(sj.read_text()) if sj.exists() else {}
                existing.update(scores)
                sj.write_text(json.dumps(existing))
            except (OSError, ValueError):
                pass
            counts["updated"] += 1
            click.echo(f"  {label}: " + " ".join(f"{k}={v:.2f}" for k, v in scores.items())
                       + " (metrics-only)")
            return
        new_status = _persist_rescore(db_path, run_config, replicate, scores)
        try:
            (rep / "scores.json").write_text(json.dumps(scores))
        except OSError:
            pass
        if new_status == "completed":
            counts["updated"] += 1
        gate = "" if tc is None else (" RECOVERED" if tc > 0 else " still-fails-gate")
        click.echo(f"  {label}: " + " ".join(f"{k}={v:.2f}" for k, v in scores.items())
                   + f" -> {new_status}{gate}")

    if workers <= 1:
        for w in work:
            _handle(_score(w))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for fut in concurrent.futures.as_completed([pool.submit(_score, w) for w in work]):
                exc = fut.exception()
                if exc:
                    click.echo(f"  (worker error: {exc})", err=True)
                else:
                    _handle(fut.result())

    if not dry_run:
        cx = sqlite3.connect(db_path)
        cx.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        cx.close()
    click.echo(f"Re-scored {counts['done']} run(s); {counts['updated']} now completed. "
               f"Run `retort reevaluate` then `retort aggregate` to refresh.")


@main.command("diagnose")
@click.option("--experiment-dir", "experiment_dir", required=True,
              type=click.Path(exists=True, file_okay=False),
              help="Experiment directory containing retort.db and runs/.")
@click.option("--as-json", "as_json", is_flag=True,
              help="Emit JSON instead of the text report.")
def diagnose(experiment_dir, as_json):
    """Deep-analyse every FAILED run and classify it TOOLING vs GENUINE.

    Read-only, so you never have to hand-investigate a failure again. For each
    failed run it RE-TESTS the archived code with the current scorers and probes
    the test command:

    \b
    * TOOLING — the code actually builds and its tests pass; the gate failed it
      on a scoring artefact (e.g. coverage measured 0 on passing tests). These
      recover with `retort rescore --only-failed`.
    * GENUINE — the tests genuinely don't run / don't pass, or the spec isn't
      met (requirement_coverage < 1). The specific cause is reported.

    Note: re-testing python archives installs their deps, so a large failure set
    can take a few minutes.
    """
    import json as _json
    import sqlite3

    from retort.playpen.runner import RunArtifacts, StackConfig
    from retort.scoring.scorers.test_coverage import TestCoverageScorer

    exp = Path(experiment_dir)
    db_path = exp / "retort.db"
    if not db_path.exists():
        raise click.ClickException(f"No retort.db in {experiment_dir}")
    runs_root = exp / "runs"
    scorer = TestCoverageScorer()
    con = sqlite3.connect(db_path)
    failed = con.execute(
        "SELECT id, run_config_json, replicate, error_message FROM experiment_runs "
        "WHERE status IN ('failed','crashed') ORDER BY run_config_json, replicate").fetchall()

    def _metric(run_id, name):
        r = con.execute(
            "SELECT value FROM run_results WHERE run_id=? AND metric_name=?",
            (run_id, name)).fetchone()
        return r[0] if r else None

    findings = []
    for run_id, rc_json, rep, err in failed:
        rc = _json.loads(rc_json)
        cell = "_".join(f"{k}={v}" for k, v in sorted(rc.items()))
        label = f"{cell}/rep{rep}"
        # A failed run is archived as repN-failed when one exists; otherwise the
        # gate-failed-but-code-present runs keep the plain repN dir.
        rep_dir = runs_root / cell / f"rep{rep}-failed"
        if not rep_dir.is_dir():
            rep_dir = runs_root / cell / f"rep{rep}"
        req_cov = _metric(run_id, "requirement_coverage")
        old_tc = _metric(run_id, "test_coverage")
        cost = _metric(run_id, "_cost_usd")
        dur = _metric(run_id, "_duration_seconds")
        # A failure that burned ~$0 and finished almost instantly didn't fail on
        # the model's merits — it was interrupted (usage/rate limit, a kill, a CLI
        # error). The tell: a genuine failure spends minutes and dollars; an
        # interruption is instant and free. Re-run it, don't trust the "failure".
        if cost in (0, 0.0, None) and dur is not None and dur < 60 \
                and old_tc in (0, 0.0, None):
            findings.append((label, "INTERRUPTED",
                             "~$0 cost / near-instant — a usage-limit or killed "
                             "run, not a model failure; re-run with --resume"))
            continue
        if not rep_dir.is_dir():
            findings.append((label, "UNKNOWN", "no archived run dir to inspect"))
            continue
        stack = StackConfig(
            language=rc.get("language", ""), agent=rc.get("agent", "unknown"),
            framework=rc.get("framework", "none"),
            extra={"tooling": rc["tooling"]} if "tooling" in rc else {})
        art = RunArtifacts(output_dir=rep_dir, stdout="", stderr="", exit_code=0,
                           duration_seconds=0.0, token_count=0, metadata={})
        # Mechanical-gate failure (tests did not run) → re-test with current scorers.
        if (err or "").startswith("tests did not run") or old_tc in (0, 0.0, None):
            tc = scorer.score(art, stack)
            if tc and tc > 0:
                findings.append((label, "TOOLING",
                                 f"tests now run and measure {tc:.0%} coverage — "
                                 "scorer false-failure (rescore recovers it)"))
            else:
                rate = scorer._tests_pass_rate(rep_dir.resolve(), rc.get("language", ""))
                if rate and rate > 0:
                    findings.append((label, "TOOLING",
                                     f"tests pass ({rate:.0%}) but the coverage "
                                     "tool measured 0"))
                else:
                    findings.append((label, "GENUINE",
                                     "tests do not run / do not pass on the "
                                     "archived code"))
        elif req_cov is not None and req_cov < 1.0:
            findings.append((label, "GENUINE",
                             f"spec shortfall: requirement_coverage={req_cov}"))
        else:
            findings.append((label, "GENUINE", err or "failed (no recorded reason)"))
    con.close()

    if as_json:
        click.echo(_json.dumps(
            [{"cell": c, "class": k, "cause": v} for c, k, v in findings], indent=2))
        return
    tooling = [f for f in findings if f[1] == "TOOLING"]
    genuine = [f for f in findings if f[1] == "GENUINE"]
    interrupted = [f for f in findings if f[1] == "INTERRUPTED"]
    if not findings:
        click.echo("No failed runs to diagnose — all runs are completed.")
        return
    click.echo(f"Diagnosed {len(findings)} failed run(s): {len(tooling)} TOOLING, "
               f"{len(genuine)} GENUINE, {len(interrupted)} INTERRUPTED\n")
    for c, k, v in findings:
        click.echo(f"  [{k:11}] {c}\n             {v}")
    if tooling:
        click.echo(f"\n→ {len(tooling)} tooling false-failure(s) recover with:\n"
                   f"    retort rescore --experiment-dir {experiment_dir} --only-failed")
    if interrupted:
        click.echo(f"\n→ {len(interrupted)} interrupted run(s) just need re-running:\n"
                   f"    retort run … --config {experiment_dir}/workspace.yaml "
                   "--resume --retry-failed")


@report.command("compare")
@click.option(
    "--experiment-dir",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    show_default=True,
    help="Experiment directory containing retort.db and runs/.",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="Path to workspace YAML config (for model settings).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output path for comparison.md. Defaults to <experiment>/reports/comparison.md.",
)
@click.option(
    "--group-by",
    type=str,
    default=None,
    help="Comma-separated factors to isolate. Default: all factors.",
)
def report_compare(
    experiment_dir: str, config: str, output: str | None, group_by: str | None
) -> None:
    """Compare evaluated runs across factor dimensions via the compare-runs skill."""
    from retort.config.loader import load_workspace

    workspace_config = load_workspace(config)
    exp_dir = Path(experiment_dir).resolve()

    skill = _find_skill("compare-runs", start=exp_dir)
    if skill is None:
        raise click.ClickException("skills/compare-runs not found")

    params = {"experiment_dir": str(exp_dir)}
    if output:
        params["output_file"] = str(Path(output).resolve())
    if group_by:
        params["group_by"] = group_by

    click.echo(f"Running compare-runs (model={workspace_config.evaluation.model})...")
    rc, out = _invoke_claude_skill(skill, params, workspace_config.evaluation.model, timeout=600)
    if rc != 0:
        raise click.ClickException(f"compare-runs failed rc={rc}: {out[:500]}")
    click.echo(out.strip() or "(compare-runs completed)")


@report.command("web")
@click.option(
    "--db",
    type=click.Path(exists=True),
    required=True,
    help="Path to the retort SQLite database.",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=None,
    help="Optional workspace.yaml — used to read experiment.visibility.",
)
@click.option(
    "--out",
    "out_dir",
    type=click.Path(),
    default=None,
    help="Output directory. Defaults to <db-dir>/reports/web/.",
)
@click.option(
    "--title",
    type=str,
    default=None,
    help="Override page title (defaults to the experiment name).",
)
def report_web(
    db: str, config: str | None, out_dir: str | None, title: str | None,
) -> None:
    """Generate static HTML reports from the run database.

    Produces an index.html with a sortable per-stack maturity table plus
    raw run details. No JavaScript framework — pure HTML + CSS + a small
    inline sort script.

    Respects experiment.visibility from workspace.yaml: in private mode,
    file paths and per-run details are redacted to aggregate metrics only.
    Public mode includes the full drill-down per stack.
    """
    from retort.reporting.web import generate_web_report

    db_path = Path(db).resolve()
    output = Path(out_dir).resolve() if out_dir else db_path.parent / "reports" / "web"

    visibility = "public"
    if config:
        from retort.config.loader import load_workspace
        try:
            ws = load_workspace(config)
            visibility = ws.experiment.visibility
        except Exception as exc:
            click.echo(f"warning: could not read visibility from {config}: {exc}", err=True)

    n_pages = generate_web_report(
        db_path=db_path,
        output_dir=output,
        title=title,
        visibility=visibility,
    )
    click.echo(f"Wrote {n_pages} page(s) to {output}", err=True)
    click.echo(str(output / "index.html"))


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
    active: list[dict] = []
    seen: set[str] = set()
    for rpid in r.stdout.split():
        ch = _run(["pgrep", "-P", rpid])
        if ch is None:
            continue
        for cpid in ch.stdout.split():
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
            label = "?"
            try:
                sj = _json.loads((Path(cwd) / "stack.json").read_text())
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
            et = _run(["ps", "-o", "etime=", "-p", cpid])
            elapsed = _etime_to_seconds(et.stdout) if et else None
            active.append(
                {
                    "label": label,
                    "replicate": None,
                    "elapsed_s": elapsed,
                    "evaluating": evaluating,
                }
            )
    return active


@main.command("monitor")
@click.argument("target", required=False)
@click.option(
    "--db",
    type=click.Path(exists=True),
    default=None,
    help="Path to the retort SQLite database (inferred from TARGET if omitted).",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=None,
    help="Workspace YAML; read to derive the expected total from replicates "
    "(inferred from TARGET if omitted).",
)
@click.option(
    "--total",
    type=int,
    default=None,
    help="Override the expected total run count (design cells × replicates).",
)
@click.option(
    "--watch/--once",
    default=False,
    help="Refresh continuously until all runs finish (Ctrl-C to stop).",
)
@click.option(
    "--interval",
    type=float,
    default=10.0,
    show_default=True,
    help="Seconds between refreshes in --watch mode.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit a JSON snapshot instead of the text report.",
)
def monitor_cmd(
    target: str | None,
    db: str | None,
    config: str | None,
    total: int | None,
    watch: bool,
    interval: float,
    as_json: bool,
) -> None:
    """Show live progress of an experiment run database.

    TARGET is an experiment directory (or a .db path): `retort monitor
    experiment-5` resolves to experiment-5/retort.db and its workspace.yaml.
    --db / --config override the inferred paths.

    Summarizes completed/remaining runs, per-cell coverage, cost and token
    totals, throughput, and an ETA. Safe to point at a database that one or
    more ``retort run`` shards are actively writing. Failed runs are reported
    as pending (they re-run under --resume --retry-failed), so a resume run
    isn't mistaken for "almost done". With --watch it refreshes until the run
    finishes. Progress is completed/(design-cells × replicates); pass --config
    (to read replicates) or --total when neither can be inferred.
    """
    import time

    from retort.reporting.monitor import (
        build_snapshot,
        render_json,
        render_text,
        resolve_target,
    )
    from retort.storage.database import get_engine, get_session_factory

    try:
        db_path, config_path = resolve_target(target, db, config)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if not db_path.is_file():
        raise click.ClickException(f"Database not found: {db_path}")

    replicates: int | None = None
    if config_path is not None:
        from retort.config.loader import load_workspace

        try:
            replicates = load_workspace(str(config_path)).playpen.replicates
        except Exception as exc:  # noqa: BLE001 - surfaced as a warning, non-fatal
            click.echo(
                f"warning: could not read replicates from {config_path}: {exc}",
                err=True,
            )

    engine = get_engine(db_path)
    session_factory = get_session_factory(engine)

    def _snapshot():
        session = session_factory()
        try:
            return build_snapshot(session, replicates=replicates, expected_total=total)
        finally:
            session.close()

    try:
        while True:
            snap = _snapshot()
            active = _discover_active_runs(db_path)
            if watch and not as_json:
                click.echo("\033[2J\033[H", nl=False)  # clear screen + cursor home
            if as_json:
                out = render_json(snap, active=active)
            else:
                out = render_text(snap, db_path=str(db_path), active=active)
            click.echo(out)
            if not watch or snap.is_done:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("", err=True)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
