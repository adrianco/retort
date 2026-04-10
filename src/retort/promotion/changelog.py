"""Immutable audit log for lifecycle transitions.

Every state change is captured as a :class:`ChangelogEntry` and appended to a
list.  Entries are append-only — callers should never mutate or remove them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from retort.promotion.gates import GateResult


@dataclass(frozen=True)
class ChangelogEntry:
    """A single immutable record of a lifecycle transition."""

    stack_id: str
    from_state: str | None
    to_state: str
    timestamp: datetime
    gate_name: str | None
    gate_passed: bool | None
    gate_detail: str
    reason: str


def record_transition(
    changelog: list[ChangelogEntry],
    *,
    stack_id: str,
    from_state: str | None,
    to_state: str,
    gate_result: "GateResult | None",
    reason: str = "",
) -> ChangelogEntry:
    """Create a :class:`ChangelogEntry` and append it to *changelog*.

    Returns the newly created entry.
    """
    from_val = from_state.value if hasattr(from_state, "value") else from_state
    to_val = to_state.value if hasattr(to_state, "value") else to_state
    entry = ChangelogEntry(
        stack_id=stack_id,
        from_state=str(from_val) if from_val is not None else None,
        to_state=str(to_val),
        timestamp=datetime.now(timezone.utc),
        gate_name=gate_result.gate_name if gate_result else None,
        gate_passed=gate_result.passed if gate_result else None,
        gate_detail=gate_result.detail if gate_result else "",
        reason=reason,
    )
    changelog.append(entry)
    return entry


def get_changelog(
    changelog: list[ChangelogEntry],
    *,
    stack_id: str | None = None,
) -> list[ChangelogEntry]:
    """Return changelog entries, optionally filtered by *stack_id*."""
    if stack_id is None:
        return list(changelog)
    return [e for e in changelog if e.stack_id == stack_id]
