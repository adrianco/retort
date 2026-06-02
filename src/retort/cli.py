"""Retort CLI entry point."""

from __future__ import annotations

import json
import os
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
    levels: [claude-code, cursor, copilot]
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
    help="With --resume, also re-run cells whose prior attempts only failed (no completed replicate).",
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
    from retort.playpen.task_loader import load_task
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
        for i, run_config in enumerate(design.run_configs()):
            config_key = json.dumps(run_config, sort_keys=True)
            for rep in range(1, reps + 1):
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
        engine.dispose()
        return

    # Set up runner and scorer
    runner_type = workspace_config.playpen.runner
    if runner_type == "local":
        prompts_dir = config_dir / "prompts"
        runner = LocalRunner(
            timeout_minutes=workspace_config.playpen.timeout_minutes,
            max_turns=workspace_config.playpen.max_turns,
            local_inference_cost=workspace_config.playpen.local_inference_cost,
            prompts_dir=prompts_dir if prompts_dir.is_dir() else None,
        )
    else:
        runner = DockerRunner(timeout_minutes=workspace_config.playpen.timeout_minutes)
    metric_names = [r.name for r in workspace_config.responses]
    collector = ScoreCollector(metrics=metric_names)

    # Fail fast: validate agent types before any runs start.
    if runner_type == "local":
        _supported_agents = {"claude-code"}
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
    skipped = 0
    accumulated_cost = 0.0
    cost_limit = workspace_config.playpen.cost_limit_usd

    session = get_session(engine)
    try:
        for run_idx, run_config in enumerate(design.run_configs()):
            stack = StackConfig.from_run_config(run_config)
            config_key = json.dumps(run_config, sort_keys=True)

            for rep in range(1, reps + 1):
                label = f"[{run_idx+1}/{design.num_runs} rep {rep}/{reps}]"
                if not _shard_owns(config_key, rep, shard_index, shard_total):
                    # Belongs to a different shard. Don't even mark it skipped —
                    # another polecat will pick it up.
                    continue
                if (config_key, rep) in skip_keys:
                    click.echo(f"  {label} {stack.language}/{stack.framework}/{stack.agent} — skip (resume)")
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
                try:
                    artifacts = runner.execute(env_id, stack, task)
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

                    status = "ok" if run_ok else "FAIL"
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
                    else:
                        failed += 1

                    if artifacts.metadata:
                        try:
                            accumulated_cost += float(artifacts.metadata.get("total_cost_usd") or 0)
                        except (TypeError, ValueError):
                            pass
                    if cost_limit is not None and accumulated_cost > cost_limit:
                        raise click.ClickException(
                            f"cost_limit_usd ${cost_limit:.2f} exceeded "
                            f"(accumulated ${accumulated_cost:.4f}) — aborting"
                        )
                finally:
                    runner.teardown(env_id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

    summary = f"\nDone: {completed} completed, {failed} failed out of {total_runs}"
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
        shutil.copytree(src, dest)
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
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
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
    param_str = " ".join(f"{k}={v}" for k, v in params.items())
    prompt = f"Follow skill at {skill_path} for {param_str}"
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
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


def _run_has_requirement_coverage(db_path, run_config: dict, replicate: int) -> bool:
    """True if the matching completed run already has a requirement_coverage row."""
    import sqlite3
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT 1 FROM run_results rr JOIN experiment_runs er ON er.id=rr.run_id "
            "WHERE rr.metric_name='requirement_coverage' AND er.replicate=? "
            "AND json_extract(er.run_config_json,'$.language')=? "
            "AND json_extract(er.run_config_json,'$.model')=? "
            "AND json_extract(er.run_config_json,'$.tooling')=? LIMIT 1",
            (replicate, run_config.get("language"), run_config.get("model"),
             run_config.get("tooling")),
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
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id FROM experiment_runs WHERE replicate=? AND status='completed' "
        "AND json_extract(run_config_json,'$.language')=? "
        "AND json_extract(run_config_json,'$.model')=? "
        "AND json_extract(run_config_json,'$.tooling')=? "
        "ORDER BY finished_at DESC", (replicate, run_config.get("language"),
                                      run_config.get("model"), run_config.get("tooling")),
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
) -> None:
    """Store a run and its scores in the database.

    ``conformance_failed`` marks an agent-succeeded run that nonetheless fails a
    conformance gate (tests did not run, or the spec gate failed) as ``failed``
    — so the matrix records it as a genuine failure to retry, not a zero-scored
    success. ``requirement_coverage``, when the spec eval produced one, is
    persisted as a metric so the eval's verdict feeds the scored data.
    """
    from retort.storage.models import (
        ExperimentRun,
        RunResult,
        RunStatus,
    )
    from datetime import datetime, timezone

    status = (
        RunStatus.completed
        if (artifacts.succeeded and not conformance_failed)
        else RunStatus.failed
    )

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
    # and lost forever.
    if artifacts.duration_seconds:
        session.add(RunResult(
            run_id=run.id,
            metric_name="_duration_seconds",
            value=float(artifacts.duration_seconds),
        ))
    if artifacts.token_count:
        session.add(RunResult(
            run_id=run.id,
            metric_name="_tokens",
            value=float(artifacts.token_count),
        ))
    cost_str = artifacts.metadata.get("total_cost_usd") if artifacts.metadata else None
    if cost_str:
        try:
            session.add(RunResult(
                run_id=run.id,
                metric_name="_cost_usd",
                value=float(cost_str),
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
        # Walk two levels: runs/<cell>/<rep> — rep dirs contain the actual code.
        # A rep dir is any subdir whose name starts with "rep".
        targets = sorted(
            rep
            for cell in runs_root.iterdir() if cell.is_dir()
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
    "--eval-model", default="claude-opus-4-6", show_default=True,
    help="Judge model for the second-opinion spec eval.",
)
@click.option("--workers", default=2, show_default=True, type=int)
@click.option(
    "--force", is_flag=True,
    help="Re-evaluate runs that already have requirement_coverage.",
)
def reevaluate(experiment_dir, config, eval_model, workers, force):
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
    reps = sorted(
        rep for cell in runs_root.iterdir() if cell.is_dir()
        for rep in cell.iterdir()
        if rep.is_dir() and rep.name.startswith("rep") and not rep.name.endswith("-failed")
    )
    work = []
    skipped = 0
    for rep in reps:
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
        m = re.search(r"rep(\d+)", rep.name)
        replicate = int(m.group(1)) if m else 1
        if not force and _run_has_requirement_coverage(db_path, run_config, replicate):
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

    results = []
    if workers <= 1:
        results = [_eval(w) for w in work]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for fut in concurrent.futures.as_completed([pool.submit(_eval, w) for w in work]):
                exc = fut.exception()
                if exc:
                    click.echo(f"  (worker error: {exc})", err=True)
                else:
                    results.append(fut.result())

    persisted = 0
    inconclusive = 0
    for rep, run_config, replicate, verdict, cov in results:
        label = f"{rep.parent.name}/{rep.name}"
        if verdict is None:
            # Eval couldn't run (usage limit / timeout). Don't persist — leave
            # the run uncovered so a later resume re-evaluates it cleanly.
            inconclusive += 1
            click.echo(f"  {label}: inconclusive (eval didn't run) — retry later")
            continue
        if _persist_requirement_coverage(db_path, run_config, replicate, cov):
            persisted += 1
        click.echo(f"  {label}: ReqCov={cov} [{'PASS' if verdict else 'fail'}]")
    # Fold any WAL back into the .db so readers (aggregate) + git see a clean file.
    import sqlite3
    cx = sqlite3.connect(db_path)
    cx.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cx.close()
    msg = f"Persisted requirement_coverage for {persisted}/{len(results)} runs."
    if inconclusive:
        msg += f" {inconclusive} inconclusive (usage limit/timeout) — re-run to finish."
    click.echo(msg)


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
    import subprocess

    def _run(args: list[str]) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=5)
        except Exception:  # noqa: BLE001 - best-effort; never fail the monitor
            return None

    exp = db_path.resolve().parent.name
    r = _run(["pgrep", "-f", f"retort run .*{exp}"])
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
            if "claude" not in cmd or " -p" not in cmd:
                continue
            evaluating = "haiku" in cmd
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
                label = "/".join(
                    str(sj[k]) for k in ("language", "model", "tooling") if k in sj
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
