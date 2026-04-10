"""Promotion subsystem — lifecycle state machine, gates, and changelog."""

from retort.promotion.changelog import ChangelogEntry, get_changelog, record_transition
from retort.promotion.gates import GateResult, evaluate_gate
from retort.promotion.lifecycle import LifecycleState, StackLifecycle

__all__ = [
    "ChangelogEntry",
    "GateResult",
    "LifecycleState",
    "StackLifecycle",
    "evaluate_gate",
    "get_changelog",
    "record_transition",
]
