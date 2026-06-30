"""Reporting — effects table, accuracy-vs-cost Pareto, Wardley/maturity overlay.

Reuses Retort's array-based Pareto sorter (``retort.analysis.pareto``) and its
lifecycle-phase classifier (``retort.analysis.maturity.classify_phase``) so the
output is consistent with Retort's own reporting vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from retort.analysis.maturity import classify_phase
from retort.analysis.pareto import pareto_analysis
from retort_metaharness import (
    DEFAULT_RESPONSES,
    RESP_COST_PER_TASK,
    RESP_REQUIREMENT_COVERAGE,
    RESPONSE_MAXIMIZE,
)
from retort_metaharness.analysis import ResponseEffects, effects_to_frame


# --------------------------------------------------------------------------
# Effects table
# --------------------------------------------------------------------------
def render_effects(effects: dict[str, ResponseEffects]) -> str:
    """ASCII effects table: % variance explained per factor, per response."""
    lines: list[str] = ["ANOVA effects table — % of variance explained", "=" * 60]
    frame = effects_to_frame(effects)
    if frame.empty:
        return "No effects to report.\n"

    resp_cols = [c for c in frame.columns if c != "term"]
    header = f"{'effect':<26}" + "".join(f"{c[:14]:>15}" for c in resp_cols)
    lines.append(header)
    lines.append("-" * len(header))
    import math

    for _, row in frame.iterrows():
        line = f"{str(row['term']):<26}"
        for c in resp_cols:
            val = row[c]
            if val is None or (isinstance(val, float) and math.isnan(val)):
                line += f"{'n/a':>15}"
            else:
                line += f"{val:>14.1f}%"
        lines.append(line)

    lines.append("-" * len(header))
    # Residual + R^2 footer
    res_line = f"{'(residual / unexplained)':<26}"
    r2_line = f"{'model R^2':<26}"
    for c in resp_cols:
        res_line += f"{effects[c].residual_pct:>14.1f}%"
        r2_line += f"{effects[c].r_squared * 100:>14.1f}%"
    lines.append(res_line)
    lines.append(r2_line)

    lines.append("\nInterpretation (largest single driver per response):")
    for resp, re_ in effects.items():
        top = re_.top_factor()
        if top:
            lines.append(
                f"  {resp:<22} -> {top.term} ({top.pct_variance:.1f}% var, "
                f"p={top.p_value:.3g}, transform={re_.transform})"
            )
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Pareto frontier (accuracy vs cost)
# --------------------------------------------------------------------------
@dataclass
class StackAgg:
    label: str
    config: dict[str, str]
    means: dict[str, float]
    n: int


def aggregate_by_config(
    df: pd.DataFrame,
    *,
    factors: list[str],
    responses: list[str] | None = None,
) -> list[StackAgg]:
    """Mean each response per unique factor-config (the 'stack')."""
    responses = [r for r in (responses or DEFAULT_RESPONSES) if r in df.columns]
    factors = [f for f in factors if f in df.columns]
    aggs: list[StackAgg] = []
    for keys, grp in df.groupby(factors, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        config = dict(zip(factors, [str(k) for k in keys]))
        label = "|".join(f"{k}={v}" for k, v in config.items())
        means = {r: float(grp[r].mean()) for r in responses}
        aggs.append(StackAgg(label=label, config=config, means=means, n=len(grp)))
    return aggs


def pareto_report(
    df: pd.DataFrame,
    *,
    factors: list[str],
    metrics: list[str] | None = None,
) -> tuple[str, list[StackAgg]]:
    """Accuracy-vs-cost Pareto over per-config means.

    Returns (text, aggs). Cost/latency are negated before ranking (the sorter
    maximises), per RESPONSE_MAXIMIZE.
    """
    metrics = [
        m for m in (metrics or [RESP_REQUIREMENT_COVERAGE, RESP_COST_PER_TASK])
        if m in df.columns
    ]
    aggs = aggregate_by_config(df, factors=factors, responses=metrics)
    if not aggs:
        return "No configs to rank.\n", []

    labels = [a.label for a in aggs]
    values = []
    for a in aggs:
        row = []
        for m in metrics:
            v = a.means[m]
            row.append(v if RESPONSE_MAXIMIZE.get(m, True) else -v)
        values.append(row)

    res = pareto_analysis(labels, values, metrics)

    lines = ["Accuracy-vs-cost Pareto frontier", "=" * 60]
    lines.append(f"metrics: {', '.join(metrics)}  (rank 0 = non-dominated)")
    lines.append("-" * 60)
    order = sorted(range(len(aggs)), key=lambda i: (res.ranks[i], -aggs[i].means.get(RESP_REQUIREMENT_COVERAGE, 0)))
    for i in order:
        a = aggs[i]
        mark = "★ frontier" if res.ranks[i] == 0 else f"  rank {res.ranks[i]}"
        metric_str = "  ".join(
            f"{m.split('_')[0]}={a.means[m]:.4g}" for m in metrics
        )
        lines.append(f"  {mark:<12} {a.label:<48} {metric_str} (n={a.n})")
    return "\n".join(lines) + "\n", aggs


# --------------------------------------------------------------------------
# Wardley / maturity overlay
# --------------------------------------------------------------------------
def maturity_overlay(
    df: pd.DataFrame,
    *,
    factors: list[str],
    headline: str = RESP_REQUIREMENT_COVERAGE,
) -> str:
    """Maturity/Wardley overlay consistent with Retort's reporting style.

    Maturity score blends headline reliability, completion (pass) rate, and
    replicate agreement; classify_phase() maps it to candidate/screening/
    trial/production — the same lifecycle ladder Retort uses for promotion.
    """
    factors = [f for f in factors if f in df.columns]
    rows: list[tuple[float, str, dict[str, str], float, float]] = []
    for keys, grp in df.groupby(factors, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        config = dict(zip(factors, [str(k) for k in keys]))
        headline_mean = float(grp[headline].mean()) if headline in grp else 0.0
        completion = (
            float((grp["status"].str.lower() == "pass").mean())
            if "status" in grp
            else 0.0
        )
        agreement = (
            1.0 - min(1.0, float(grp[headline].std(ddof=0)) / (headline_mean + 1e-9))
            if headline in grp and len(grp) > 1
            else 1.0
        )
        maturity = 0.5 * headline_mean + 0.3 * completion + 0.2 * agreement
        rows.append((maturity, headline_mean, config, completion, agreement))

    rows.sort(key=lambda r: r[0], reverse=True)
    lines = ["Wardley / maturity overlay", "=" * 60]
    lines.append(f"{'maturity':>9}  {'phase':>10}  {'headline':>9}  config")
    lines.append("-" * 60)
    for maturity, headline_mean, config, completion, agreement in rows:
        cfg = ", ".join(f"{k}={v}" for k, v in config.items())
        lines.append(
            f"{maturity:>9.3f}  {classify_phase(maturity):>10}  "
            f"{headline_mean:>9.3f}  {cfg}"
        )
        lines.append(
            f"{'':>9}  {'':>10}  {'':>9}  "
            f"completion={completion:.2f} agreement={agreement:.2f}"
        )
    lines.append(
        "\nWardley evolution: candidate→screening→trial→production tracks the "
        "genesis→custom→product→commodity axis. Lower-cost configs at equal "
        "reliability sit further right (more commoditised)."
    )
    return "\n".join(lines) + "\n"


def full_report(
    df: pd.DataFrame,
    effects: dict[str, ResponseEffects],
    *,
    factors: list[str],
) -> str:
    """Assemble the complete report: effects + Pareto + Wardley overlay."""
    parts = [render_effects(effects)]
    pareto_txt, _ = pareto_report(df, factors=factors)
    parts.append(pareto_txt)
    parts.append(maturity_overlay(df, factors=factors))
    return "\n".join(parts)
