"""Analysis / data commands (analyze, aggregate, maturity)."""
from __future__ import annotations

import click  # noqa: F401

from retort import cli
from retort.cli import main


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
        cli.sys.exit(1)

    results = cli.run_all_responses(
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
            diag = cli.check_residuals(result.model, resp_name)
            click.echo(f"\n{diag.summary()}")

        if predict:
            from retort.analysis.predict import predict_unmeasured, render_predictions
            preds = predict_unmeasured(result, df, factor_list)
            click.echo(f"\n--- Predictions for unmeasured cells ---")
            click.echo(render_predictions(preds, transform=result.transform))


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

    root = cli.Path(experiments_dir)
    n = build_master_db(root, cli.Path(out_path))
    click.echo(f"Aggregated {n} runs from {root}/experiment-*/retort.db -> {out_path}")
    if csv_path:
        write_csv(root, cli.Path(csv_path))
        click.echo(f"Wrote CSV -> {csv_path}")


@main.command("maturity")
@click.option(
    "--db",
    type=click.Path(exists=True),
    required=True,
    help="cli.Path to the retort SQLite database.",
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

    engine = get_engine(cli.Path(db))
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
        cli.Path(output).write_text(rendered)
        click.echo(f"Wrote maturity report ({len(report)} stacks) to {output}", err=True)
    else:
        click.echo(rendered)
