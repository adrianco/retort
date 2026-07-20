"""Reporting subcommands (`retort report ...`) — extracted from cli.py.

Registered on the shared ``report`` group; ``retort.cli`` imports this module at
its bottom (after the group + helpers are defined -> not circular). Shared helpers
are referenced through the ``cli`` module so monkeypatching still reaches them.
"""
from __future__ import annotations

import sys  # noqa: F401  (used inside moved bodies)
from pathlib import Path  # noqa: F401

import click  # noqa: F401

from retort import cli
from retort.cli import report


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


@report.command("optimal")
@click.option(
    "--db",
    type=click.Path(exists=True),
    default=None,
    help="Aggregate master.db to read (default: the repo-root master.db).",
)
@click.option(
    "--health",
    "health_only",
    is_flag=True,
    help="Only print the data-health report — run this before trusting a refresh.",
)
@click.option(
    "--write",
    "write_blog",
    type=click.Path(),
    default=None,
    metavar="BLOG_MD",
    help="Splice the generated tables into a blog file's GEN markers, in place.",
)
def report_optimal(db: str | None, health_only: bool, write_blog: str | None) -> None:
    """Select the optimal stack per language/task from master.db.

    Aggregates the measured runs into the tables that drive optimal-blog.md:
    a leading-stacks summary, the per-language success-rate matrix (the number
    to decide on — a cross-language average hides a stack's weak languages), the
    cheapest-qualifying-stack picks, and the local prompt sweep — plus a
    data-health report.

    \b
    Print everything (tables + health) to stdout:
        retort report optimal
    Gate a refresh on data integrity first:
        retort report optimal --health
    Regenerate the blog's tables in place (idempotent):
        retort report optimal --write optimal-blog.md

    See the update-optimal-blog skill for the full refresh workflow.
    """
    from retort.reporting import optimal as opt

    db_path = Path(db) if db else opt.DB
    if not db_path.exists():
        raise click.ClickException(
            f"master.db not found at {db_path}. Pass --db <path>."
        )
    conn = opt.open_db(db_path)
    try:
        if health_only:
            click.echo(opt.health_report(conn, opt.REPO))
        elif write_blog:
            path = Path(write_blog)
            changed, skipped = opt.splice(path, conn)
            for key in skipped:
                click.echo(f"  (no GEN markers for '{key}', skipped)", err=True)
            click.echo(f"Spliced {changed} table(s) into {path}")
        else:
            click.echo(opt.render_all(conn, opt.REPO))
    finally:
        conn.close()


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

    registry = cli._load_factors(config)

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
    help="cli.Path to workspace YAML config (for model settings).",
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
    exp_dir = cli.Path(experiment_dir).resolve()

    skill = cli._find_skill("compare-runs", start=exp_dir)
    if skill is None:
        raise click.ClickException("skills/compare-runs not found")

    params = {"experiment_dir": str(exp_dir)}
    if output:
        params["output_file"] = str(cli.Path(output).resolve())
    if group_by:
        params["group_by"] = group_by

    click.echo(f"Running compare-runs (model={workspace_config.evaluation.model})...")
    rc, out = cli._invoke_claude_skill(skill, params, workspace_config.evaluation.model, timeout=600)
    if rc != 0:
        raise click.ClickException(f"compare-runs failed rc={rc}: {out[:500]}")
    click.echo(out.strip() or "(compare-runs completed)")


@report.command("web")
@click.option(
    "--db",
    type=click.Path(exists=True),
    required=True,
    help="cli.Path to the retort SQLite database.",
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

    db_path = cli.Path(db).resolve()
    output = cli.Path(out_dir).resolve() if out_dir else db_path.parent / "reports" / "web"

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
