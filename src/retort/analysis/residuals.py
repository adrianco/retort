"""Residual diagnostics for model adequacy checks.

After fitting an OLS model via ANOVA, these checks verify that the model
assumptions (normality, homoscedasticity, independence) are reasonable.
If residual patterns remain, the design resolution may need to be upgraded
to capture higher-order interactions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class ResidualDiagnostics:
    """Summary of residual analysis for a fitted model.

    Attributes:
        response: The response variable name.
        n_obs: Number of observations.
        residuals: Raw residuals from the model.
        standardized_residuals: Residuals divided by their standard deviation.
        shapiro_stat: Shapiro-Wilk test statistic for normality.
        shapiro_p: P-value for the Shapiro-Wilk test.
        normality_ok: True if residuals appear normally distributed (p > 0.05).
        levene_stat: Levene test statistic for homoscedasticity (if groups provided).
        levene_p: P-value for the Levene test.
        homoscedasticity_ok: True if variance appears constant across groups.
        durbin_watson: Durbin-Watson statistic for autocorrelation.
        independence_ok: True if DW is in [1.5, 2.5] (no strong autocorrelation).
        outlier_indices: Row indices of observations with |standardized residual| > 3.
    """

    response: str
    n_obs: int
    residuals: np.ndarray
    standardized_residuals: np.ndarray
    shapiro_stat: float
    shapiro_p: float
    normality_ok: bool
    levene_stat: float | None
    levene_p: float | None
    homoscedasticity_ok: bool | None
    durbin_watson: float
    independence_ok: bool
    outlier_indices: list[int]

    @property
    def all_ok(self) -> bool:
        """True if all checked assumptions pass."""
        checks = [self.normality_ok, self.independence_ok]
        if self.homoscedasticity_ok is not None:
            checks.append(self.homoscedasticity_ok)
        return all(checks)

    def summary(self) -> str:
        """Return a human-readable summary of the diagnostics."""
        lines = [
            f"Residual Diagnostics: {self.response}",
            f"  Observations: {self.n_obs}",
            f"  Shapiro-Wilk: W={self.shapiro_stat:.4f}, p={self.shapiro_p:.4f}"
            f"  {'PASS' if self.normality_ok else 'FAIL'}",
            f"  Durbin-Watson: {self.durbin_watson:.4f}"
            f"  {'PASS' if self.independence_ok else 'FAIL'}",
        ]
        if self.levene_stat is not None:
            lines.append(
                f"  Levene: F={self.levene_stat:.4f}, p={self.levene_p:.4f}"
                f"  {'PASS' if self.homoscedasticity_ok else 'FAIL'}"
            )
        if self.outlier_indices:
            lines.append(f"  Outliers (|z|>3): rows {self.outlier_indices}")
        lines.append(f"  Overall: {'PASS' if self.all_ok else 'FAIL'}")
        return "\n".join(lines)


def _durbin_watson(residuals: np.ndarray) -> float:
    """Compute the Durbin-Watson statistic."""
    diff = np.diff(residuals)
    return float(np.sum(diff**2) / np.sum(residuals**2))


def check_residuals(
    model: object,
    response: str,
    group_column: str | None = None,
    data: pd.DataFrame | None = None,
    normality_alpha: float = 0.05,
    homoscedasticity_alpha: float = 0.05,
) -> ResidualDiagnostics:
    """Run residual diagnostics on a fitted OLS model.

    Args:
        model: A fitted statsmodels OLS result (must have `resid` and `fittedvalues`).
        response: Name of the response variable (for labelling).
        group_column: If provided, run Levene's test for equal variances
            across groups of this factor. Requires *data* to be provided.
        data: The original data (needed for Levene's test grouping).
        normality_alpha: Significance level for the Shapiro-Wilk test.
        homoscedasticity_alpha: Significance level for the Levene test.

    Returns:
        ResidualDiagnostics with all computed checks.
    """
    resid = np.array(model.resid)  # type: ignore[attr-defined]
    n = len(resid)

    # Standardized residuals
    std = resid.std(ddof=1) if n > 1 else 1.0
    if std == 0:
        std_resid = np.zeros_like(resid)
    else:
        std_resid = resid / std

    # Normality: Shapiro-Wilk (works for n <= 5000)
    if n >= 3:
        sw_stat, sw_p = stats.shapiro(resid)
    else:
        sw_stat, sw_p = float("nan"), float("nan")
    normality_ok = bool(sw_p > normality_alpha) if not np.isnan(sw_p) else True

    # Homoscedasticity: Levene's test across groups
    levene_stat: float | None = None
    levene_p: float | None = None
    homoscedasticity_ok: bool | None = None

    if group_column is not None and data is not None and group_column in data.columns:
        groups = [
            resid[data[group_column] == level]
            for level in data[group_column].unique()
        ]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) >= 2:
            levene_stat, levene_p = stats.levene(*groups)
            levene_stat = float(levene_stat)
            levene_p = float(levene_p)
            homoscedasticity_ok = levene_p > homoscedasticity_alpha

    # Independence: Durbin-Watson
    dw = _durbin_watson(resid) if n >= 2 else float("nan")
    independence_ok = bool(1.5 <= dw <= 2.5) if not np.isnan(dw) else True

    # Outliers
    outlier_indices = [int(i) for i, z in enumerate(std_resid) if abs(z) > 3]

    return ResidualDiagnostics(
        response=response,
        n_obs=n,
        residuals=resid,
        standardized_residuals=std_resid,
        shapiro_stat=float(sw_stat),
        shapiro_p=float(sw_p),
        normality_ok=normality_ok,
        levene_stat=levene_stat,
        levene_p=levene_p,
        homoscedasticity_ok=homoscedasticity_ok,
        durbin_watson=float(dw),
        independence_ok=independence_ok,
        outlier_indices=outlier_indices,
    )
