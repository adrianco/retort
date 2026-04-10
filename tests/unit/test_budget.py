"""Tests for the scheduler budget tracker."""

from __future__ import annotations

import pytest

from retort.scheduler.budget import (
    BudgetExhausted,
    BudgetTracker,
    CostEntry,
    PhaseReport,
)
from retort.storage.models import LifecyclePhase


@pytest.fixture
def tracker() -> BudgetTracker:
    return BudgetTracker()


@pytest.fixture
def capped_tracker() -> BudgetTracker:
    """Tracker with a $100 screening limit and $500 trial limit."""
    return BudgetTracker(
        limits={
            LifecyclePhase.screening: 100.0,
            LifecyclePhase.trial: 500.0,
        }
    )


class TestSetLimit:
    def test_set_limit(self, tracker: BudgetTracker):
        tracker.set_limit(LifecyclePhase.screening, 200.0)
        assert tracker.limits[LifecyclePhase.screening] == 200.0

    def test_set_limit_zero(self, tracker: BudgetTracker):
        tracker.set_limit(LifecyclePhase.screening, 0.0)
        assert tracker.limits[LifecyclePhase.screening] == 0.0

    def test_set_limit_negative_raises(self, tracker: BudgetTracker):
        with pytest.raises(ValueError, match="non-negative"):
            tracker.set_limit(LifecyclePhase.screening, -1.0)

    def test_set_limit_overwrites(self, tracker: BudgetTracker):
        tracker.set_limit(LifecyclePhase.screening, 100.0)
        tracker.set_limit(LifecyclePhase.screening, 200.0)
        assert tracker.limits[LifecyclePhase.screening] == 200.0


class TestRecord:
    def test_record_returns_entry(self, tracker: BudgetTracker):
        entry = tracker.record(LifecyclePhase.screening, 10.0, "run-1")
        assert isinstance(entry, CostEntry)
        assert entry.phase is LifecyclePhase.screening
        assert entry.amount_usd == 10.0
        assert entry.description == "run-1"

    def test_record_accumulates(self, tracker: BudgetTracker):
        tracker.record(LifecyclePhase.screening, 10.0)
        tracker.record(LifecyclePhase.screening, 25.0)
        assert tracker.spend(LifecyclePhase.screening) == 35.0

    def test_record_negative_raises(self, tracker: BudgetTracker):
        with pytest.raises(ValueError, match="non-negative"):
            tracker.record(LifecyclePhase.screening, -5.0)

    def test_record_exceeds_limit_raises(self, capped_tracker: BudgetTracker):
        capped_tracker.record(LifecyclePhase.screening, 90.0)
        with pytest.raises(BudgetExhausted, match="exceed budget"):
            capped_tracker.record(LifecyclePhase.screening, 20.0)

    def test_record_exactly_at_limit(self, capped_tracker: BudgetTracker):
        # Recording exactly up to the limit should succeed
        capped_tracker.record(LifecyclePhase.screening, 100.0)
        assert capped_tracker.spend(LifecyclePhase.screening) == 100.0

    def test_record_no_limit_allows_any_amount(self, tracker: BudgetTracker):
        tracker.record(LifecyclePhase.screening, 999999.0)
        assert tracker.spend(LifecyclePhase.screening) == 999999.0

    def test_record_phases_independent(self, capped_tracker: BudgetTracker):
        capped_tracker.record(LifecyclePhase.screening, 90.0)
        # Trial has its own $500 limit — this should not be affected
        capped_tracker.record(LifecyclePhase.trial, 400.0)
        assert capped_tracker.spend(LifecyclePhase.trial) == 400.0


class TestQueries:
    def test_spend_empty(self, tracker: BudgetTracker):
        assert tracker.spend(LifecyclePhase.screening) == 0.0

    def test_remaining_with_limit(self, capped_tracker: BudgetTracker):
        capped_tracker.record(LifecyclePhase.screening, 30.0)
        assert capped_tracker.remaining(LifecyclePhase.screening) == 70.0

    def test_remaining_no_limit(self, tracker: BudgetTracker):
        assert tracker.remaining(LifecyclePhase.screening) is None

    def test_remaining_exhausted_returns_zero(self, capped_tracker: BudgetTracker):
        capped_tracker.record(LifecyclePhase.screening, 100.0)
        assert capped_tracker.remaining(LifecyclePhase.screening) == 0.0

    def test_is_exhausted_true(self, capped_tracker: BudgetTracker):
        capped_tracker.record(LifecyclePhase.screening, 100.0)
        assert capped_tracker.is_exhausted(LifecyclePhase.screening) is True

    def test_is_exhausted_false(self, capped_tracker: BudgetTracker):
        capped_tracker.record(LifecyclePhase.screening, 50.0)
        assert capped_tracker.is_exhausted(LifecyclePhase.screening) is False

    def test_is_exhausted_no_limit(self, tracker: BudgetTracker):
        tracker.record(LifecyclePhase.screening, 999999.0)
        assert tracker.is_exhausted(LifecyclePhase.screening) is False

    def test_entries_all(self, tracker: BudgetTracker):
        tracker.record(LifecyclePhase.screening, 10.0)
        tracker.record(LifecyclePhase.trial, 20.0)
        assert len(tracker.entries()) == 2

    def test_entries_filtered(self, tracker: BudgetTracker):
        tracker.record(LifecyclePhase.screening, 10.0)
        tracker.record(LifecyclePhase.trial, 20.0)
        screening = tracker.entries(LifecyclePhase.screening)
        assert len(screening) == 1
        assert screening[0].phase is LifecyclePhase.screening


class TestReporting:
    def test_phase_report(self, capped_tracker: BudgetTracker):
        capped_tracker.record(LifecyclePhase.screening, 30.0, "run-1")
        capped_tracker.record(LifecyclePhase.screening, 20.0, "run-2")
        report = capped_tracker.phase_report(LifecyclePhase.screening)
        assert isinstance(report, PhaseReport)
        assert report.phase is LifecyclePhase.screening
        assert report.total_spend_usd == 50.0
        assert report.limit_usd == 100.0
        assert report.remaining_usd == 50.0
        assert report.num_entries == 2
        assert report.is_exhausted is False

    def test_report_includes_all_active_phases(self, capped_tracker: BudgetTracker):
        capped_tracker.record(LifecyclePhase.screening, 10.0)
        reports = capped_tracker.report()
        # screening has activity, trial has a limit but no activity
        phase_names = [r.phase for r in reports]
        assert LifecyclePhase.screening in phase_names
        assert LifecyclePhase.trial in phase_names

    def test_report_empty_tracker(self, tracker: BudgetTracker):
        reports = tracker.report()
        assert reports == []
