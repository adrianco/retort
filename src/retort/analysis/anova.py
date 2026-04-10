"""ANOVA analysis using statsmodels OLS with categorical encoding.

Fits a linear model with categorical factors and (optionally) two-factor
interactions, then runs Type II ANOVA to determine which factors have
statistically significant effects on each response metric.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm


@dataclass(frozen=True)
class AnovaResult:
    """Result of an ANOVA analysis for one response metric.

    Attributes:
        response: Name of the response variable analysed.
        anova_table: The statsmodels ANOVA table as a DataFrame.
        significant_factors: Factor names with p-value below the threshold.
        r_squared: R-squared of the fitted OLS model.
        adj_r_squared: Adjusted R-squared of the fitted model.
        model: The fitted OLS model (for residual diagnostics).
    """

    response: str
    anova_table: pd.DataFrame
    significant_factors: list[str]
    r_squared: float
    adj_r_squared: float
    model: object = field(repr=False)


def _sanitize_name(name: str) -> str:
    """Make a column name safe for use in statsmodels formulas.

    Replaces characters that would break patsy formula parsing with
    underscores.
    """
    return name.replace("-", "_").replace(" ", "_").replace(".", "_")


def _sanitize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Sanitize all column names and return the mapping from new to original."""
    mapping: dict[str, str] = {}
    renames: dict[str, str] = {}
    for col in df.columns:
        safe = _sanitize_name(col)
        if safe != col:
            renames[col] = safe
        mapping[safe] = col
    return df.rename(columns=renames), mapping


def build_formula(
    response: str,
    factors: list[str],
    include_interactions: bool = False,
) -> str:
    """Build an OLS formula string with categorical encoding.

    Args:
        response: Name of the response column.
        factors: Names of factor columns (must be sanitized).
        include_interactions: If True, include all two-factor interactions.

    Returns:
        A patsy-style formula string, e.g.
        ``"y ~ C(A) + C(B) + C(A):C(B)"``.
    """
    terms = [f"C({f})" for f in factors]
    if include_interactions and len(factors) >= 2:
        for i, f1 in enumerate(factors):
            for f2 in factors[i + 1 :]:
                terms.append(f"C({f1}):C({f2})")
    return f"{response} ~ {' + '.join(terms)}"


def run_anova(
    data: pd.DataFrame,
    response: str,
    factors: list[str] | None = None,
    include_interactions: bool = False,
    significance: float = 0.10,
) -> AnovaResult:
    """Run ANOVA on experimental results for a single response metric.

    Args:
        data: DataFrame with factor columns and at least one response column.
            Factor columns should contain categorical level names.
        response: Name of the response column to analyse.
        factors: Factor column names. If None, all columns except *response*
            are treated as factors.
        include_interactions: Include two-factor interaction terms.
        significance: P-value threshold for declaring a factor significant.

    Returns:
        AnovaResult with the ANOVA table and significant factors.

    Raises:
        ValueError: If the data is insufficient for the model.
    """
    if response not in data.columns:
        raise ValueError(f"Response column {response!r} not found in data")

    if factors is None:
        factors = [c for c in data.columns if c != response]

    if not factors:
        raise ValueError("No factor columns provided or found")

    # Sanitize names for patsy formula compatibility
    df = data.copy()
    safe_response = _sanitize_name(response)
    safe_factors: list[str] = []
    rename_map: dict[str, str] = {}
    reverse_map: dict[str, str] = {}

    for f in factors:
        safe = _sanitize_name(f)
        if safe != f:
            rename_map[f] = safe
        safe_factors.append(safe)
        reverse_map[safe] = f

    if safe_response != response:
        rename_map[response] = safe_response

    if rename_map:
        df = df.rename(columns=rename_map)

    formula = build_formula(safe_response, safe_factors, include_interactions)
    model = ols(formula, data=df).fit()
    table = anova_lm(model, typ=2)

    # Extract significant factors from ANOVA table rows
    significant: list[str] = []
    for row_label in table.index:
        if row_label == "Residual":
            continue
        p = table.loc[row_label, "PR(>F)"]
        if pd.notna(p) and p < significance:
            # Map back to original factor names
            original = _anova_row_to_factor(row_label, reverse_map)
            if original is not None:
                significant.append(original)

    return AnovaResult(
        response=response,
        anova_table=table,
        significant_factors=significant,
        r_squared=model.rsquared,
        adj_r_squared=model.rsquared_adj,
        model=model,
    )


def _anova_row_to_factor(row_label: str, reverse_map: dict[str, str]) -> str | None:
    """Extract the original factor name(s) from an ANOVA table row label.

    Row labels look like ``C(language)`` for main effects or
    ``C(language):C(agent)`` for interactions.
    """
    parts = row_label.split(":")
    names: list[str] = []
    for part in parts:
        part = part.strip()
        if part.startswith("C(") and part.endswith(")"):
            safe_name = part[2:-1]
            names.append(reverse_map.get(safe_name, safe_name))
    if not names:
        return None
    return ":".join(names)


def run_all_responses(
    data: pd.DataFrame,
    responses: list[str],
    factors: list[str] | None = None,
    include_interactions: bool = False,
    significance: float = 0.10,
) -> dict[str, AnovaResult]:
    """Run ANOVA for multiple response metrics.

    Args:
        data: DataFrame with factor and response columns.
        responses: List of response column names.
        factors: Factor column names (if None, inferred).
        include_interactions: Include two-factor interactions.
        significance: P-value threshold.

    Returns:
        Dict mapping response name to its AnovaResult.
    """
    if factors is None:
        factors = [c for c in data.columns if c not in responses]

    results: dict[str, AnovaResult] = {}
    for resp in responses:
        results[resp] = run_anova(
            data,
            response=resp,
            factors=factors,
            include_interactions=include_interactions,
            significance=significance,
        )
    return results
