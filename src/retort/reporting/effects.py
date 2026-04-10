"""Main effect and interaction effect computation from experiment results.

Computes:
- Main effects: mean response per level of each factor
- Interaction effects: mean response per (level_i, level_j) for each factor pair

Data is pulled from the SQLAlchemy storage layer (design matrix + run results).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import pandas as pd
from sqlalchemy.orm import Session

from retort.storage.models import (
    DesignMatrix,
    DesignMatrixCell,
    DesignMatrixRow,
    ExperimentRun,
    FactorLevel,
    RunResult,
    RunStatus,
)


@dataclass
class MainEffect:
    """Mean response for each level of a single factor."""

    factor: str
    metric: str
    level_means: dict[str, float]
    grand_mean: float

    @property
    def effect_range(self) -> float:
        """Spread between max and min level means."""
        if not self.level_means:
            return 0.0
        vals = list(self.level_means.values())
        return max(vals) - min(vals)


@dataclass
class InteractionEffect:
    """Mean response for each combination of two factor levels."""

    factor_a: str
    factor_b: str
    metric: str
    cell_means: dict[tuple[str, str], float]
    grand_mean: float


@dataclass
class EffectsReport:
    """Complete effects analysis for one metric across a design matrix."""

    metric: str
    design_name: str
    n_runs: int
    grand_mean: float
    main_effects: list[MainEffect] = field(default_factory=list)
    interactions: list[InteractionEffect] = field(default_factory=list)


def _build_results_frame(session: Session, matrix_id: int) -> pd.DataFrame:
    """Query database and build a flat DataFrame of run results with factor levels.

    Returns a DataFrame with columns: one per factor + one per metric.
    Each row is a completed experiment run.
    """
    rows = (
        session.query(
            DesignMatrixRow.id.label("row_id"),
            DesignMatrixRow.row_index,
            FactorLevel.factor_name,
            FactorLevel.level_name,
        )
        .join(DesignMatrixCell, DesignMatrixCell.row_id == DesignMatrixRow.id)
        .join(FactorLevel, FactorLevel.id == DesignMatrixCell.factor_level_id)
        .filter(DesignMatrixRow.matrix_id == matrix_id)
        .all()
    )

    if not rows:
        return pd.DataFrame()

    # Pivot factor assignments: row_id -> {factor_name: level_name}
    factor_map: dict[int, dict[str, str]] = {}
    for row_id, _row_index, factor_name, level_name in rows:
        factor_map.setdefault(row_id, {})[factor_name] = level_name

    # Get completed run results for these rows
    results = (
        session.query(
            ExperimentRun.design_row_id,
            ExperimentRun.replicate,
            RunResult.metric_name,
            RunResult.value,
        )
        .join(RunResult, RunResult.run_id == ExperimentRun.id)
        .filter(
            ExperimentRun.design_row_id.in_(list(factor_map.keys())),
            ExperimentRun.status == RunStatus.completed,
        )
        .all()
    )

    if not results:
        return pd.DataFrame()

    # Build flat records
    records: list[dict[str, object]] = []
    for design_row_id, replicate, metric_name, value in results:
        if design_row_id not in factor_map:
            continue
        record: dict[str, object] = {**factor_map[design_row_id]}
        record["_replicate"] = replicate
        record["_metric"] = metric_name
        record["_value"] = value
        records.append(record)

    return pd.DataFrame(records)


def compute_main_effects(
    df: pd.DataFrame, factors: list[str], metric: str
) -> list[MainEffect]:
    """Compute main effect (mean per level) for each factor."""
    subset = df[df["_metric"] == metric]
    if subset.empty:
        return []

    grand_mean = float(subset["_value"].mean())
    effects: list[MainEffect] = []

    for factor in factors:
        level_means = (
            subset.groupby(factor)["_value"].mean().to_dict()
        )
        effects.append(
            MainEffect(
                factor=factor,
                metric=metric,
                level_means={str(k): float(v) for k, v in level_means.items()},
                grand_mean=grand_mean,
            )
        )

    return effects


def compute_interaction_effects(
    df: pd.DataFrame, factors: list[str], metric: str
) -> list[InteractionEffect]:
    """Compute interaction effects (mean per level pair) for all factor pairs."""
    subset = df[df["_metric"] == metric]
    if subset.empty:
        return []

    grand_mean = float(subset["_value"].mean())
    interactions: list[InteractionEffect] = []

    for fa, fb in combinations(factors, 2):
        cell_means = (
            subset.groupby([fa, fb])["_value"].mean().to_dict()
        )
        interactions.append(
            InteractionEffect(
                factor_a=fa,
                factor_b=fb,
                metric=metric,
                cell_means={
                    (str(k[0]), str(k[1])): float(v)
                    for k, v in cell_means.items()
                },
                grand_mean=grand_mean,
            )
        )

    return interactions


def compute_effects(
    session: Session, matrix_id: int, metric: str
) -> EffectsReport:
    """Compute full effects report for a metric on a design matrix.

    Args:
        session: SQLAlchemy session.
        matrix_id: ID of the design matrix.
        metric: Name of the response metric to analyze.

    Returns:
        EffectsReport with main effects and interactions.

    Raises:
        ValueError: If the design matrix is not found or has no completed runs.
    """
    matrix = session.get(DesignMatrix, matrix_id)
    if matrix is None:
        raise ValueError(f"Design matrix {matrix_id} not found")

    df = _build_results_frame(session, matrix_id)
    if df.empty:
        raise ValueError(
            f"No completed runs with results for design matrix {matrix_id}"
        )

    # Identify factors from columns (everything except _prefixed columns)
    factors = [c for c in df.columns if not c.startswith("_")]

    available_metrics = df["_metric"].unique().tolist()
    if metric not in available_metrics:
        raise ValueError(
            f"Metric {metric!r} not found. Available: {available_metrics}"
        )

    grand_mean = float(df[df["_metric"] == metric]["_value"].mean())
    n_runs = int(df[df["_metric"] == metric]["_replicate"].nunique() * len(
        df[df["_metric"] == metric].drop(columns=["_replicate", "_metric", "_value"])
        .drop_duplicates()
    ))

    main = compute_main_effects(df, factors, metric)
    interactions = compute_interaction_effects(df, factors, metric)

    return EffectsReport(
        metric=metric,
        design_name=matrix.name,
        n_runs=len(df[df["_metric"] == metric]),
        grand_mean=grand_mean,
        main_effects=main,
        interactions=interactions,
    )
