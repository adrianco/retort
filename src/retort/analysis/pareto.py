"""Multi-objective Pareto frontier ranking.

Identifies non-dominated solutions across multiple response metrics and
computes posterior probabilities of dominance used by promotion gates.

Terminology
-----------
- **dominates**: solution A dominates B if A is at least as good on every
  metric and strictly better on at least one (assumes *higher is better*;
  negate cost-like metrics before passing them in).
- **Pareto frontier**: the set of non-dominated solutions.
- **Pareto rank**: rank 0 = frontier, rank 1 = frontier after removing
  rank-0, etc. (non-dominated sorting, as in NSGA-II).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from retort.analysis.bayesian import NormalInverseGamma


def _dominates(a: np.ndarray, b: np.ndarray) -> bool:
    """Return True if row *a* Pareto-dominates row *b* (higher is better)."""
    return bool(np.all(a >= b) and np.any(a > b))


def pareto_frontier_mask(values: ArrayLike) -> np.ndarray:
    """Boolean mask of non-dominated rows (Pareto rank 0).

    Parameters
    ----------
    values : array-like, shape (n_solutions, n_metrics)
        Objective values.  **Higher is better** on every column; negate
        cost-like metrics before calling.

    Returns
    -------
    np.ndarray of bool, shape (n_solutions,)
        True for non-dominated rows.
    """
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2-D array, got shape {arr.shape}")
    n = arr.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]:
            continue
        for j in range(n):
            if i == j or not mask[j]:
                continue
            if _dominates(arr[j], arr[i]):
                mask[i] = False
                break
    return mask


def pareto_ranks(values: ArrayLike) -> np.ndarray:
    """Non-dominated sorting — assign integer ranks to every row.

    Rank 0 is the Pareto frontier; rank 1 is the frontier after removing
    rank-0 solutions, and so on.

    Parameters
    ----------
    values : array-like, shape (n_solutions, n_metrics)

    Returns
    -------
    np.ndarray of int, shape (n_solutions,)
    """
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2-D array, got shape {arr.shape}")
    n = arr.shape[0]
    ranks = np.full(n, -1, dtype=int)
    remaining = np.ones(n, dtype=bool)
    rank = 0
    while remaining.any():
        subset_idx = np.where(remaining)[0]
        subset = arr[subset_idx]
        frontier = pareto_frontier_mask(subset)
        for local_i, global_i in enumerate(subset_idx):
            if frontier[local_i]:
                ranks[global_i] = rank
                remaining[global_i] = False
        rank += 1
    return ranks


@dataclass
class ParetoResult:
    """Result of a Pareto analysis over a set of solutions.

    Attributes
    ----------
    labels : list[str]
        Identifier for each solution (e.g. design-row id or stack name).
    values : np.ndarray
        (n_solutions, n_metrics) objective matrix.
    metric_names : list[str]
        Column names for the objectives.
    ranks : np.ndarray
        Non-dominated sorting rank per solution.
    """

    labels: list[str]
    values: np.ndarray
    metric_names: list[str]
    ranks: np.ndarray

    @property
    def frontier_labels(self) -> list[str]:
        """Labels of rank-0 (Pareto-optimal) solutions."""
        return [self.labels[i] for i in range(len(self.labels)) if self.ranks[i] == 0]

    @property
    def frontier_mask(self) -> np.ndarray:
        return self.ranks == 0

    def is_dominated(self, label: str) -> bool:
        """True if *label* is dominated (rank > 0)."""
        idx = self.labels.index(label)
        return bool(self.ranks[idx] > 0)


def pareto_analysis(
    labels: list[str],
    values: ArrayLike,
    metric_names: list[str],
) -> ParetoResult:
    """Run Pareto analysis on a set of solutions.

    Parameters
    ----------
    labels : list[str]
        One label per solution row.
    values : array-like, shape (n_solutions, n_metrics)
        Higher-is-better objective values.
    metric_names : list[str]
        Column names.

    Returns
    -------
    ParetoResult
    """
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2-D values, got shape {arr.shape}")
    if len(labels) != arr.shape[0]:
        raise ValueError(
            f"labels length ({len(labels)}) != rows ({arr.shape[0]})"
        )
    if len(metric_names) != arr.shape[1]:
        raise ValueError(
            f"metric_names length ({len(metric_names)}) != columns ({arr.shape[1]})"
        )
    ranks = pareto_ranks(arr)
    return ParetoResult(
        labels=labels,
        values=arr,
        metric_names=metric_names,
        ranks=ranks,
    )


# ------------------------------------------------------------------
# Probabilistic dominance via Bayesian posteriors
# ------------------------------------------------------------------


def prob_pareto_non_dominated(
    posteriors_by_solution: dict[str, dict[str, NormalInverseGamma]],
    metric_names: list[str],
    n_samples: int = 5000,
    rng_seed: int | None = 42,
) -> dict[str, float]:
    """Estimate P(solution is Pareto-non-dominated) via posterior sampling.

    For each Monte-Carlo draw, sample mu for every (solution, metric) from
    the marginal Student-t posterior, then check Pareto dominance.

    Parameters
    ----------
    posteriors_by_solution : dict[str, dict[str, NIG]]
        Outer key = solution label, inner key = metric name.
    metric_names : list[str]
        Metrics to consider (must be keys in every inner dict).
    n_samples : int
        Monte-Carlo draws.
    rng_seed : int or None
        For reproducibility.

    Returns
    -------
    dict[str, float]
        P(non-dominated) per solution.  Values suitable for the
        trial-to-production gate (threshold 0.80) and the
        production-to-retired gate (1 - value vs. threshold 0.95).
    """
    rng = np.random.default_rng(rng_seed)
    labels = list(posteriors_by_solution.keys())
    n_sol = len(labels)
    n_met = len(metric_names)

    # Pre-compute t-distribution parameters for every (solution, metric)
    t_params: list[list[tuple[float, float, float]]] = []  # df, loc, scale
    for label in labels:
        row: list[tuple[float, float, float]] = []
        for met in metric_names:
            nig = posteriors_by_solution[label][met]
            df = 2.0 * nig.alpha
            loc = nig.mu_0
            scale = float(np.sqrt(nig.beta / (nig.kappa * nig.alpha)))
            row.append((df, loc, scale))
        t_params.append(row)

    non_dom_count = np.zeros(n_sol, dtype=int)

    for _ in range(n_samples):
        # Sample objectives matrix
        sampled = np.empty((n_sol, n_met))
        for i in range(n_sol):
            for j in range(n_met):
                df, loc, scale = t_params[i][j]
                z = rng.standard_t(df)
                sampled[i, j] = loc + scale * z
        # Check dominance
        mask = pareto_frontier_mask(sampled)
        non_dom_count += mask.astype(int)

    probs = non_dom_count / n_samples
    return {label: float(probs[i]) for i, label in enumerate(labels)}
