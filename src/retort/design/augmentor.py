"""D-optimal design augmentation via OApackage.

When a new factor level appears (e.g., a new AI agent ships), the existing
design matrix is insufficient — it doesn't cover the new level.  Rather than
re-running every experiment from scratch, D-optimal augmentation adds the
*minimum* new rows needed to estimate all main effects for the updated factor
space while preserving data from rows that have already been executed.

The algorithm:
1. Build an updated factor registry that includes the new level.
2. Generate a D-optimal design for the full updated factor space via
   OApackage's coordinate-exchange optimizer.
3. Identify which runs are already present in the existing design (no need
   to re-run them).
4. Return only the *augmentation rows* — the new runs to schedule.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from retort.design.factors import Factor, FactorRegistry
from retort.design.generator import DesignMatrix, DesignPhase


@dataclass(frozen=True)
class AugmentationResult:
    """Result of a D-optimal augmentation.

    Attributes:
        new_rows: DataFrame of new runs to schedule (same columns as original).
        full_design: The complete updated DesignMatrix (existing + new rows).
        added_factor: Name of the factor that gained a new level.
        added_level: The new level that was added.
        d_efficiency: D-efficiency of the augmented design.
    """

    new_rows: pd.DataFrame
    full_design: DesignMatrix
    added_factor: str
    added_level: str
    d_efficiency: float

    @property
    def num_new_runs(self) -> int:
        return len(self.new_rows)


def _compute_n_runs(registry: FactorRegistry) -> int:
    """Compute a reasonable number of runs for D-optimal design.

    Heuristic: max(sum of (levels - 1) + 1, product of levels up to a cap).
    The first term is the minimum for estimating all main effects (saturated);
    we add a small margin for better D-efficiency.
    """
    factors = registry.factors
    # Minimum runs to estimate intercept + all main-effect contrasts
    min_runs = 1 + sum(f.num_levels - 1 for f in factors)
    # Add margin (~50%) for better estimation, but cap at 2x minimum
    target = int(min_runs * 1.5)
    # Round up to next multiple of max level count for balance
    max_lev = max(f.num_levels for f in factors)
    target = ((target + max_lev - 1) // max_lev) * max_lev
    return max(target, min_runs + 1)


def _generate_d_optimal(
    registry: FactorRegistry,
    n_runs: int,
    nrestarts: int = 40,
) -> tuple[np.ndarray, float]:
    """Generate a D-optimal design using OApackage.

    Args:
        registry: Factor registry defining factor levels.
        n_runs: Number of runs in the design.
        nrestarts: Number of random restarts for the optimizer.

    Returns:
        Tuple of (design array with integer-encoded levels, D-efficiency).
    """
    try:
        import oapackage
    except ImportError:
        raise ImportError(
            "OApackage is required for D-optimal augmentation. "
            "Install with: pip install OApackage"
        ) from None

    factors = registry.factors
    level_counts = [f.num_levels for f in factors]
    ncols = len(factors)

    # OApackage requires intVector for factor levels
    s = oapackage.intVector(level_counts)
    arrayclass = oapackage.arraydata_t(s, n_runs, 0, ncols)

    # Pure D-optimality: alpha = [1, 0, 0]
    alpha = oapackage.doubleVector([1.0, 0.0, 0.0])

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = oapackage.Doptimize(
            arrayclass,
            nrestarts=nrestarts,
            alpha=alpha,
            verbose=0,
        )

    if not result.designs:
        raise RuntimeError("OApackage failed to generate any designs")

    # Select best design by D-efficiency
    best = max(result.designs, key=lambda d: d.Defficiency())
    arr = np.array(best)
    d_eff = best.Defficiency()

    return arr, d_eff


def _encode_existing(
    existing: DesignMatrix,
    registry: FactorRegistry,
) -> set[tuple[int, ...]]:
    """Encode existing design rows as tuples of level indices."""
    factors = registry.factors
    encoded = set()
    for _, row in existing.matrix.iterrows():
        indices = []
        for factor in factors:
            level = row[factor.name]
            try:
                idx = factor.levels.index(level)
            except ValueError:
                # Level not in updated registry — skip this row
                break
            indices.append(idx)
        else:
            encoded.add(tuple(indices))
    return encoded


def augment_design(
    existing: DesignMatrix,
    registry: FactorRegistry,
    factor_name: str,
    new_level: str,
    *,
    nrestarts: int = 40,
    n_runs: int | None = None,
) -> AugmentationResult:
    """Add rows to an existing design for a newly added factor level.

    Uses OApackage's D-optimal coordinate-exchange algorithm to generate an
    optimal design for the updated factor space, then identifies which rows
    are genuinely new (not already present in the existing design).

    Args:
        existing: The current design matrix (already partially executed).
        registry: Factor registry *before* the new level is added.
        factor_name: Name of the factor receiving a new level.
        new_level: The new level value to add.
        nrestarts: Number of optimizer restarts (higher = better but slower).
        n_runs: Total runs for the augmented design. If None, computed
                automatically.

    Returns:
        AugmentationResult with the new rows to schedule.

    Raises:
        ValueError: If the factor doesn't exist or level already exists.
        ImportError: If OApackage is not installed.
    """
    # Validate inputs
    if factor_name not in registry:
        raise ValueError(
            f"Factor {factor_name!r} not found. "
            f"Available: {registry.names}"
        )

    factor = registry.get(factor_name)
    if new_level in factor.levels:
        raise ValueError(
            f"Level {new_level!r} already exists in factor {factor_name!r}. "
            f"Existing levels: {list(factor.levels)}"
        )

    # Build updated registry with the new level
    updated_registry = FactorRegistry()
    for f in registry.factors:
        if f.name == factor_name:
            updated_levels = list(f.levels) + [new_level]
            updated_registry.add(f.name, updated_levels, f.factor_type)
        else:
            updated_registry.add(f.name, list(f.levels), f.factor_type)

    # Determine total run count for updated design
    if n_runs is None:
        n_runs = _compute_n_runs(updated_registry)

    # Ensure we have at least as many runs as existing + some new
    n_runs = max(n_runs, existing.num_runs + 1)

    # Generate D-optimal design for the updated factor space
    encoded_design, d_eff = _generate_d_optimal(
        updated_registry, n_runs, nrestarts=nrestarts
    )

    # Decode integer-encoded design back to named levels
    updated_factors = updated_registry.factors
    data: dict[str, list[str]] = {f.name: [] for f in updated_factors}
    for row_idx in range(encoded_design.shape[0]):
        for col_idx, factor in enumerate(updated_factors):
            level_idx = int(encoded_design[row_idx, col_idx]) % factor.num_levels
            data[factor.name].append(factor.levels[level_idx])

    full_df = pd.DataFrame(data)
    full_df = full_df.drop_duplicates().reset_index(drop=True)
    full_design = DesignMatrix(matrix=full_df, phase=existing.phase)

    # Find rows in the new design not present in the existing design
    existing_rows = _encode_existing(existing, updated_registry)

    new_row_indices = []
    for idx, row in full_df.iterrows():
        encoded_row = tuple(
            updated_registry.get(f.name).levels.index(row[f.name])
            for f in updated_factors
        )
        if encoded_row not in existing_rows:
            new_row_indices.append(idx)

    new_rows = full_df.iloc[new_row_indices].reset_index(drop=True)

    return AugmentationResult(
        new_rows=new_rows,
        full_design=full_design,
        added_factor=factor_name,
        added_level=new_level,
        d_efficiency=d_eff,
    )
