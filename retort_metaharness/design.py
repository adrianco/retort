"""Fractional-factorial design over our factors — the headline upgrade.

Instead of one-factor-at-a-time (OFAT), we screen the whole factor space with
an orthogonal-array / fractional-factorial design so *interaction* effects are
estimable (e.g. does +agenticow-memory help opus-4.8 but not glm-5.2?). This is
a thin composition layer over Retort's own design machinery:

- retort.design.generator.generate_design  — pyDOE3-backed fractional / full
  factorial matrices (Resolution III screening, Resolution IV characterization).
- retort.design.aliasing.compute_aliasing   — confounding/aliasing structure.

We add: our documented factor model (factors.py), constant-factor stamping,
a full-factorial confirmation grid, and a CSV cell-plan that the runner consumes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from retort.design.aliasing import AliasingReport, compute_aliasing
from retort.design.factors import FactorRegistry
from retort.design.generator import DesignMatrix, generate_design
from retort_metaharness import factors as fz


@dataclass
class CellPlan:
    """A planned experiment: the design matrix + provenance.

    Attributes:
        matrix: One row per cell. Columns are factor names (varying factors from
            the registry + any constant factors stamped on). Plus a ``cell_id``.
        phase: "screening" (fractional, Res III) or "characterization" (Res IV)
            or "full" (full factorial confirmation grid).
        fraction: Fraction of the full factorial actually run (1.0 = full).
        full_factorial_size: Total cells in the unreduced full factorial of the
            *varying* factors.
        replicates: Replicates requested per cell (stamped, not expanded here).
        varying_factors: Factor names that vary in the design.
        constant_factors: {factor: level} held constant across all cells.
        aliasing: The confounding report for the (varying) design.
    """

    matrix: pd.DataFrame
    phase: str
    fraction: float
    full_factorial_size: int
    replicates: int
    varying_factors: list[str]
    constant_factors: dict[str, str]
    aliasing: AliasingReport | None = field(default=None, repr=False)

    @property
    def num_cells(self) -> int:
        return len(self.matrix)

    @property
    def num_runs(self) -> int:
        return self.num_cells * self.replicates

    def to_csv(self, path: str | Path) -> None:
        self.matrix.to_csv(path, index=False)

    def cell_configs(self) -> list[dict[str, str]]:
        """Each cell as a {factor: level} dict (excludes cell_id helper col)."""
        recs = self.matrix.to_dict(orient="records")
        return [{k: v for k, v in r.items() if k != "cell_id"} for r in recs]


def _stamp_constants_and_id(
    matrix: pd.DataFrame, constants: dict[str, str]
) -> pd.DataFrame:
    """Add constant factor columns and a stable cell_id to a design matrix."""
    out = matrix.copy().reset_index(drop=True)
    for name, level in constants.items():
        out[name] = level
    # Reorder columns to the canonical factor order for readability
    ordered = [f for f in fz.FACTOR_ORDER if f in out.columns]
    out = out[ordered]
    out.insert(0, "cell_id", [f"c{i:03d}" for i in range(len(out))])
    return out


def build_screening_design(
    *,
    models=None,
    harnesses=None,
    scaffolds=None,
    languages=None,
    tasks=None,
    fraction: float | None = None,
    phase: str = "screening",
    replicates: int = 1,
    max_alias_order: int = 2,
) -> CellPlan:
    """Build a fractional-factorial screening design over the selected factors.

    Args:
        models/harnesses/scaffolds/languages/tasks: explicit level subsets per
            factor (None = full documented set). A factor pinned to one level is
            held constant and stamped onto every cell.
        fraction: fraction of the full factorial to run (e.g. 0.25 quarter
            fraction). None = the generator's default fractional design for the
            phase resolution.
        phase: "screening" (Res III, main effects) or "characterization"
            (Res IV, + two-factor interactions).
        replicates: replicates per cell (recorded for the runner; rows not
            duplicated in the plan).
        max_alias_order: highest interaction order to include in the aliasing
            report.

    Returns:
        CellPlan with the design matrix and the aliasing/confounding report.
    """
    registry: FactorRegistry = fz.build_registry(
        models=models, harnesses=harnesses, scaffolds=scaffolds,
        languages=languages, tasks=tasks,
    )
    constants = fz.constant_levels(
        models=models, harnesses=harnesses, scaffolds=scaffolds,
        languages=languages, tasks=tasks,
    )

    dm: DesignMatrix = generate_design(registry, phase=phase, fraction=fraction)
    aliasing = compute_aliasing(registry, phase=phase, max_order=max_alias_order)

    matrix = _stamp_constants_and_id(dm.matrix, constants)
    return CellPlan(
        matrix=matrix,
        phase=phase,
        fraction=dm.fraction,
        full_factorial_size=dm.full_factorial_size,
        replicates=replicates,
        varying_factors=registry.names,
        constant_factors=constants,
        aliasing=aliasing,
    )


def build_full_factorial(
    *,
    models=None,
    harnesses=None,
    scaffolds=None,
    languages=None,
    tasks=None,
    replicates: int = 1,
) -> CellPlan:
    """Build the full-factorial confirmation grid over the selected factors.

    Use this for a small confirmation grid once screening has narrowed the
    space — every combination of varying factor levels appears once, so all
    interactions are estimable (no aliasing).
    """
    registry = fz.build_registry(
        models=models, harnesses=harnesses, scaffolds=scaffolds,
        languages=languages, tasks=tasks,
    )
    constants = fz.constant_levels(
        models=models, harnesses=harnesses, scaffolds=scaffolds,
        languages=languages, tasks=tasks,
    )

    # Full factorial via fraction=1.0 -> generator returns the full grid.
    from itertools import product

    factor_names = registry.names
    level_lists = [registry.get(n).levels for n in factor_names]
    rows = [dict(zip(factor_names, combo)) for combo in product(*level_lists)]
    full_matrix = pd.DataFrame(rows)
    full_n = len(full_matrix)

    matrix = _stamp_constants_and_id(full_matrix, constants)
    return CellPlan(
        matrix=matrix,
        phase="full",
        fraction=1.0,
        full_factorial_size=full_n,
        replicates=replicates,
        varying_factors=factor_names,
        constant_factors=constants,
        aliasing=None,  # full factorial — nothing aliased
    )


def render_aliasing_summary(plan: CellPlan) -> str:
    """Plain-text aliasing/confounding summary for a screening plan."""
    if plan.aliasing is None:
        return "Full factorial — no aliasing (all effects clear).\n"

    rep = plan.aliasing
    lines: list[str] = []
    lines.append(
        f"Aliasing report — resolution {getattr(rep, 'resolution', '?')}, "
        f"{plan.num_cells} cells of {plan.full_factorial_size} "
        f"(fraction {plan.fraction:.3f})"
    )
    lines.append("-" * 72)
    groups = getattr(rep, "alias_groups", None) or []
    confounded = [g for g in groups if not g.is_clear]
    clear = [g for g in groups if g.is_clear]
    lines.append(f"Clear effects (estimable independently): {len(clear)}")
    for g in clear:
        lines.append(f"  ✓ {g.effects[0]}")
    if confounded:
        lines.append(f"\nConfounded / aliased groups: {len(confounded)}")
        for g in confounded:
            lines.append("  ⚠ " + "  =  ".join(g.effects))
    else:
        lines.append("\nNo confounding among the reported effect orders.")
    return "\n".join(lines) + "\n"
