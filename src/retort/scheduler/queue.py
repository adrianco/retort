"""Priority queue of pending experiment runs.

Manages the ordering and lifecycle of runs waiting to be executed.
Runs are prioritised by phase (screening before trial before production)
and then by insertion order within the same priority.
"""

from __future__ import annotations

import enum
import heapq
import itertools
from dataclasses import dataclass, field

from retort.storage.models import LifecyclePhase


class QueuedRunStatus(str, enum.Enum):
    """Status of a run within the scheduler queue."""

    pending = "pending"
    executing = "executing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


# Lower number = higher priority.  Screening runs should execute before
# trial runs, which should execute before production monitoring.
PHASE_PRIORITY: dict[LifecyclePhase, int] = {
    LifecyclePhase.screening: 0,
    LifecyclePhase.trial: 1,
    LifecyclePhase.production: 2,
    LifecyclePhase.candidate: 3,
    LifecyclePhase.retired: 4,
}


@dataclass(frozen=True)
class PendingRun:
    """Describes a single run waiting in the queue.

    Attributes
    ----------
    run_id:
        Application-level identifier for this run (e.g. design_row_id + replicate).
    phase:
        The lifecycle phase this run belongs to.
    priority:
        Explicit priority override.  Lower is higher priority.  When ``None``
        the phase-based default is used.
    run_config:
        The factor-level mapping for this run.
    estimated_cost_usd:
        Optional estimated cost, used for budget pre-checks.
    """

    run_id: str
    phase: LifecyclePhase
    priority: int | None = None
    run_config: dict[str, str] = field(default_factory=dict)
    estimated_cost_usd: float | None = None

    @property
    def effective_priority(self) -> int:
        """Return the priority to use for ordering."""
        if self.priority is not None:
            return self.priority
        return PHASE_PRIORITY.get(self.phase, 99)


class RunNotFound(Exception):
    """Raised when a run_id is not found in the queue."""


@dataclass
class RunQueue:
    """A priority queue that manages pending experiment runs.

    Runs are ordered first by effective priority (lower = more urgent),
    then by insertion order (FIFO within the same priority).
    """

    _heap: list[tuple[int, int, PendingRun]] = field(default_factory=list)
    _counter: itertools.count = field(default_factory=itertools.count)
    _statuses: dict[str, QueuedRunStatus] = field(default_factory=dict)
    _removed: set[str] = field(default_factory=set)

    # ------------------------------------------------------------------
    # Enqueue / Dequeue
    # ------------------------------------------------------------------

    def enqueue(self, run: PendingRun) -> None:
        """Add a run to the queue.

        Raises ``ValueError`` if a run with the same *run_id* is already queued.
        """
        if run.run_id in self._statuses:
            raise ValueError(f"run {run.run_id!r} is already in the queue")
        count = next(self._counter)
        heapq.heappush(self._heap, (run.effective_priority, count, run))
        self._statuses[run.run_id] = QueuedRunStatus.pending

    def dequeue(self) -> PendingRun | None:
        """Remove and return the highest-priority pending run, or ``None`` if empty.

        Skips runs that have been cancelled or already removed.
        The returned run is automatically moved to *executing* status.
        """
        while self._heap:
            _prio, _count, run = heapq.heappop(self._heap)
            if run.run_id in self._removed:
                continue
            status = self._statuses.get(run.run_id)
            if status is not QueuedRunStatus.pending:
                continue
            self._statuses[run.run_id] = QueuedRunStatus.executing
            return run
        return None

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def mark_completed(self, run_id: str) -> None:
        """Mark a run as completed.

        Raises :class:`RunNotFound` if *run_id* is unknown.
        """
        self._require_exists(run_id)
        self._statuses[run_id] = QueuedRunStatus.completed

    def mark_failed(self, run_id: str) -> None:
        """Mark a run as failed.

        Raises :class:`RunNotFound` if *run_id* is unknown.
        """
        self._require_exists(run_id)
        self._statuses[run_id] = QueuedRunStatus.failed

    def cancel(self, run_id: str) -> None:
        """Cancel a pending run, removing it from consideration.

        Raises :class:`RunNotFound` if *run_id* is unknown.
        """
        self._require_exists(run_id)
        self._statuses[run_id] = QueuedRunStatus.cancelled
        self._removed.add(run_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def status(self, run_id: str) -> QueuedRunStatus:
        """Return the current status of *run_id*.

        Raises :class:`RunNotFound` if *run_id* is unknown.
        """
        self._require_exists(run_id)
        return self._statuses[run_id]

    def pending_count(self) -> int:
        """Return the number of runs still in *pending* status."""
        return sum(
            1 for s in self._statuses.values() if s is QueuedRunStatus.pending
        )

    def peek(self, limit: int | None = None) -> list[PendingRun]:
        """Return pending runs in priority order without removing them.

        Parameters
        ----------
        limit:
            Maximum number of runs to return.  ``None`` returns all.
        """
        pending = [
            (prio, count, run)
            for prio, count, run in self._heap
            if run.run_id not in self._removed
            and self._statuses.get(run.run_id) is QueuedRunStatus.pending
        ]
        pending.sort()
        runs = [run for _prio, _count, run in pending]
        if limit is not None:
            runs = runs[:limit]
        return runs

    @property
    def size(self) -> int:
        """Total number of tracked runs (all statuses)."""
        return len(self._statuses)

    def summary(self) -> dict[QueuedRunStatus, int]:
        """Return a count of runs by status."""
        counts: dict[QueuedRunStatus, int] = {}
        for s in self._statuses.values():
            counts[s] = counts.get(s, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require_exists(self, run_id: str) -> None:
        if run_id not in self._statuses:
            raise RunNotFound(f"run {run_id!r} not found in queue")
