"""Small utility subcommands — `retort plugin/export/tasks ...` — extracted from
cli.py. Each registers on its shared group; ``retort.cli`` imports this at its
bottom. These have no cli-helper dependencies (only stdlib + their group).
"""
from __future__ import annotations

import json  # noqa: F401
import sys  # noqa: F401
from pathlib import Path  # noqa: F401

import click  # noqa: F401

from retort.cli import plugin, export, tasks  # noqa: F401


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


