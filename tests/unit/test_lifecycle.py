"""Tests for the promotion lifecycle state machine."""

from __future__ import annotations

import pytest

from retort.promotion.changelog import ChangelogEntry
from retort.promotion.gates import GateResult
from retort.promotion.lifecycle import (
    InvalidTransition,
    LifecycleState,
    StackLifecycle,
)


@pytest.fixture
def lifecycle() -> StackLifecycle:
    return StackLifecycle()


def _pass_gate(name: str = "test") -> GateResult:
    return GateResult(passed=True, gate_name=name, detail="ok")


def _fail_gate(name: str = "test") -> GateResult:
    return GateResult(passed=False, gate_name=name, detail="threshold not met")


class TestRegister:
    def test_register_new_stack(self, lifecycle: StackLifecycle):
        state = lifecycle.register("stack-a")
        assert state is LifecycleState.candidate

    def test_register_duplicate_raises(self, lifecycle: StackLifecycle):
        lifecycle.register("stack-a")
        with pytest.raises(ValueError, match="already registered"):
            lifecycle.register("stack-a")

    def test_register_creates_changelog_entry(self, lifecycle: StackLifecycle):
        lifecycle.register("stack-a")
        assert len(lifecycle.changelog) == 1
        entry: ChangelogEntry = lifecycle.changelog[0]
        assert entry.stack_id == "stack-a"
        assert entry.from_state is None
        assert entry.to_state == "candidate"


class TestState:
    def test_state_returns_current(self, lifecycle: StackLifecycle):
        lifecycle.register("x")
        assert lifecycle.state("x") is LifecycleState.candidate

    def test_state_unknown_raises(self, lifecycle: StackLifecycle):
        with pytest.raises(KeyError, match="not registered"):
            lifecycle.state("nope")


class TestPromote:
    def test_candidate_to_screening_automatic(self, lifecycle: StackLifecycle):
        lifecycle.register("s1")
        new = lifecycle.promote("s1", _fail_gate())  # gate ignored for this edge
        assert new is LifecycleState.screening

    def test_screening_to_trial_pass(self, lifecycle: StackLifecycle):
        lifecycle.register("s1")
        lifecycle.promote("s1", _pass_gate())
        new = lifecycle.promote("s1", _pass_gate("screening_to_trial"))
        assert new is LifecycleState.trial

    def test_screening_to_trial_fail(self, lifecycle: StackLifecycle):
        lifecycle.register("s1")
        lifecycle.promote("s1", _pass_gate())  # → screening
        with pytest.raises(InvalidTransition, match="did not pass"):
            lifecycle.promote("s1", _fail_gate("screening_to_trial"))
        assert lifecycle.state("s1") is LifecycleState.screening  # unchanged

    def test_full_lifecycle(self, lifecycle: StackLifecycle):
        lifecycle.register("s1")
        lifecycle.promote("s1", _pass_gate())                      # → screening
        lifecycle.promote("s1", _pass_gate("screening_to_trial"))  # → trial
        lifecycle.promote("s1", _pass_gate("trial_to_production")) # → production
        lifecycle.promote("s1", _pass_gate("production_to_retired"))  # → retired
        assert lifecycle.state("s1") is LifecycleState.retired

    def test_promote_terminal_raises(self, lifecycle: StackLifecycle):
        lifecycle.register("s1")
        lifecycle.promote("s1", _pass_gate())
        lifecycle.promote("s1", _pass_gate())
        lifecycle.promote("s1", _pass_gate())
        lifecycle.promote("s1", _pass_gate())
        with pytest.raises(InvalidTransition, match="terminal state"):
            lifecycle.promote("s1", _pass_gate())

    def test_promote_unknown_stack_raises(self, lifecycle: StackLifecycle):
        with pytest.raises(KeyError):
            lifecycle.promote("nope", _pass_gate())

    def test_promote_records_changelog(self, lifecycle: StackLifecycle):
        lifecycle.register("s1")
        lifecycle.promote("s1", _pass_gate(), reason="automated")
        # register + promote = 2 entries
        assert len(lifecycle.changelog) == 2
        entry = lifecycle.changelog[-1]
        assert entry.from_state == "candidate"
        assert entry.to_state == "screening"
        assert entry.reason == "automated"


class TestStacks:
    def test_stacks_snapshot(self, lifecycle: StackLifecycle):
        lifecycle.register("a")
        lifecycle.register("b")
        lifecycle.promote("a", _pass_gate())
        snap = lifecycle.stacks
        assert snap == {"a": LifecycleState.screening, "b": LifecycleState.candidate}

    def test_stacks_in(self, lifecycle: StackLifecycle):
        lifecycle.register("a")
        lifecycle.register("b")
        lifecycle.promote("a", _pass_gate())
        assert lifecycle.stacks_in(LifecycleState.candidate) == ["b"]
        assert lifecycle.stacks_in(LifecycleState.screening) == ["a"]
