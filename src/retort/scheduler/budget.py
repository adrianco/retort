"""Cost tracking per phase, spend limits, and budget reporting.

Each experimental phase (screening, trial, etc.) may have an independent spend
cap.  The :class:`BudgetTracker` accumulates costs as runs complete and
enforces the configured limit, raising :class:`BudgetExhausted` when a phase
exceeds its cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from retort.storage.models import LifecyclePhase


class BudgetExhausted(Exception):
    """Raised when a phase's spend limit has been reached."""


@dataclass(frozen=True)
class CostEntry:
    """An immutable record of a single cost event."""

    phase: LifecyclePhase
    amount_usd: float
    description: str
    recorded_at: datetime


@dataclass(frozen=True)
class PhaseReport:
    """Budget summary for a single phase."""

    phase: LifecyclePhase
    total_spend_usd: float
    limit_usd: float | None
    remaining_usd: float | None
    num_entries: int
    is_exhausted: bool


@dataclass
class BudgetTracker:
    """Tracks cumulative spend per lifecycle phase against configurable limits.

    Parameters
    ----------
    limits:
        Mapping of phase → maximum spend in USD.  Phases without an entry
        have no spending cap.
    """

    limits: dict[LifecyclePhase, float] = field(default_factory=dict)
    _ledger: list[CostEntry] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_limit(self, phase: LifecyclePhase, limit_usd: float) -> None:
        """Set or update the spend cap for *phase*.

        Raises ``ValueError`` if *limit_usd* is negative.
        """
        if limit_usd < 0:
            raise ValueError(f"limit must be non-negative, got {limit_usd}")
        self.limits[phase] = limit_usd

    # ------------------------------------------------------------------
    # Recording costs
    # ------------------------------------------------------------------

    def record(
        self,
        phase: LifecyclePhase,
        amount_usd: float,
        description: str = "",
    ) -> CostEntry:
        """Record a cost event against *phase*.

        Raises
        ------
        ValueError
            If *amount_usd* is negative.
        BudgetExhausted
            If recording this cost would exceed the phase limit.
        """
        if amount_usd < 0:
            raise ValueError(f"cost must be non-negative, got {amount_usd}")

        limit = self.limits.get(phase)
        if limit is not None:
            new_total = self.spend(phase) + amount_usd
            if new_total > limit:
                raise BudgetExhausted(
                    f"phase {phase.value!r} would exceed budget: "
                    f"${new_total:.2f} > ${limit:.2f} limit"
                )

        entry = CostEntry(
            phase=phase,
            amount_usd=amount_usd,
            description=description,
            recorded_at=datetime.now(timezone.utc),
        )
        self._ledger.append(entry)
        return entry

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def spend(self, phase: LifecyclePhase) -> float:
        """Return the total spend so far for *phase*."""
        return sum(e.amount_usd for e in self._ledger if e.phase is phase)

    def remaining(self, phase: LifecyclePhase) -> float | None:
        """Return remaining budget for *phase*, or ``None`` if no limit is set."""
        limit = self.limits.get(phase)
        if limit is None:
            return None
        return max(0.0, limit - self.spend(phase))

    def is_exhausted(self, phase: LifecyclePhase) -> bool:
        """Return ``True`` if the phase's spend has reached or exceeded its limit."""
        limit = self.limits.get(phase)
        if limit is None:
            return False
        return self.spend(phase) >= limit

    def entries(self, phase: LifecyclePhase | None = None) -> list[CostEntry]:
        """Return cost entries, optionally filtered by *phase*."""
        if phase is None:
            return list(self._ledger)
        return [e for e in self._ledger if e.phase is phase]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def phase_report(self, phase: LifecyclePhase) -> PhaseReport:
        """Generate a budget summary for a single *phase*."""
        total = self.spend(phase)
        limit = self.limits.get(phase)
        return PhaseReport(
            phase=phase,
            total_spend_usd=total,
            limit_usd=limit,
            remaining_usd=self.remaining(phase),
            num_entries=len(self.entries(phase)),
            is_exhausted=self.is_exhausted(phase),
        )

    def report(self) -> list[PhaseReport]:
        """Generate budget summaries for all phases that have activity or limits."""
        active_phases: set[LifecyclePhase] = set()
        for entry in self._ledger:
            active_phases.add(entry.phase)
        active_phases.update(self.limits.keys())
        return [self.phase_report(p) for p in sorted(active_phases, key=lambda p: p.value)]
