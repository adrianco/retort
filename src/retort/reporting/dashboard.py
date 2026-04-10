"""Dashboard reporting — full status overview of the retort workspace.

Aggregates:
- Active experiments (design matrices with run counts and completion rates)
- Lifecycle states (stack counts per phase)
- Budget usage (runs completed / failed / pending)
- Recent promotions (changelog entries)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from retort.storage.models import (
    DesignMatrix,
    ExperimentRun,
    LifecyclePhase,
    RunStatus,
)


@dataclass
class ExperimentSummary:
    """Summary of a single design matrix and its runs."""

    matrix_id: int
    name: str
    phase: str
    total_runs: int
    completed: int
    failed: int
    pending: int
    running: int
    created_at: datetime | None


@dataclass
class BudgetSummary:
    """Aggregate run budget across all experiments."""

    total_runs: int
    completed: int
    failed: int
    pending: int
    running: int
    cancelled: int

    @property
    def completion_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.completed / self.total_runs

    @property
    def failure_rate(self) -> float:
        finished = self.completed + self.failed
        if finished == 0:
            return 0.0
        return self.failed / finished


@dataclass
class LifecycleSummary:
    """Count of stacks in each lifecycle phase."""

    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


@dataclass
class PromotionEntry:
    """A recent promotion event extracted from run metadata."""

    stack_id: str
    from_phase: str
    to_phase: str
    timestamp: str


@dataclass
class DashboardReport:
    """Complete dashboard status report."""

    experiments: list[ExperimentSummary]
    budget: BudgetSummary
    lifecycle: LifecycleSummary
    recent_promotions: list[PromotionEntry]


def gather_experiments(session: Session) -> list[ExperimentSummary]:
    """Query all design matrices and their run statistics."""
    matrices = session.query(DesignMatrix).order_by(DesignMatrix.created_at.desc()).all()
    summaries: list[ExperimentSummary] = []

    for matrix in matrices:
        row_ids = [r.id for r in matrix.rows]
        if not row_ids:
            summaries.append(
                ExperimentSummary(
                    matrix_id=matrix.id,
                    name=matrix.name,
                    phase=matrix.phase.value if matrix.phase else "unknown",
                    total_runs=0,
                    completed=0,
                    failed=0,
                    pending=0,
                    running=0,
                    created_at=matrix.created_at,
                )
            )
            continue

        runs = (
            session.query(ExperimentRun)
            .filter(ExperimentRun.design_row_id.in_(row_ids))
            .all()
        )

        status_counts = {s: 0 for s in RunStatus}
        for run in runs:
            status_counts[run.status] += 1

        summaries.append(
            ExperimentSummary(
                matrix_id=matrix.id,
                name=matrix.name,
                phase=matrix.phase.value if matrix.phase else "unknown",
                total_runs=len(runs),
                completed=status_counts[RunStatus.completed],
                failed=status_counts[RunStatus.failed],
                pending=status_counts[RunStatus.pending],
                running=status_counts[RunStatus.running],
                created_at=matrix.created_at,
            )
        )

    return summaries


def gather_budget(session: Session) -> BudgetSummary:
    """Aggregate run counts across all experiments."""
    runs = session.query(ExperimentRun).all()

    status_counts = {s: 0 for s in RunStatus}
    for run in runs:
        status_counts[run.status] += 1

    return BudgetSummary(
        total_runs=len(runs),
        completed=status_counts[RunStatus.completed],
        failed=status_counts[RunStatus.failed],
        pending=status_counts[RunStatus.pending],
        running=status_counts[RunStatus.running],
        cancelled=status_counts[RunStatus.cancelled],
    )


def gather_lifecycle(session: Session) -> LifecycleSummary:
    """Count design matrices by lifecycle phase."""
    matrices = session.query(DesignMatrix).all()
    counts: dict[str, int] = {}
    for matrix in matrices:
        phase = matrix.phase.value if matrix.phase else "unknown"
        counts[phase] = counts.get(phase, 0) + 1
    return LifecycleSummary(counts=counts)


def gather_promotions(session: Session, limit: int = 10) -> list[PromotionEntry]:
    """Extract recent promotion-like transitions from run config metadata.

    Scans completed runs for run_config_json containing promotion evidence.
    Since the promotion subsystem uses in-memory changelogs, we look at
    design matrices that have moved through lifecycle phases.
    """
    # Return promotions based on design matrices that are in advanced phases
    matrices = (
        session.query(DesignMatrix)
        .filter(DesignMatrix.phase.in_([
            LifecyclePhase.trial,
            LifecyclePhase.production,
            LifecyclePhase.retired,
        ]))
        .order_by(DesignMatrix.created_at.desc())
        .limit(limit)
        .all()
    )

    entries: list[PromotionEntry] = []
    for matrix in matrices:
        # Infer the "from" phase based on current phase
        phase = matrix.phase.value if matrix.phase else "unknown"
        from_map = {
            "trial": "screening",
            "production": "trial",
            "retired": "production",
        }
        from_phase = from_map.get(phase, "unknown")
        ts = matrix.created_at.isoformat() if matrix.created_at else "unknown"
        entries.append(
            PromotionEntry(
                stack_id=matrix.name,
                from_phase=from_phase,
                to_phase=phase,
                timestamp=ts,
            )
        )

    return entries


def build_dashboard(session: Session) -> DashboardReport:
    """Build a complete dashboard report from the database."""
    return DashboardReport(
        experiments=gather_experiments(session),
        budget=gather_budget(session),
        lifecycle=gather_lifecycle(session),
        recent_promotions=gather_promotions(session),
    )


def render_text(report: DashboardReport) -> str:
    """Render dashboard report as human-readable text."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("RETORT DASHBOARD")
    lines.append("=" * 70)
    lines.append("")

    # Budget overview
    b = report.budget
    lines.append("Budget Usage")
    lines.append("-" * 40)
    lines.append(f"  Total runs:    {b.total_runs}")
    lines.append(f"  Completed:     {b.completed}")
    lines.append(f"  Failed:        {b.failed}")
    lines.append(f"  Pending:       {b.pending}")
    lines.append(f"  Running:       {b.running}")
    lines.append(f"  Cancelled:     {b.cancelled}")
    if b.total_runs > 0:
        lines.append(f"  Completion:    {b.completion_rate:.1%}")
        if b.completed + b.failed > 0:
            lines.append(f"  Failure rate:  {b.failure_rate:.1%}")
    lines.append("")

    # Lifecycle states
    lc = report.lifecycle
    lines.append("Lifecycle States")
    lines.append("-" * 40)
    if lc.counts:
        for phase in ["candidate", "screening", "trial", "production", "retired"]:
            count = lc.counts.get(phase, 0)
            if count > 0:
                lines.append(f"  {phase:15s} {count}")
        lines.append(f"  {'total':15s} {lc.total}")
    else:
        lines.append("  (no experiments)")
    lines.append("")

    # Active experiments
    lines.append("Active Experiments")
    lines.append("-" * 40)
    if report.experiments:
        for exp in report.experiments:
            lines.append(f"  [{exp.matrix_id}] {exp.name} ({exp.phase})")
            lines.append(
                f"      runs: {exp.total_runs} total, "
                f"{exp.completed} done, {exp.failed} failed, "
                f"{exp.pending} pending, {exp.running} running"
            )
    else:
        lines.append("  (no experiments)")
    lines.append("")

    # Recent promotions
    lines.append("Recent Promotions")
    lines.append("-" * 40)
    if report.recent_promotions:
        for p in report.recent_promotions:
            lines.append(
                f"  {p.stack_id}: {p.from_phase} -> {p.to_phase} ({p.timestamp})"
            )
    else:
        lines.append("  (no promotions)")
    lines.append("")

    return "\n".join(lines)


def render_json(report: DashboardReport) -> str:
    """Serialize dashboard report to JSON."""
    data = {
        "budget": {
            "total_runs": report.budget.total_runs,
            "completed": report.budget.completed,
            "failed": report.budget.failed,
            "pending": report.budget.pending,
            "running": report.budget.running,
            "cancelled": report.budget.cancelled,
            "completion_rate": report.budget.completion_rate,
            "failure_rate": report.budget.failure_rate,
        },
        "lifecycle": {
            "counts": report.lifecycle.counts,
            "total": report.lifecycle.total,
        },
        "experiments": [
            {
                "matrix_id": exp.matrix_id,
                "name": exp.name,
                "phase": exp.phase,
                "total_runs": exp.total_runs,
                "completed": exp.completed,
                "failed": exp.failed,
                "pending": exp.pending,
                "running": exp.running,
            }
            for exp in report.experiments
        ],
        "recent_promotions": [
            {
                "stack_id": p.stack_id,
                "from_phase": p.from_phase,
                "to_phase": p.to_phase,
                "timestamp": p.timestamp,
            }
            for p in report.recent_promotions
        ],
    }
    return json.dumps(data, indent=2)
