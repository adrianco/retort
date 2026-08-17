"""Lifecycle persistence — the half the promotion subsystem never had.

`lifecycle.py` (candidate → screening → trial → production → retired) and
`changelog.py` ("immutable audit log") were both written and tested, and nothing
called them. `dashboard.py` says so outright: *"the promotion subsystem uses
in-memory changelogs"*. So no stack ever had a recorded state, and `retort
promote` evaluated a gate and echoed the verdict without promoting anything.
"""
from __future__ import annotations

import json

import pytest

from retort.promotion import store
from retort.promotion.gates import GateResult
from retort.promotion.lifecycle import LifecycleState, StackLifecycle


@pytest.fixture
def path(tmp_path):
    return tmp_path / "lifecycle.json"


def _passed():
    return GateResult(gate_name="screening_to_trial", passed=True, detail="ok")


def test_state_and_history_survive_a_round_trip(path):
    life = StackLifecycle()
    life.register("stack-a")
    life.promote("stack-a", _passed(), reason="auto")
    store.save(life, path)

    back = store.load(path)
    assert back.stacks["stack-a"] is LifecycleState.screening
    assert len(back.changelog) == len(life.changelog)
    assert back.changelog[0].reason == "initial registration"


def test_missing_file_loads_empty_rather_than_failing(path):
    assert store.load(path).stacks == {}


def test_corrupt_file_does_not_take_the_command_down(path):
    path.write_text("{not json")
    assert store.load(path).stacks == {}


def test_the_changelog_cannot_shrink(path):
    """An audit log that can lose entries is not an audit log."""
    life = StackLifecycle()
    life.register("stack-a")
    life.promote("stack-a", _passed())
    store.save(life, path)

    with pytest.raises(ValueError, match="append-only"):
        store.save(StackLifecycle(), path)          # a truncating write

    assert len(json.loads(path.read_text())["changelog"]) == 2


def test_appending_is_allowed(path):
    life = StackLifecycle()
    life.register("stack-a")
    store.save(life, path)

    life = store.load(path)
    life.promote("stack-a", _passed())
    store.save(life, path)

    assert len(store.load(path).changelog) == 2


def test_unknown_state_is_skipped_not_guessed(path):
    path.write_text(json.dumps({
        "states": {"good": "trial", "weird": "not-a-state"},
        "changelog": [],
    }))
    stacks = store.load(path).stacks
    assert stacks == {"good": LifecycleState.trial}


def test_timestamps_survive_serialisation(path):
    life = StackLifecycle()
    life.register("stack-a")
    store.save(life, path)
    assert store.load(path).changelog[0].timestamp == life.changelog[0].timestamp
