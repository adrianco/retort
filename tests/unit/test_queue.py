"""Tests for the scheduler run queue."""

from __future__ import annotations

import pytest

from retort.scheduler.queue import (
    PendingRun,
    QueuedRunStatus,
    RunNotFound,
    RunQueue,
)
from retort.storage.models import LifecyclePhase


@pytest.fixture
def queue() -> RunQueue:
    return RunQueue()


def _run(
    run_id: str,
    phase: LifecyclePhase = LifecyclePhase.screening,
    priority: int | None = None,
    estimated_cost_usd: float | None = None,
) -> PendingRun:
    return PendingRun(
        run_id=run_id,
        phase=phase,
        priority=priority,
        run_config={"language": "python"},
        estimated_cost_usd=estimated_cost_usd,
    )


class TestPendingRun:
    def test_effective_priority_from_phase(self):
        run = _run("r1", phase=LifecyclePhase.screening)
        assert run.effective_priority == 0

    def test_effective_priority_from_override(self):
        run = _run("r1", phase=LifecyclePhase.screening, priority=99)
        assert run.effective_priority == 99

    def test_effective_priority_trial(self):
        run = _run("r1", phase=LifecyclePhase.trial)
        assert run.effective_priority == 1


class TestEnqueue:
    def test_enqueue_single(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        assert queue.size == 1
        assert queue.pending_count() == 1

    def test_enqueue_duplicate_raises(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        with pytest.raises(ValueError, match="already in the queue"):
            queue.enqueue(_run("r1"))

    def test_enqueue_multiple(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.enqueue(_run("r3"))
        assert queue.size == 3


class TestDequeue:
    def test_dequeue_empty(self, queue: RunQueue):
        assert queue.dequeue() is None

    def test_dequeue_fifo_same_priority(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.enqueue(_run("r3"))
        assert queue.dequeue().run_id == "r1"
        assert queue.dequeue().run_id == "r2"
        assert queue.dequeue().run_id == "r3"

    def test_dequeue_respects_phase_priority(self, queue: RunQueue):
        queue.enqueue(_run("trial-1", phase=LifecyclePhase.trial))
        queue.enqueue(_run("screen-1", phase=LifecyclePhase.screening))
        queue.enqueue(_run("prod-1", phase=LifecyclePhase.production))
        # Screening (0) < Trial (1) < Production (2)
        assert queue.dequeue().run_id == "screen-1"
        assert queue.dequeue().run_id == "trial-1"
        assert queue.dequeue().run_id == "prod-1"

    def test_dequeue_respects_explicit_priority(self, queue: RunQueue):
        queue.enqueue(_run("low", priority=10))
        queue.enqueue(_run("high", priority=1))
        assert queue.dequeue().run_id == "high"
        assert queue.dequeue().run_id == "low"

    def test_dequeue_sets_executing(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.dequeue()
        assert queue.status("r1") is QueuedRunStatus.executing

    def test_dequeue_skips_cancelled(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.cancel("r1")
        result = queue.dequeue()
        assert result.run_id == "r2"


class TestStatusTransitions:
    def test_mark_completed(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.dequeue()
        queue.mark_completed("r1")
        assert queue.status("r1") is QueuedRunStatus.completed

    def test_mark_failed(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.dequeue()
        queue.mark_failed("r1")
        assert queue.status("r1") is QueuedRunStatus.failed

    def test_cancel_pending(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.cancel("r1")
        assert queue.status("r1") is QueuedRunStatus.cancelled

    def test_unknown_run_raises(self, queue: RunQueue):
        with pytest.raises(RunNotFound, match="not found"):
            queue.mark_completed("nope")

    def test_status_unknown_raises(self, queue: RunQueue):
        with pytest.raises(RunNotFound, match="not found"):
            queue.status("nope")

    def test_cancel_unknown_raises(self, queue: RunQueue):
        with pytest.raises(RunNotFound, match="not found"):
            queue.cancel("nope")


class TestQueries:
    def test_pending_count(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.enqueue(_run("r3"))
        queue.dequeue()  # r1 → executing
        assert queue.pending_count() == 2

    def test_peek_returns_ordered(self, queue: RunQueue):
        queue.enqueue(_run("trial-1", phase=LifecyclePhase.trial))
        queue.enqueue(_run("screen-1", phase=LifecyclePhase.screening))
        runs = queue.peek()
        assert [r.run_id for r in runs] == ["screen-1", "trial-1"]

    def test_peek_with_limit(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.enqueue(_run("r3"))
        runs = queue.peek(limit=2)
        assert len(runs) == 2

    def test_peek_excludes_cancelled(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.cancel("r1")
        runs = queue.peek()
        assert [r.run_id for r in runs] == ["r2"]

    def test_peek_excludes_executing(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.dequeue()  # r1 → executing
        runs = queue.peek()
        assert [r.run_id for r in runs] == ["r2"]

    def test_summary(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.enqueue(_run("r3"))
        queue.dequeue()  # r1 → executing
        queue.cancel("r3")
        summary = queue.summary()
        assert summary[QueuedRunStatus.executing] == 1
        assert summary[QueuedRunStatus.pending] == 1
        assert summary[QueuedRunStatus.cancelled] == 1

    def test_size(self, queue: RunQueue):
        queue.enqueue(_run("r1"))
        queue.enqueue(_run("r2"))
        queue.dequeue()
        queue.mark_completed("r1")
        # size tracks all runs regardless of status
        assert queue.size == 2
