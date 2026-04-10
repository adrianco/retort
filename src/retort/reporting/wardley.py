"""Wardley map overlay — stack evolution stage visualization.

Maps each stack (design matrix) to a Wardley evolution stage based on its
lifecycle phase, and renders an overlay visualization as text or JSON.

Wardley evolution stages:
    I   Genesis       ← candidate
    II  Custom-Built  ← screening
    III Product       ← trial
    IV  Commodity     ← production
    (retired stacks shown as off-map / decommissioned)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from retort.storage.models import (
    DesignMatrix,
    ExperimentRun,
    LifecyclePhase,
    RunStatus,
)

# Mapping from lifecycle phase to Wardley evolution stage.
EVOLUTION_STAGES: dict[str, tuple[int, str]] = {
    "candidate": (1, "Genesis"),
    "screening": (2, "Custom-Built"),
    "trial": (3, "Product"),
    "production": (4, "Commodity"),
    "retired": (0, "Retired"),
}

# Column boundaries for ASCII map rendering (each stage gets a band).
_STAGE_ORDER = ["Genesis", "Custom-Built", "Product", "Commodity"]


@dataclass
class StackPosition:
    """A single stack positioned on the Wardley map."""

    stack_id: str
    phase: str
    evolution_stage: str
    evolution_index: int
    visibility: float  # 0.0–1.0, higher = more visible in value chain
    run_count: int
    completion_rate: float


@dataclass
class WardleyMapReport:
    """Complete Wardley map overlay report."""

    stacks: list[StackPosition]
    stage_counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.stacks)

    @property
    def active_stacks(self) -> list[StackPosition]:
        """Stacks that are not retired."""
        return [s for s in self.stacks if s.phase != "retired"]

    @property
    def retired_stacks(self) -> list[StackPosition]:
        return [s for s in self.stacks if s.phase == "retired"]


def gather_stacks(session: Session) -> list[StackPosition]:
    """Query all design matrices and map them to Wardley positions."""
    matrices = session.query(DesignMatrix).order_by(DesignMatrix.created_at.desc()).all()
    positions: list[StackPosition] = []

    for matrix in matrices:
        phase = matrix.phase.value if matrix.phase else "candidate"
        stage_index, stage_name = EVOLUTION_STAGES.get(phase, (1, "Genesis"))

        row_ids = [r.id for r in matrix.rows]
        if row_ids:
            runs = (
                session.query(ExperimentRun)
                .filter(ExperimentRun.design_row_id.in_(row_ids))
                .all()
            )
            total_runs = len(runs)
            completed = sum(1 for r in runs if r.status == RunStatus.completed)
            completion_rate = completed / total_runs if total_runs > 0 else 0.0
        else:
            total_runs = 0
            completed = 0
            completion_rate = 0.0

        # Visibility is derived from completion rate and run volume.
        # Higher completion with more runs = more visible in the value chain.
        volume_factor = min(total_runs / 10.0, 1.0) if total_runs > 0 else 0.1
        visibility = round(completion_rate * 0.7 + volume_factor * 0.3, 3)

        positions.append(
            StackPosition(
                stack_id=matrix.name,
                phase=phase,
                evolution_stage=stage_name,
                evolution_index=stage_index,
                visibility=visibility,
                run_count=total_runs,
                completion_rate=round(completion_rate, 4),
            )
        )

    return positions


def build_wardley_map(session: Session) -> WardleyMapReport:
    """Build a complete Wardley map overlay from the database."""
    stacks = gather_stacks(session)

    stage_counts: dict[str, int] = {name: 0 for name in _STAGE_ORDER}
    stage_counts["Retired"] = 0
    for s in stacks:
        stage_counts[s.evolution_stage] = stage_counts.get(s.evolution_stage, 0) + 1

    return WardleyMapReport(stacks=stacks, stage_counts=stage_counts)


def render_text(report: WardleyMapReport) -> str:
    """Render Wardley map overlay as human-readable text."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("WARDLEY MAP — STACK EVOLUTION OVERLAY")
    lines.append("=" * 70)
    lines.append("")

    # Evolution stage summary
    lines.append("Evolution Stage Distribution")
    lines.append("-" * 40)
    for stage in _STAGE_ORDER:
        count = report.stage_counts.get(stage, 0)
        bar = "#" * count
        lines.append(f"  {stage:15s} [{count:2d}] {bar}")
    retired_count = report.stage_counts.get("Retired", 0)
    if retired_count > 0:
        bar = "#" * retired_count
        lines.append(f"  {'Retired':15s} [{retired_count:2d}] {bar}")
    lines.append(f"  {'Total':15s}  {report.total}")
    lines.append("")

    # ASCII map: Y-axis = visibility, X-axis = evolution stage
    lines.append("Map Overlay (visibility vs. evolution)")
    lines.append("-" * 70)
    col_width = 16
    header = "  Visibility |"
    for stage in _STAGE_ORDER:
        header += f" {stage:^{col_width}s}|"
    lines.append(header)
    lines.append("  " + "-" * (1 + (col_width + 2) * len(_STAGE_ORDER) + 1))

    # Bucket stacks by visibility bands and stage
    active = report.active_stacks
    bands = [
        ("high", 0.7, 1.01),
        ("med", 0.3, 0.7),
        ("low", 0.0, 0.3),
    ]

    for band_label, lo, hi in bands:
        row = f"  {band_label:>10s} |"
        for stage in _STAGE_ORDER:
            in_cell = [
                s.stack_id for s in active
                if s.evolution_stage == stage and lo <= s.visibility < hi
            ]
            if in_cell:
                # Truncate names to fit
                cell_text = ", ".join(
                    n[:12] for n in in_cell[:2]
                )
                if len(in_cell) > 2:
                    cell_text += f" +{len(in_cell) - 2}"
            else:
                cell_text = "·"
            row += f" {cell_text:^{col_width}s}|"
        lines.append(row)

    lines.append("  " + "-" * (1 + (col_width + 2) * len(_STAGE_ORDER) + 1))
    lines.append("")

    # Detail listing grouped by stage
    lines.append("Stack Details")
    lines.append("-" * 40)
    for stage in _STAGE_ORDER + ["Retired"]:
        stage_stacks = [s for s in report.stacks if s.evolution_stage == stage]
        if not stage_stacks:
            continue
        lines.append(f"  [{stage}]")
        for s in sorted(stage_stacks, key=lambda x: -x.visibility):
            lines.append(
                f"    {s.stack_id:20s}  vis={s.visibility:.2f}  "
                f"runs={s.run_count}  done={s.completion_rate:.0%}"
            )
    lines.append("")

    return "\n".join(lines)


def render_json(report: WardleyMapReport) -> str:
    """Serialize Wardley map overlay to JSON."""
    data = {
        "stage_counts": report.stage_counts,
        "total": report.total,
        "stacks": [
            {
                "stack_id": s.stack_id,
                "phase": s.phase,
                "evolution_stage": s.evolution_stage,
                "evolution_index": s.evolution_index,
                "visibility": s.visibility,
                "run_count": s.run_count,
                "completion_rate": s.completion_rate,
            }
            for s in report.stacks
        ],
    }
    return json.dumps(data, indent=2)
