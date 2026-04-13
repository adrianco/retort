"""Predict response values + 95% CIs for unmeasured factor combinations.

Useful for fractional factorial designs: the experiment runs a fraction
of the cells, the ANOVA fits a model on what was measured, and this
module projects predictions for the cells that weren't run. The user
then knows where to invest more replicates (cells with high uncertainty)
or where to act on a strong predicted effect (cells with tight CIs and
extreme predicted values).

The model assumed here is the one fit by ``analysis.anova.run_anova``.
Predictions account for the response transform (log10 vs identity) and
back-transform the CI bounds so the output is on the original scale.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from retort.analysis.anova import AnovaResult


@dataclass(frozen=True)
class Prediction:
    """Predicted response for one factor combination.

    All values are reported on the *original* (back-transformed) scale,
    so a log-fitted model still produces predictions/CIs you can read
    in the units of the metric. The transform applied is recorded.
    """

    factors: dict[str, str]
    predicted: float
    ci_lower: float
    ci_upper: float
    transform: str

    def to_dict(self) -> dict:
        return {
            "factors": self.factors,
            "predicted": self.predicted,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "transform": self.transform,
        }


def predict_unmeasured(
    result: AnovaResult,
    data: pd.DataFrame,
    factors: list[str] | None = None,
    *,
    alpha: float = 0.05,
) -> list[Prediction]:
    """Return predictions for every factor combination NOT present in data.

    Args:
        result: The fitted AnovaResult from ``run_anova`` (or one entry
            from ``run_all_responses``).
        data: The original DataFrame fed into the analysis. Used both to
            enumerate the full factor space (cartesian product of observed
            levels) and to identify which combinations were measured.
        factors: Factor column names. If None, inferred from ``data`` by
            excluding the response.
        alpha: Significance for the prediction interval (default 0.05 → 95%).

    Returns:
        List of Prediction objects on the original scale, sorted by
        ``predicted`` ascending.
    """
    response = result.response
    if factors is None:
        factors = [c for c in data.columns if c != response]

    # Observed combinations (so we don't predict cells we already measured).
    observed = {
        tuple(row[f] for f in factors)
        for _, row in data[factors].drop_duplicates().iterrows()
    }

    # Cartesian product of all observed levels per factor.
    levels_per_factor = [sorted(data[f].dropna().unique()) for f in factors]
    all_combos = itertools.product(*levels_per_factor)

    # Build a DataFrame of cells we want predictions for.
    rows = [combo for combo in all_combos if combo not in observed]
    if not rows:
        return []
    pred_df = pd.DataFrame(rows, columns=factors)

    # statsmodels needs the same sanitized column names the model was fit on.
    from retort.analysis.anova import _sanitize_name
    rename = {c: _sanitize_name(c) for c in factors if _sanitize_name(c) != c}
    if rename:
        pred_df = pred_df.rename(columns=rename)

    model = result.model
    pred = model.get_prediction(pred_df)
    summary = pred.summary_frame(alpha=alpha)

    # Back-transform if log was applied. The transform string is one of:
    #   'none', 'log10(y)', 'log10(y+1)'.
    transform = result.transform

    def _back(value: float) -> float:
        if transform == "log10(y)":
            return float(10 ** value)
        if transform == "log10(y+1)":
            return float(10 ** value - 1)
        return float(value)

    out: list[Prediction] = []
    for (idx, _), pred_row in zip(pred_df.iterrows(), summary.itertuples()):
        combo = rows[idx] if idx < len(rows) else tuple(pred_df.iloc[idx])
        out.append(Prediction(
            factors=dict(zip(factors, combo)),
            predicted=_back(pred_row.mean),
            ci_lower=_back(pred_row.mean_ci_lower),
            ci_upper=_back(pred_row.mean_ci_upper),
            transform=transform,
        ))

    out.sort(key=lambda p: p.predicted)
    return out


def render_predictions(predictions: list[Prediction], *, transform: str = "none") -> str:
    """Human-readable table of predictions."""
    if not predictions:
        return "(no unmeasured cells — every combination is in the data)"

    factor_names = list(predictions[0].factors.keys())
    note = f"  [model fit on {transform} scale; values back-transformed]"
    header = "  ".join(factor_names) + "  |  predicted  (95% CI)"
    sep = "-" * max(len(header), 60)

    lines = [note, sep, header, sep]
    for p in predictions:
        factors_str = "  ".join(str(p.factors[f]) for f in factor_names)
        lines.append(
            f"{factors_str}  |  {p.predicted:>9.3f}  ({p.ci_lower:.3f} – {p.ci_upper:.3f})"
        )
    return "\n".join(lines)


def predictions_to_json(predictions: list[Prediction]) -> str:
    return json.dumps([p.to_dict() for p in predictions], indent=2)
