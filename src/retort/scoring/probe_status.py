"""A breadcrumb so the live monitor can see runtime scoring in progress.

`retort monitor` finds in-flight work by looking for the AGENT process under
`retort run` (`claude`, `codex`, `hermes`, …). The runtime and factual probes
have no agent: they launch the program the model wrote — `npm start`, a Rust
binary, a JVM — so for the whole scoring phase the monitor saw a live `retort
run` with no recognizable child and reported the cell as not started. A run that
was working looked hung, which is the same confusion this project keeps hitting
in a different costume: an absent measurement and a stalled one are
indistinguishable unless something says which.

So the probes announce themselves. The scorer runs in-process inside `retort
run`, so `os.getpid()` here IS the pid the monitor already resolved for the
experiment, and the file it writes is keyed by that pid — no discovery needed.

Every operation is best-effort and silent: a monitor breadcrumb must never be
able to fail a run.
"""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path


def _dir(base: str | None = None) -> Path:
    root = Path(base).expanduser() if base else (
        Path(os.environ.get("RETORT_HOME", Path.home() / ".retort")))
    return root / "state" / "probe"


def _path(pid: int | None = None, base: str | None = None) -> Path:
    return _dir(base) / f"{pid or os.getpid()}.json"


def announce(phase: str, label: str = "", base: str | None = None) -> None:
    """Record what the probe is doing right now. Never raises."""
    try:
        d = _dir(base)
        d.mkdir(parents=True, exist_ok=True)
        tmp = _path(base=base).with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "pid": os.getpid(), "phase": phase, "label": label,
            "updated": time.time(),
        }))
        tmp.replace(_path(base=base))
    except Exception:  # noqa: BLE001 — a status file must never break scoring
        pass


def clear(base: str | None = None) -> None:
    """Drop the breadcrumb. Never raises."""
    try:
        _path(base=base).unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass


def read(pid: int, base: str | None = None, max_age_s: float = 300.0) -> dict | None:
    """The probe phase for `pid`, or None if there isn't a fresh one.

    Stale files are ignored rather than deleted: a crashed run leaves one behind,
    and reporting "measuring runtime" for a process that died an hour ago would
    be worse than reporting nothing.
    """
    try:
        data = json.loads(_path(pid, base).read_text())
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None
    updated = data.get("updated")
    if not isinstance(updated, (int, float)) or time.time() - updated > max_age_s:
        return None
    return data


@contextmanager
def announcing(phase: str, label: str = "", base: str | None = None):
    """Announce for the duration of a block, then clear."""
    announce(phase, label, base)
    try:
        yield lambda p: announce(p, label, base)
    finally:
        clear(base)
