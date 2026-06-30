"""retort-metaharness CLI — design | run | analyze | diagnose | report.

OpenRouter-metered (key from /tmp/.orkey), conformant (the pinned
REQUIREMENTS.json gold is used only for scoring, never injected into the solve
loop). Composes Retort's design/ANOVA/Pareto with the per-cell metaharness
runner.
"""

from __future__ import annotations

from pathlib import Path

import click
import pandas as pd

from retort_metaharness import __version__
from retort_metaharness import analysis as mz_analysis
from retort_metaharness import design as mz_design
from retort_metaharness import diagnose as mz_diag
from retort_metaharness import factors as fz
from retort_metaharness import openrouter as orouter
from retort_metaharness import report as mz_report
from retort_metaharness import runner as mz_runner

def _selection_kwargs(model, harness, scaffold, language, task):
    """Map CLI multi-options to factors.build_* kwargs (None = full set)."""
    return {
        "models": list(model) or None,
        "harnesses": list(harness) or None,
        "scaffolds": list(scaffold) or None,
        "languages": list(language) or None,
        "tasks": list(task) or None,
    }


def _factor_select_options(f):
    f = click.option("--model", multiple=True, help="model level (repeatable)")(f)
    f = click.option("--harness", multiple=True, help="harness_config level (repeatable)")(f)
    f = click.option("--scaffold", multiple=True, help="scaffold level (repeatable)")(f)
    f = click.option("--language", multiple=True, help="language level (repeatable)")(f)
    f = click.option("--task", multiple=True, help="task level (repeatable)")(f)
    return f


@click.group()
@click.version_option(version=__version__, prog_name="retort-metaharness")
def main() -> None:
    """DoE/ANOVA benchmarking of agentic-orchestration harnesses (on Retort)."""


@main.command("factors")
def factors_cmd() -> None:
    """Print the documented factor model (all factors and levels)."""
    click.echo(fz.describe_factor_model())


# --------------------------------------------------------------------------
@main.command("design")
@_factor_select_options
@click.option("--full", is_flag=True, help="Full-factorial confirmation grid (no aliasing).")
@click.option("--fraction", type=float, default=None, help="Fraction of full factorial (e.g. 0.25).")
@click.option("--phase", type=click.Choice(["screening", "characterization"]), default="screening")
@click.option("--replicates", type=int, default=1)
@click.option("-o", "--out", type=click.Path(), default="design.csv", help="Cell-plan CSV.")
def design_cmd(model, harness, scaffold, language, task, full, fraction, phase, replicates, out):
    """Build a fractional-factorial screening (or full) design over our factors."""
    sel = _selection_kwargs(model, harness, scaffold, language, task)
    if full:
        plan = mz_design.build_full_factorial(replicates=replicates, **sel)
    else:
        plan = mz_design.build_screening_design(
            fraction=fraction, phase=phase, replicates=replicates, **sel
        )
    plan.to_csv(out)
    click.echo(
        f"Design: phase={plan.phase} cells={plan.num_cells} "
        f"(of {plan.full_factorial_size} full, fraction={plan.fraction:.3f}) "
        f"replicates={plan.replicates} -> {plan.num_runs} runs"
    )
    click.echo(f"Varying factors: {plan.varying_factors}")
    if plan.constant_factors:
        click.echo(f"Held constant:  {plan.constant_factors}")
    click.echo(f"Cell plan written to {out}\n")
    click.echo(mz_design.render_aliasing_summary(plan))


# --------------------------------------------------------------------------
@main.command("run")
@click.option("-d", "--design", "design_csv", type=click.Path(exists=True), required=True)
@click.option("-o", "--out", type=click.Path(), default="results.csv")
@click.option("--replicates", type=int, default=1, help="Replicates per cell.")
@click.option(
    "--runner",
    type=click.Choice(["local-stub", "metaharness"]),
    default="local-stub",
    help="local-stub = $0 no-LLM pipeline check; metaharness = the real runner.",
)
@click.option("--runner-cmd", default=None, help="Command for the metaharness runner (or $METAHARNESS_RUNNER_CMD).")
def run_cmd(design_csv, out, replicates, runner, runner_cmd):
    """Execute each design cell via the runner; write a metered results CSV."""
    plan_df = pd.read_csv(design_csv)
    configs = plan_df.to_dict(orient="records")
    configs = [{k: str(v) for k, v in c.items()} for c in configs]
    specs = mz_runner.expand_cells(configs, replicates)

    if runner == "metaharness":
        if not orouter.have_key():
            click.echo("warning: no OpenRouter key at /tmp/.orkey — the runner "
                       "needs it for real model calls.", err=True)
        r: mz_runner.CellRunner = mz_runner.MetaHarnessRunner(cmd=runner_cmd)
    else:
        r = mz_runner.LocalStubRunner()

    click.echo(f"Running {len(specs)} cell-runs via '{r.name}' runner...")
    results = mz_runner.run_plan(r, specs)
    rows = [res.to_row() for res in results]
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)

    total_cost = float(df["cost_per_task"].sum())
    n_pass = int((df["status"].str.lower() == "pass").sum())
    click.echo(
        f"Done: {len(df)} runs, {n_pass} pass, "
        f"metered cost ${total_cost:.4f} -> {out}"
    )


# --------------------------------------------------------------------------
@main.command("diagnose")
@click.option("-r", "--results", type=click.Path(exists=True), required=True)
@click.option("--min-cost", type=float, default=0.0005, help="USD floor for 'genuine'.")
@click.option("--min-latency", type=float, default=0.5, help="Seconds floor for 'genuine'.")
@click.option("-o", "--out", type=click.Path(), default=None, help="Write diagnosed CSV.")
def diagnose_cmd(results, min_cost, min_latency, out):
    """Classify every cell: TOOLING_FALSE_FAIL vs GENUINE_MODEL_FAIL vs PASS."""
    df = pd.read_csv(results)
    thr = mz_diag.DiagnosisThresholds(min_cost_usd=min_cost, min_latency_s=min_latency)
    click.echo(mz_diag.render_text(df, thr=thr))
    if out:
        mz_diag.diagnose_frame(df, thr=thr).to_csv(out, index=False)
        click.echo(f"Diagnosed results written to {out}")


# --------------------------------------------------------------------------
@main.command("analyze")
@click.option("-r", "--results", type=click.Path(exists=True), required=True)
@click.option("--no-drop-tooling", is_flag=True, help="Keep tooling-fail cells in the ANOVA.")
@click.option("--no-interactions", is_flag=True, help="Main effects only.")
@click.option("--transform", type=click.Choice(["log", "none"]), default="log")
@click.option("--significance", type=float, default=0.10)
@click.option("-o", "--out", type=click.Path(), default=None, help="Write effects-table CSV.")
def analyze_cmd(results, no_drop_tooling, no_interactions, transform, significance, out):
    """Type-II ANOVA: % variance per factor (harness vs model vs language ...)."""
    df = pd.read_csv(results)
    if not no_drop_tooling:
        before = len(df)
        df = mz_diag.drop_tooling_fails(df)
        click.echo(f"(dropped {before - len(df)} tooling-false-fail cells before ANOVA)")
    factors = [c for c in fz.FACTOR_ORDER if c in df.columns and df[c].nunique() > 1]
    if not factors:
        raise click.ClickException("No varying factors present in results.")
    effects = mz_analysis.attribute(
        df,
        factors=factors,
        include_interactions=not no_interactions,
        significance=significance,
        transform=transform,
    )
    click.echo(mz_report.render_effects(effects))
    if out:
        mz_analysis.effects_to_frame(effects).to_csv(out, index=False)
        click.echo(f"Effects table written to {out}")


# --------------------------------------------------------------------------
@main.command("report")
@click.option("-r", "--results", type=click.Path(exists=True), required=True)
@click.option("--no-drop-tooling", is_flag=True)
@click.option("--transform", type=click.Choice(["log", "none"]), default="log")
@click.option("-o", "--out", type=click.Path(), default=None, help="Write full report text.")
def report_cmd(results, no_drop_tooling, transform, out):
    """Full report: effects table + accuracy-vs-cost Pareto + Wardley overlay."""
    raw = pd.read_csv(results)
    df = raw if no_drop_tooling else mz_diag.drop_tooling_fails(raw)
    factors = [c for c in fz.FACTOR_ORDER if c in df.columns and df[c].nunique() > 1]
    effects = mz_analysis.attribute(
        df, factors=factors, include_interactions=True, transform=transform
    )
    # Diagnosis summary header
    diag_txt = mz_diag.render_text(raw)
    body = mz_report.full_report(df, effects, factors=factors)
    text = diag_txt + "\n" + body
    click.echo(text)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        click.echo(f"Report written to {out}")


# --------------------------------------------------------------------------
@main.command("smoke")
@click.option("-o", "--out-dir", type=click.Path(), default="smoke-out")
def smoke_cmd(out_dir):
    """End-to-end $0 smoke: design->run(local-stub)->diagnose->ANOVA->report.

    Proves the whole pipeline produces a real ANOVA effects table and a real
    diagnosis on >=2 cells without any paid API call. The local-stub runner
    uses NO model — numbers reflect the deterministic fixture, not real models.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Multi-factor full-factorial smoke grid. language=rust is unsupported by
    # the stub (-> tooling fail); self-consistency-N + reflexion is a known
    # buggy combo (-> tooling fail). Everything else runs genuinely.
    plan = mz_design.build_full_factorial(
        models=["deepseek-v4-pro", "opus-4.8"],
        harnesses=["base-ReAct", "self-consistency-N", "+agenticow-memory"],
        scaffolds=["none", "reflexion"],
        languages=["python", "rust"],
        tasks=["rest-api-crud"],
        replicates=2,
    )
    design_csv = out / "design.csv"
    plan.to_csv(design_csv)
    click.echo(f"[1/5] design: {plan.num_cells} cells x {plan.replicates} reps "
               f"= {plan.num_runs} runs (full factorial, no aliasing)")

    specs = mz_runner.expand_cells(plan.cell_configs(), plan.replicates)
    # cell_configs() drops cell_id, so re-attach from the matrix for stable ids
    ids = list(plan.matrix["cell_id"])
    specs = []
    for cid, cfg in zip(ids, plan.cell_configs()):
        for rep in range(plan.replicates):
            specs.append(mz_runner.CellSpec(cell_id=cid, levels=cfg, replicate=rep))

    runner = mz_runner.LocalStubRunner()
    results = mz_runner.run_plan(runner, specs)
    df = pd.DataFrame([r.to_row() for r in results])
    results_csv = out / "results.csv"
    df.to_csv(results_csv, index=False)
    total_cost = float(df["cost_per_task"].sum())
    click.echo(f"[2/5] run: {len(df)} runs via local-stub, "
               f"metered (tokens x price) cost ${total_cost:.4f}")

    # The $0 stub's costs/latencies sit below the real-LLM diagnosis floor, so
    # for the smoke we key on the token signal (tokens==0 => the harness never
    # engaged => tooling). With the real runner the default $/time floors apply.
    thr = mz_diag.DiagnosisThresholds(min_latency_s=0.0)
    diag_txt = mz_diag.render_text(df, thr=thr)
    (out / "diagnosis.txt").write_text(diag_txt, encoding="utf-8")
    summ = mz_diag.summarize(df, thr=thr)
    click.echo(f"[3/5] diagnose: pass={summ['pass']} "
               f"genuine_model_fail={summ['genuine_model_fail']} "
               f"tooling_false_fail={summ['tooling_false_fail']}")

    genuine = mz_diag.drop_tooling_fails(df, thr=thr)
    factors = [c for c in fz.FACTOR_ORDER if c in genuine.columns and genuine[c].nunique() > 1]
    effects = mz_analysis.attribute(
        genuine, factors=factors, include_interactions=True, transform="log"
    )
    eff_frame = mz_analysis.effects_to_frame(effects)
    eff_frame.to_csv(out / "effects.csv", index=False)
    click.echo(f"[4/5] analyze: ANOVA on {len(genuine)} genuine cells, "
               f"factors={factors}")

    report_text = (
        diag_txt + "\n" + mz_report.full_report(genuine, effects, factors=factors)
    )
    (out / "report.txt").write_text(report_text, encoding="utf-8")
    click.echo(f"[5/5] report: written to {out / 'report.txt'}\n")
    click.echo(report_text)
    click.echo(f"\nAll smoke artifacts in: {out}/")


if __name__ == "__main__":
    main()
