"""Design matrix generation using fractional factorial designs.

Generates Resolution III screening designs via pyDOE3. For factors with
mixed level counts, uses a generalized fractional factorial approach.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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
    """

    matrix: pd.DataFrame
    phase: DesignPhase

    @property
    def num_runs(self) -> int:
        return len(self.matrix)

    def to_csv(self, path: str) -> None:
        self.matrix.to_csv(path, index_label="run")

    def run_configs(self) -> list[dict[str, str]]:
        """Return each run as a dict of {factor_name: level_name}."""
        return self.matrix.to_dict(orient="records")


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

    return DesignMatrix(matrix=matrix, phase=DesignPhase.SCREENING)


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


def generate_design(
    registry: FactorRegistry, phase: DesignPhase | str
) -> DesignMatrix:
    """Generate a design matrix for the given phase.

    Args:
        registry: Factor registry.
        phase: "screening" or "characterization".

    Returns:
        DesignMatrix ready for experiment execution.
    """
    if isinstance(phase, str):
        phase = DesignPhase(phase)

    if phase == DesignPhase.SCREENING:
        return generate_screening_design(registry)
    elif phase == DesignPhase.CHARACTERIZATION:
        # Characterization uses Resolution IV
        factors = registry.factors
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
        return DesignMatrix(matrix=matrix, phase=DesignPhase.CHARACTERIZATION)
    else:
        raise ValueError(f"Unknown phase: {phase}")
