"""Design matrix generation using fractional factorial designs.

Generates Resolution III screening designs via pyDOE3. For factors with
mixed level counts, uses a generalized fractional factorial approach.
Supports explicit fraction control (e.g. quarter-fraction) via the
`fraction` parameter, which produces a balanced subset of the full design
and documents which cells were skipped for later prediction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
import pyDOE3

from retort.design.factors import FactorRegistry


class DesignPhase(Enum):
    """Experiment phase determining design resolution."""

    SCREENING = "screening"  # Resolution III — main effects
    CHARACTERIZATION = "characterization"  # Resolution IV — + two-factor interactions


@dataclass
class DesignMatrix:
    """A generated experimental design.

    Attributes:
        matrix: DataFrame where columns are factor names and values are level names.
        phase: The design phase this matrix was generated for.
        num_runs: Number of experimental runs (rows).
        fraction: Fraction of the full factorial this matrix represents (1.0 = all cells).
        full_factorial_size: Total cells in the unreduced full factorial.
    """

    matrix: pd.DataFrame
    phase: DesignPhase
    fraction: float = 1.0
    full_factorial_size: int = 0

    @property
    def num_runs(self) -> int:
        return len(self.matrix)

    def to_csv(self, path: str) -> None:
        self.matrix.to_csv(path, index_label="run")

    def run_configs(self) -> list[dict[str, str]]:
        """Return each run as a dict of {factor_name: level_name}."""
        return self.matrix.to_dict(orient="records")

    @classmethod
    def from_csv(cls, path: str | Path, phase: DesignPhase | str = DesignPhase.SCREENING) -> "DesignMatrix":
        """Load a design matrix from a CSV file.

        The CSV must have a header row whose columns are factor names (plus an
        optional leading 'run' index column that is ignored).  This is the same
        format produced by ``to_csv()`` and ``retort design generate -o``.

        Args:
            path: Path to the CSV file.
            phase: Experiment phase to tag the loaded design with.

        Returns:
            DesignMatrix loaded from the file.
        """
        if isinstance(phase, str):
            phase = DesignPhase(phase)
        df = pd.read_csv(path)
        # Drop the index column if present (named 'run' by to_csv)
        if "run" in df.columns:
            df = df.drop(columns=["run"])
        df = df.reset_index(drop=True)
        return cls(matrix=df, phase=phase)


def _two_level_fractional(n_factors: int, resolution: int) -> np.ndarray:
    """Generate a 2-level fractional factorial design.

    Uses pyDOE3.fracfact with appropriate generator strings.
    For Resolution III screening, we want the smallest design that
    estimates all main effects.
    """
    if n_factors <= 1:
        raise ValueError("Need at least 2 factors for fractional factorial")

    if resolution == 3:
        # Resolution III: main effects estimable, 2FI aliased with main effects
        # Use fracfact generators: base factors + generators
        if n_factors <= 3:
            # Full factorial is small enough
            return pyDOE3.ff2n(n_factors)

        # For k factors, use p generators where 2^(k-p) gives adequate runs
        # Find smallest k-p such that 2^(k-p) >= k+1 (to estimate k main effects + intercept)
        base = _min_base_factors(n_factors, resolution)
        gen_string = _build_generator_string(n_factors, base)
        return pyDOE3.fracfact(gen_string)
    elif resolution == 4:
        # Resolution IV: main effects + 2FI estimable
        base = _min_base_factors(n_factors, resolution)
        gen_string = _build_generator_string(n_factors, base)
        return pyDOE3.fracfact(gen_string)
    else:
        raise ValueError(f"Unsupported resolution: {resolution}")


def _min_base_factors(n_factors: int, resolution: int) -> int:
    """Find minimum number of base factors for the given resolution.

    For Resolution III: need 2^base >= n_factors + 1
    For Resolution IV: need 2^base >= C(n_factors,2) + n_factors + 1
    """
    if resolution == 3:
        # Need at least n_factors+1 runs to estimate all main effects
        base = 1
        while 2**base < n_factors + 1:
            base += 1
        return min(base, n_factors)
    elif resolution == 4:
        base = 2
        while 2**base < n_factors + 1:
            base += 1
        # Add one more for resolution IV margin
        return min(base + 1, n_factors)
    return n_factors


def _build_generator_string(n_factors: int, n_base: int) -> str:
    """Build a pyDOE3 fracfact generator string.

    Base factors are labeled a, b, c, ...
    Generated factors are products of base factors.
    """
    letters = [chr(ord("a") + i) for i in range(n_base)]
    generators: list[str] = list(letters)

    # Generate additional columns as products of base factors
    n_generated = n_factors - n_base
    if n_generated > 0:
        gen_products = _interaction_generators(letters, n_generated)
        generators.extend(gen_products)

    return " ".join(generators)


def _interaction_generators(base_letters: list[str], n_needed: int) -> list[str]:
    """Create generator columns from interactions of base factors.

    Starts with 2-factor interactions, then 3-factor, etc.
    """
    from itertools import combinations

    generators: list[str] = []
    for order in range(2, len(base_letters) + 1):
        for combo in combinations(base_letters, order):
            generators.append("".join(combo))
            if len(generators) >= n_needed:
                return generators
    return generators


def generate_screening_design(registry: FactorRegistry) -> DesignMatrix:
    """Generate a Resolution III fractional factorial screening design.

    For mixed-level factors, uses a 2-level fractional factorial as the base
    and maps encoded columns back to factor levels using modular arithmetic.

    Args:
        registry: Factor registry with at least 2 factors.

    Returns:
        DesignMatrix with named levels for each run.
    """
    factors = registry.factors
    if len(factors) < 2:
        raise ValueError("Screening design requires at least 2 factors")

    n_factors = len(factors)

    # Generate 2-level fractional factorial base
    encoded = _two_level_fractional(n_factors, resolution=3)

    # Convert -1/+1 encoding to 0/1
    binary = ((encoded + 1) / 2).astype(int)

    # Map to named levels
    # For factors with >2 levels, we need more runs. Use the base design
    # replicated with level cycling to cover all levels.
    max_levels = max(f.num_levels for f in factors)
    if max_levels > 2:
        binary = _expand_for_mixed_levels(binary, registry)

    # Build the named DataFrame
    data: dict[str, list[str]] = {}
    for col_idx, factor in enumerate(factors):
        level_indices = binary[:, col_idx] % factor.num_levels
        data[factor.name] = [factor.levels[i] for i in level_indices]

    matrix = pd.DataFrame(data)
    # Drop exact duplicate rows
    matrix = matrix.drop_duplicates().reset_index(drop=True)

    full_n = math.prod(f.num_levels for f in factors)
    return DesignMatrix(matrix=matrix, phase=DesignPhase.SCREENING, fraction=len(matrix) / full_n, full_factorial_size=full_n)


def _expand_for_mixed_levels(
    binary: np.ndarray, registry: FactorRegistry
) -> np.ndarray:
    """Expand a binary design to cover factors with more than 2 levels.

    Replicates the base design with shifted level assignments so that all
    levels of each factor appear at least once.
    """
    factors = registry.factors
    max_levels = max(f.num_levels for f in factors)

    blocks = [binary]
    for shift in range(1, max_levels):
        shifted = binary.copy()
        for col_idx, factor in enumerate(factors):
            if factor.num_levels > 2:
                shifted[:, col_idx] = (binary[:, col_idx] + shift) % factor.num_levels
        blocks.append(shifted)

    return np.vstack(blocks)


def _one_per_primary_level(
    primary_factor: "retort.design.factors.Factor",  # type: ignore[name-defined]
    secondary_factors: list["retort.design.factors.Factor"],  # type: ignore[name-defined]
    factor_names: list[str],
) -> pd.DataFrame:
    """Generate one run per primary factor level with balanced secondary assignments.

    For a k-level primary factor and m binary secondary factors this produces
    k rows in which:
      - every primary level appears exactly once
      - each secondary factor is balanced (each level appears k/2 times for k even)
      - the correlation between any two secondary factors is minimised

    Construction (for binary secondary factors with n primary levels):
      - Factor 0: floor-division — first n//2 runs get level 0, rest level 1.
        Gives balanced halves; maximises separation between the two model groups.
      - Factor 1: period-2 alternation (i % 2).
        Independent of factor 0, balanced, minimal |r| = 1/3 with factor 0 for n=6.
      - Factor 2: binary parity (number of set bits in i, mod 2).
        Balanced and approximately orthogonal to factors 0 and 1.
      - Factor j >= 3: falls back to period-2^(j-1) interleave (may be unbalanced
        for n not divisible by 2^j; callers should check).

    For k=6 and two binary factors this gives the optimal 2-1-1-2 M×T distribution
    with |r(M,T)| = 1/3 — the minimum achievable with 6 balanced binary runs.
    """
    n = primary_factor.num_levels
    rows = []
    for i, level in enumerate(primary_factor.levels):
        row: dict[str, str] = {primary_factor.name: level}
        for j, sf in enumerate(secondary_factors):
            if sf.num_levels == 2:
                if j == 0:
                    # Floor-division: first half → level 0, second half → level 1
                    idx = (i * 2) // n
                elif j == 1:
                    # Period-2 alternation — balanced and minimally correlated with j=0
                    idx = i % 2
                elif j == 2:
                    # Binary parity of i — balanced and orthogonal to j=0 and j=1
                    idx = bin(i).count("1") % 2
                else:
                    # Higher-order: period-2^(j-1) interleave (best effort)
                    idx = (i // (2 ** (j - 1))) % 2
            else:
                idx = i % sf.num_levels
            row[sf.name] = sf.levels[idx % sf.num_levels]
        rows.append(row)

    df = pd.DataFrame(rows)
    # Reorder columns to match original factor order
    return df[factor_names]


def _multi_run_per_primary_level(
    primary_factor: "retort.design.factors.Factor",  # type: ignore[name-defined]
    secondary_factors: list["retort.design.factors.Factor"],  # type: ignore[name-defined]
    factor_names: list[str],
    runs_per_level: int,
) -> pd.DataFrame:
    """Generate multiple runs per primary level using cyclic language shifts.

    Pass k uses the ``_one_per_primary_level`` assignment for language index
    ``(i + k) % n_primary``.  This guarantees:
      - Every primary level appears exactly ``runs_per_level`` times.
      - Every secondary factor level appears in at least one pass.
      - The overall secondary factor balance is maintained across passes.

    For the common case of a half-fraction of a 6×2×2 design (runs_per_level=2)
    both binary secondary factors remain individually balanced (6 runs per level).
    """
    n = primary_factor.num_levels
    rows = []
    for k in range(runs_per_level):
        for i, prim_level in enumerate(primary_factor.levels):
            shifted_i = (i + k) % n
            row: dict[str, str] = {primary_factor.name: prim_level}
            for j, sf in enumerate(secondary_factors):
                if sf.num_levels == 2:
                    if j == 0:
                        idx = (shifted_i * 2) // n
                    elif j == 1:
                        idx = shifted_i % 2
                    elif j == 2:
                        idx = bin(shifted_i).count("1") % 2
                    else:
                        idx = (shifted_i // (2 ** (j - 1))) % 2
                else:
                    idx = shifted_i % sf.num_levels
                row[sf.name] = sf.levels[idx % sf.num_levels]
            rows.append(row)

    return pd.DataFrame(rows)[factor_names].reset_index(drop=True)


def generate_fractional_design(
    registry: FactorRegistry,
    fraction: float,
    phase: DesignPhase | str = DesignPhase.SCREENING,
) -> DesignMatrix:
    """Generate a balanced fractional factorial design at the given fraction.

    Computes the target run count as ``ceil(full_factorial_size * fraction)``,
    but always runs enough to cover every level of every factor at least once.

    When the target equals the number of levels of the highest-level factor
    (the common case for a quarter-fraction of a mixed-level design), uses the
    ``_one_per_primary_level`` construction which gives the minimum achievable
    correlation between secondary factors.

    For other target sizes, generates the full design and strides through it
    with a step chosen to cover all primary-factor levels.

    Args:
        registry: Factor registry with at least 2 factors.
        fraction: Fraction of the full factorial to generate (0 < fraction <= 1).
        phase: Experiment phase (affects resolution of the fallback full design).

    Returns:
        DesignMatrix with ``fraction`` and ``full_factorial_size`` populated.
    """
    if isinstance(phase, str):
        phase = DesignPhase(phase)

    if not 0 < fraction <= 1:
        raise ValueError(f"fraction must be in (0, 1], got {fraction}")

    factors = registry.factors
    if len(factors) < 2:
        raise ValueError("Fractional design requires at least 2 factors")

    full_n = math.prod(f.num_levels for f in factors)
    max_levels = max(f.num_levels for f in factors)
    target_n = max(math.ceil(full_n * fraction), max_levels)

    if target_n >= full_n:
        # Fraction covers everything — fall back to the standard generator
        return generate_design(registry, phase)

    # Primary factor: the one with the most levels (drives run count in a fraction)
    primary = max(factors, key=lambda f: f.num_levels)
    secondary = [f for f in factors if f.name != primary.name]
    factor_names = [f.name for f in factors]

    if target_n == primary.num_levels:
        # Exact one-per-primary-level case — use the balanced construction
        matrix = _one_per_primary_level(primary, secondary, factor_names)
    else:
        # General case: multiple runs per primary level.
        # Use cyclic shifts of the _one_per_primary_level assignment so each
        # additional pass introduces a different secondary-factor combination
        # for each primary level while preserving overall balance.
        n_primary = primary.num_levels
        runs_per_level = max(1, target_n // n_primary)
        matrix = _multi_run_per_primary_level(primary, secondary, factor_names, runs_per_level)

    return DesignMatrix(
        matrix=matrix,
        phase=phase,
        fraction=fraction,
        full_factorial_size=full_n,
    )


def generate_design(
    registry: FactorRegistry,
    phase: DesignPhase | str,
    fraction: float | None = None,
) -> DesignMatrix:
    """Generate a design matrix for the given phase.

    Args:
        registry: Factor registry.
        phase: "screening" or "characterization".
        fraction: Optional fraction of the full factorial (e.g. 0.25 for a
            quarter fraction).  When provided, delegates to
            ``generate_fractional_design``.  When omitted, generates the
            standard fractional factorial for the given resolution.

    Returns:
        DesignMatrix ready for experiment execution.
    """
    if isinstance(phase, str):
        phase = DesignPhase(phase)

    if fraction is not None and fraction < 1.0:
        return generate_fractional_design(registry, fraction, phase)

    factors = registry.factors
    full_n = math.prod(f.num_levels for f in factors)

    if phase == DesignPhase.SCREENING:
        dm = generate_screening_design(registry)
        dm.full_factorial_size = full_n
        dm.fraction = dm.num_runs / full_n
        return dm
    elif phase == DesignPhase.CHARACTERIZATION:
        # Characterization uses Resolution IV
        if len(factors) < 2:
            raise ValueError("Characterization design requires at least 2 factors")

        n_factors = len(factors)
        encoded = _two_level_fractional(n_factors, resolution=4)
        binary = ((encoded + 1) / 2).astype(int)

        max_levels = max(f.num_levels for f in factors)
        if max_levels > 2:
            binary = _expand_for_mixed_levels(binary, registry)

        data: dict[str, list[str]] = {}
        for col_idx, factor in enumerate(factors):
            level_indices = binary[:, col_idx] % factor.num_levels
            data[factor.name] = [factor.levels[i] for i in level_indices]

        matrix = pd.DataFrame(data)
        matrix = matrix.drop_duplicates().reset_index(drop=True)
        dm = DesignMatrix(matrix=matrix, phase=DesignPhase.CHARACTERIZATION)
        dm.full_factorial_size = full_n
        dm.fraction = dm.num_runs / full_n
        return dm
    else:
        raise ValueError(f"Unknown phase: {phase}")
