"""Persist the stack lifecycle and its changelog.

The lifecycle state machine (candidate → screening → trial → production →
retired) and the append-only changelog were both written and tested, but held
their state in memory only — `dashboard.py` says so outright: *"the promotion
subsystem uses in-memory changelogs, we look at design matrices that have moved
through lifecycle phases"*. Nothing survived the process, so no stack ever had a
recorded state, and `retort promote` echoed PASS/FAIL without promoting
anything. This is the missing half.

JSON beside `master.db`, not a new table: the changelog is described as an
IMMUTABLE AUDIT LOG, and this repo already treats its evidence as reviewable
files under git — a transition should show up in a diff. It is also
cheapest-to-reverse: delete the file and nothing else changes.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from retort.promotion.changelog import ChangelogEntry, record_transition
from retort.promotion.lifecycle import LifecycleState, StackLifecycle

DEFAULT_PATH = Path("lifecycle.json")

__all__ = ["load", "save", "DEFAULT_PATH", "ChangelogEntry", "record_transition"]


def load(path: Path = DEFAULT_PATH) -> StackLifecycle:
    """Read the lifecycle, or an empty one if it does not exist yet."""
    life = StackLifecycle()
    if not Path(path).exists():
        return life
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return life

    for stack_id, state in (data.get("states") or {}).items():
        try:
            life._states[stack_id] = LifecycleState(state)
        except ValueError:
            continue                      # unknown state: skip, never guess
    for e in data.get("changelog") or []:
        try:
            life.changelog.append(ChangelogEntry(
                stack_id=e["stack_id"],
                from_state=e.get("from_state"),
                to_state=e["to_state"],
                timestamp=datetime.fromisoformat(e["timestamp"]),
                gate_name=e.get("gate_name"),
                gate_passed=e.get("gate_passed"),
                gate_detail=e.get("gate_detail", ""),
                reason=e.get("reason", ""),
            ))
        except (KeyError, ValueError):
            continue
    return life


def save(life: StackLifecycle, path: Path = DEFAULT_PATH) -> Path:
    """Write the lifecycle out. The changelog is APPEND-ONLY by contract.

    Refuses to shrink the changelog: an audit log that can lose entries is not
    an audit log, and a truncating write here would silently erase the record of
    every promotion ever made.
    """
    path = Path(path)
    if path.exists():
        try:
            existing = len(json.loads(path.read_text()).get("changelog") or [])
        except (OSError, ValueError):
            existing = 0
        if len(life.changelog) < existing:
            raise ValueError(
                f"refusing to write {path}: it holds {existing} changelog "
                f"entries and this write has {len(life.changelog)}. The "
                f"changelog is append-only; load it before saving."
            )

    payload = {
        "_note": ("Stack lifecycle and its append-only transition log. "
                  "Written by `retort promote`. Safe to read; do not hand-edit "
                  "the changelog."),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "states": {k: v.value for k, v in life.stacks.items()},
        "changelog": [
            {**asdict(e), "timestamp": e.timestamp.isoformat()}
            for e in life.changelog
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=False))
    return path
