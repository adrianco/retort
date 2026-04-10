"""Retort CLI entry point."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click

from retort import __version__
from retort.analysis.anova import run_all_responses, run_anova
from retort.analysis.residuals import check_residuals
from retort.design.factors import FactorRegistry
from retort.design.generator import generate_design

WORKSPACE_TEMPLATE = """\
# Retort workspace configuration
# See docs/configuration.md for full reference

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
"""


@click.group()
@click.version_option(version=__version__, prog_name="retort")
def main() -> None:
    """Retort — Platform Evolution Engine.

    Distill the best from the combinatorial mess.
    """


@main.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Overwrite existing directory")
def init(name: str, force: bool):
    """Initialize a new Retort workspace.

    Creates a workspace directory with a config template and initialized SQLite database.
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
    config_path.write_text(WORKSPACE_TEMPLATE)

    # Initialize database
    db_path = workspace / "retort.db"
    _init_database(db_path)

    click.echo(f"Initialized Retort workspace in {workspace}")
    click.echo(f"  Config:   {config_path}")
    click.echo(f"  Database: {db_path}")
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
    """
    registry = _load_factors(config)

    if len(registry) < 2:
        click.echo("Error: need at least 2 factors for design generation.", err=True)
        sys.exit(1)

    result = generate_design(registry, phase)

    if output:
        result.to_csv(output)
        click.echo(f"Design matrix written to {output} ({result.num_runs} runs)")
    else:
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
def run_experiments(
    phase: str,
    config: str,
    task_source: str | None,
    replicates: int | None,
    dry_run: bool,
) -> None:
    """Execute experiment runs for a design matrix.

    Generates the design, provisions playpens, executes each run,
    scores the results, and stores everything in the workspace database.
    """
    import yaml as _yaml

    from retort.config.loader import load_workspace
    from retort.playpen.docker_runner import DockerRunner
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

    # Generate design matrix
    design = generate_design(registry, phase)
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

    if dry_run:
        click.echo("\n[dry-run] Design matrix:")
        for i, run_config in enumerate(design.run_configs()):
            click.echo(f"  Run {i+1}: {run_config}")
        click.echo(f"\nWould execute {total_runs} runs. Exiting.")
        return

    # Initialize database
    config_dir = Path(config).resolve().parent
    db_path = config_dir / "retort.db"
    engine = get_engine(db_path)
    create_tables(engine)

    # Set up runner and scorer
    runner = DockerRunner(timeout_minutes=workspace_config.playpen.timeout_minutes)
    metric_names = [r.name for r in workspace_config.responses]
    collector = ScoreCollector(metrics=metric_names)

    click.echo(f"\nStarting experiment runs...")

    completed = 0
    failed = 0

    session = get_session(engine)
    try:
        for run_idx, run_config in enumerate(design.run_configs()):
            stack = StackConfig.from_run_config(run_config)

            for rep in range(1, reps + 1):
                label = f"[{run_idx+1}/{design.num_runs} rep {rep}/{reps}]"
                click.echo(f"  {label} {stack.language}/{stack.framework}/{stack.agent}", nl=False)

                env_id = runner.provision(stack, task)
                try:
                    artifacts = runner.execute(env_id, stack, task)
                    scores = collector.collect(artifacts, stack)

                    status = "ok" if artifacts.succeeded else "FAIL"
                    score_str = ", ".join(
                        f"{k}={v:.2f}" for k, v in scores.to_dict().items()
                    )
                    click.echo(f" — {status} ({artifacts.duration_seconds:.1f}s) [{score_str}]")

                    # Store results
                    _store_run_result(
                        session, run_config, phase, run_idx, rep,
                        artifacts, scores,
                    )

                    if artifacts.succeeded:
                        completed += 1
                    else:
                        failed += 1
                finally:
                    runner.teardown(env_id)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

    click.echo(f"\nDone: {completed} completed, {failed} failed out of {total_runs}")


def _store_run_result(
    session,
    run_config: dict[str, str],
    phase: str,
    run_idx: int,
    replicate: int,
    artifacts,
    scores,
) -> None:
    """Store a run and its scores in the database."""
    from retort.storage.models import (
        ExperimentRun,
        RunResult,
        RunStatus,
    )
    from datetime import datetime, timezone

    status = RunStatus.completed if artifacts.succeeded else RunStatus.failed

    run = ExperimentRun(
        design_row_id=None,
        replicate=replicate,
        status=status,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        error_message=artifacts.stderr if not artifacts.succeeded else None,
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
    type=click.Choice(["text", "json", "csv"]),
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
def analyze(
    data: str,
    responses: tuple[str, ...],
    factors: tuple[str, ...],
    interactions: bool,
    significance: float,
    show_residuals: bool,
) -> None:
    """Analyse experimental results using ANOVA.

    Reads a CSV of experiment data and runs Type II ANOVA for each response
    metric, reporting which factors have statistically significant effects.
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
    )

    for resp_name, result in results.items():
        click.echo(f"\n{'='*60}")
        click.echo(f"Response: {resp_name}")
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


if __name__ == "__main__":
    main()
