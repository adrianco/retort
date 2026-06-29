"""ANOVA attribution — how much variance is the harness vs the raw model.

Wraps Retort's ``retort.analysis.anova`` (statsmodels Type-II ANOVA on a
DataFrame) and turns each ANOVA table into an *effects table*: the percentage of
variance in each response explained by each factor / interaction (eta-squared =
SS_term / SS_total). This is the headline deliverable — it answers "of any lift
from +agenticow-memory, how much is the memory branching vs the model".

We deliberately do not re-fit anything Retort already fits; we read the same
``sum_sq`` decomposition statsmodels produced and normalise it.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import pandas as pd
from statsmodels.tools.sm_exceptions import ValueWarning

from retort.analysis.anova import AnovaResult, run_anova
from retort_metaharness import DEFAULT_RESPONSES


@dataclass
class EffectRow:
    """One factor/interaction's contribution to one response's variance."""

    term: str
    pct_variance: float  # eta-squared, SS_term / SS_total  (0..100)
    f_value: float
    p_value: float
    significant: bool


@dataclass
class ResponseEffects:
    """Effects table for a single response metric."""

    response: str
    transform: str
    r_squared: float
    adj_r_squared: float
    n_obs: int
    rows: list[EffectRow]
    residual_pct: float
    anova: AnovaResult

    def top_factor(self) -> EffectRow | None:
        valid = [r for r in self.rows if r.pct_variance == r.pct_variance]  # drop nan
        ranked = sorted(valid, key=lambda r: r.pct_variance, reverse=True)
        return ranked[0] if ranked else None


def _effects_from_anova(res: AnovaResult, n_obs: int, significance: float) -> ResponseEffects:
    table = res.anova_table
    total_ss = float(table["sum_sq"].sum())
    rows: list[EffectRow] = []
    residual_pct = 0.0
    for term in table.index:
        ss = float(table.loc[term, "sum_sq"])
        pct = 100.0 * ss / total_ss if total_ss > 0 else 0.0
        if term == "Residual":
            residual_pct = pct
            continue
        f_val = table.loc[term, "F"] if "F" in table.columns else float("nan")
        p_val = table.loc[term, "PR(>F)"] if "PR(>F)" in table.columns else float("nan")
        f_val = float(f_val) if pd.notna(f_val) else float("nan")
        p_val = float(p_val) if pd.notna(p_val) else float("nan")
        rows.append(
            EffectRow(
                term=_pretty_term(term),
                pct_variance=round(pct, 2),
                f_value=round(f_val, 3) if f_val == f_val else float("nan"),
                p_value=round(p_val, 5) if p_val == p_val else float("nan"),
                significant=bool(p_val == p_val and p_val < significance),
            )
        )
    rows.sort(key=lambda r: r.pct_variance, reverse=True)
    return ResponseEffects(
        response=res.response,
        transform=res.transform,
        r_squared=round(res.r_squared, 4),
        adj_r_squared=round(res.adj_r_squared, 4),
        n_obs=n_obs,
        rows=rows,
        residual_pct=round(residual_pct, 2),
        anova=res,
    )


def _pretty_term(raw: str) -> str:
    """C(model) -> model ; C(model):C(harness_config) -> model×harness_config."""
    parts = []
    for p in raw.split(":"):
        p = p.strip()
        if p.startswith("C(") and p.endswith(")"):
            p = p[2:-1]
        parts.append(p)
    return "×".join(parts)


def attribute(
    data: pd.DataFrame,
    *,
    factors: list[str],
    responses: list[str] | None = None,
    include_interactions: bool = True,
    significance: float = 0.10,
    transform: str = "log",
) -> dict[str, ResponseEffects]:
    """Run Type-II ANOVA per response and return effects tables.

    Args:
        data: results frame — factor columns + response columns. Tooling-fail
            cells should already be removed (see diagnose.drop_tooling_fails).
        factors: factor column names to attribute over.
        responses: response columns (default: the canonical four).
        include_interactions: include two-factor interactions in the model.
            Automatically downgraded to False if there are not enough residual
            degrees of freedom to fit the interaction model.
        significance: p threshold for the significant flag.
        transform: 'log' (multiplicative, default) or 'none' (additive). cost
            and latency are log-natural; coverage/quality default to log too but
            fall back automatically when values include 0.

    Returns:
        {response: ResponseEffects}.
    """
    responses = list(responses or DEFAULT_RESPONSES)
    responses = [r for r in responses if r in data.columns]
    factors = [f for f in factors if f in data.columns and data[f].nunique() > 1]
    if len(factors) < 1:
        raise ValueError("Need at least one varying factor present in the data.")

    out: dict[str, ResponseEffects] = {}
    for resp in responses:
        use_interactions = include_interactions and _can_fit_interactions(
            data, factors
        )
        with warnings.catch_warnings():
            # Deterministic / unbalanced subsets can make some effects
            # inestimable; statsmodels warns about rank-deficient constraints.
            # We surface that as 'n/a (aliased)' in the table instead.
            warnings.simplefilter("ignore", ValueWarning)
            warnings.simplefilter("ignore", RuntimeWarning)
            res = run_anova(
                data,
                response=resp,
                factors=factors,
                include_interactions=use_interactions,
                significance=significance,
                transform=transform,
            )
        out[resp] = _effects_from_anova(res, n_obs=len(data), significance=significance)
    return out


def _can_fit_interactions(data: pd.DataFrame, factors: list[str]) -> bool:
    """Heuristic: enough rows to estimate main effects + 2FI with residual df>0."""
    # df consumed = sum(levels-1) for mains + sum((la-1)(lb-1)) for each pair.
    main_df = sum(data[f].nunique() - 1 for f in factors)
    inter_df = 0
    for i, fa in enumerate(factors):
        for fb in factors[i + 1 :]:
            inter_df += (data[fa].nunique() - 1) * (data[fb].nunique() - 1)
    consumed = main_df + inter_df + 1  # +1 intercept
    return len(data) - consumed >= 1


def effects_to_frame(effects: dict[str, ResponseEffects]) -> pd.DataFrame:
    """Pivot effects tables to one DataFrame: rows=terms, cols=%variance/response."""
    all_terms: list[str] = []
    for re_ in effects.values():
        for row in re_.rows:
            if row.term not in all_terms:
                all_terms.append(row.term)
    data: dict[str, list[float]] = {"term": all_terms}
    for resp, re_ in effects.items():
        lookup = {row.term: row.pct_variance for row in re_.rows}
        data[resp] = [lookup.get(t, 0.0) for t in all_terms]
    df = pd.DataFrame(data)
    return df
