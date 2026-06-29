"""Tests for the retort-metaharness methodology layer.

These exercise the feature layer (factors / design / runner-glue / analysis /
diagnose / report) and confirm it composes with Retort's own design + ANOVA +
Pareto machinery. No network / no LLM (uses the LocalStubRunner).
"""

from __future__ import annotations

import math

import pandas as pd
import pytest
from retort_metaharness import analysis as mz_analysis
from retort_metaharness import design as mz_design
from retort_metaharness import diagnose as mz_diag
from retort_metaharness import factors as fz
from retort_metaharness import report as mz_report
from retort_metaharness import runner as mz_runner


# -------------------------- factors --------------------------
def test_build_registry_drops_constants_and_orders():
    reg = fz.build_registry(
        models=["deepseek-v4-pro", "opus-4.8"],
        harnesses=["base-ReAct", "+agenticow-memory"],
        scaffolds=["none"],  # single level -> constant -> dropped
        languages=["python"],  # constant -> dropped
        tasks=["rest-api-crud"],  # constant -> dropped
    )
    assert reg.names == [fz.F_MODEL, fz.F_HARNESS]
    consts = fz.constant_levels(
        models=["deepseek-v4-pro", "opus-4.8"],
        scaffolds=["none"], languages=["python"], tasks=["rest-api-crud"],
    )
    assert consts == {"scaffold": "none", "language": "python", "task": "rest-api-crud"}


def test_build_registry_requires_two_varying_factors():
    with pytest.raises(ValueError):
        fz.build_registry(models=["opus-4.8"], harnesses=["base-ReAct"],
                          scaffolds=["none"], languages=["python"], tasks=["rest-api-crud"])


def test_unknown_level_rejected():
    with pytest.raises(ValueError):
        fz.build_registry(models=["not-a-model", "opus-4.8"])


def test_openrouter_and_runner_flags_mapping():
    assert fz.openrouter_id("opus-4.8") == "anthropic/claude-opus-4.8"
    flags = fz.runner_flags_for(fz.F_HARNESS, "routed")
    assert flags.get("route") == "cheap-to-frontier"


# -------------------------- design --------------------------
def test_screening_design_is_a_fraction_with_aliasing():
    plan = mz_design.build_screening_design(
        models=["deepseek-v4-pro", "opus-4.8"],
        harnesses=["base-ReAct", "routed", "+agenticow-memory"],
        scaffolds=["none", "reflexion"],
        languages=["python", "go"],
        tasks=["rest-api-crud"],
        fraction=0.5,
    )
    assert plan.fraction <= 1.0
    assert plan.num_cells < plan.full_factorial_size
    assert "cell_id" in plan.matrix.columns
    # task held constant -> stamped on every row
    assert (plan.matrix["task"] == "rest-api-crud").all()
    assert plan.aliasing is not None
    txt = mz_design.render_aliasing_summary(plan)
    assert "Aliasing report" in txt


def test_full_factorial_has_no_aliasing_and_full_grid():
    plan = mz_design.build_full_factorial(
        models=["deepseek-v4-pro", "opus-4.8"],
        harnesses=["base-ReAct", "+agenticow-memory"],
        scaffolds=["none", "reflexion"],
        languages=["python"],
        tasks=["rest-api-crud"],
    )
    assert plan.num_cells == 2 * 2 * 2  # model x harness x scaffold
    assert plan.aliasing is None
    assert "no aliasing" in mz_design.render_aliasing_summary(plan).lower()


# -------------------------- runner glue --------------------------
def test_cellspec_runner_flags_include_model_and_toggles():
    spec = mz_runner.CellSpec(
        cell_id="c0",
        levels={fz.F_MODEL: "opus-4.8", fz.F_HARNESS: "+agenticow-memory",
                fz.F_SCAFFOLD: "reflexion", fz.F_LANGUAGE: "python",
                fz.F_TASK: "rest-api-crud"},
    )
    flags = spec.runner_flags()
    assert flags["model"] == "anthropic/claude-opus-4.8"
    assert flags["memory"] == "agenticow"
    assert flags["scaffold"] == "reflexion"


def test_local_stub_is_deterministic_and_meters_cost():
    runner = mz_runner.LocalStubRunner()
    spec = mz_runner.CellSpec(
        cell_id="c0",
        levels={fz.F_MODEL: "opus-4.8", fz.F_HARNESS: "base-ReAct",
                fz.F_SCAFFOLD: "none", fz.F_LANGUAGE: "python",
                fz.F_TASK: "rest-api-crud"},
    )
    a = runner.run(spec)
    b = runner.run(spec)
    assert a.requirement_coverage == b.requirement_coverage  # deterministic metrics
    assert a.tokens > 0 and a.cost_per_task > 0  # metered
    assert a.status == "pass"  # opus base = 0.78 >= threshold


def test_local_stub_tooling_failures_are_zero_token():
    runner = mz_runner.LocalStubRunner()
    # unsupported language
    rust = runner.run(mz_runner.CellSpec("c0", {
        fz.F_MODEL: "opus-4.8", fz.F_HARNESS: "base-ReAct", fz.F_SCAFFOLD: "none",
        fz.F_LANGUAGE: "rust", fz.F_TASK: "rest-api-crud"}))
    assert rust.status == "fail" and rust.tokens == 0 and rust.cost_per_task == 0.0
    # unimplemented harness path
    sc = runner.run(mz_runner.CellSpec("c1", {
        fz.F_MODEL: "opus-4.8", fz.F_HARNESS: "self-consistency-N",
        fz.F_SCAFFOLD: "none", fz.F_LANGUAGE: "python", fz.F_TASK: "rest-api-crud"}))
    assert sc.status == "fail" and sc.tokens == 0


# -------------------------- diagnose --------------------------
def test_classify_row_invariant():
    # zero-token failure -> tooling
    assert mz_diag.classify_row(status="fail", cost_usd=0.0, latency_s=0.0,
                                tokens=0) == mz_diag.Verdict.TOOLING_FALSE_FAIL
    # genuine model fail: real cost + time + tokens
    assert mz_diag.classify_row(status="fail", cost_usd=0.02, latency_s=8.0,
                                tokens=5000) == mz_diag.Verdict.GENUINE_MODEL_FAIL
    # pass
    assert mz_diag.classify_row(status="pass", cost_usd=0.02, latency_s=8.0,
                                tokens=5000) == mz_diag.Verdict.PASS
    # $0/instant failure even with tokens reported but require_tokens off
    thr = mz_diag.DiagnosisThresholds(require_tokens=False)
    assert mz_diag.classify_row(status="fail", cost_usd=0.0, latency_s=0.01,
                                tokens=10, thr=thr) == mz_diag.Verdict.TOOLING_FALSE_FAIL


def test_drop_tooling_fails_filters():
    df = pd.DataFrame([
        {"status": "fail", "cost_per_task": 0.0, "latency_s": 0.0, "tokens": 0},
        {"status": "fail", "cost_per_task": 0.02, "latency_s": 9.0, "tokens": 4000},
        {"status": "pass", "cost_per_task": 0.02, "latency_s": 9.0, "tokens": 4000},
    ])
    kept = mz_diag.drop_tooling_fails(df)
    assert len(kept) == 2
    summ = mz_diag.summarize(df)
    assert summ["tooling_false_fail"] == 1 and summ["genuine_model_fail"] == 1


# -------------------------- analysis + report --------------------------
def _smoke_results() -> pd.DataFrame:
    plan = mz_design.build_full_factorial(
        models=["deepseek-v4-pro", "opus-4.8"],
        harnesses=["base-ReAct", "+agenticow-memory"],
        scaffolds=["none", "reflexion"],
        languages=["python"],
        tasks=["rest-api-crud"],
        replicates=2,
    )
    specs = []
    for cid, cfg in zip(plan.matrix["cell_id"], plan.cell_configs()):
        for rep in range(plan.replicates):
            specs.append(mz_runner.CellSpec(cell_id=cid, levels=cfg, replicate=rep))
    results = mz_runner.run_plan(mz_runner.LocalStubRunner(), specs)
    return pd.DataFrame([r.to_row() for r in results])


def test_attribute_produces_effects_summing_with_residual():
    df = _smoke_results()
    factors = [c for c in fz.FACTOR_ORDER if c in df.columns and df[c].nunique() > 1]
    effects = mz_analysis.attribute(df, factors=factors, include_interactions=True)
    assert set(effects).issuperset({"requirement_coverage", "code_quality"})
    for resp, re_ in effects.items():
        total = sum(r.pct_variance for r in re_.rows if r.pct_variance == r.pct_variance)
        # explained + residual ~= 100%
        assert math.isclose(total + re_.residual_pct, 100.0, abs_tol=0.5)
    # model should be a meaningful driver of code_quality in the fixture
    top = effects["code_quality"].top_factor()
    assert top is not None and "model" in top.term


def test_full_report_renders_all_sections():
    df = _smoke_results()
    factors = [c for c in fz.FACTOR_ORDER if c in df.columns and df[c].nunique() > 1]
    effects = mz_analysis.attribute(df, factors=factors, include_interactions=True)
    text = mz_report.full_report(df, effects, factors=factors)
    assert "ANOVA effects table" in text
    assert "Pareto frontier" in text
    assert "Wardley" in text
