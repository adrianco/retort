"""Tests for the adaptive per-run timeout estimator (_estimate_run_timeout).

The estimator must only ever *extend* the configured budget — never shorten it
below ``timeout_minutes`` — so that early, history-poor runs are not killed
under budget (which produced false all-zeros timeouts in experiment 5).
"""

from __future__ import annotations

import json

from retort.cli import _estimate_run_timeout
from retort.storage.models import ExperimentRun, RunResult, RunStatus


def _add_completed(session, factors: dict, duration_s: float) -> None:
    run = ExperimentRun(
        design_row_id=None,
        replicate=1,
        status=RunStatus.completed,
        run_config_json=json.dumps(factors),
    )
    session.add(run)
    session.flush()
    session.add(
        RunResult(run_id=run.id, metric_name="_duration_seconds", value=duration_s)
    )
    session.flush()


PY_NONE = {"language": "python", "model": "claude-opus-4-8", "tooling": "none"}


def test_no_history_returns_fallback(db_session):
    assert _estimate_run_timeout(db_session, PY_NONE, 45) == 45


def test_short_history_floors_at_configured_budget(db_session):
    # A fast prior python run (600s) would naively suggest ~15 min. The floor
    # must keep the budget at the configured 45 min — this is the bug fix.
    _add_completed(db_session, {**PY_NONE, "tooling": "beads"}, 600)
    assert _estimate_run_timeout(db_session, PY_NONE, 45) == 45


def test_long_history_extends_above_budget(db_session):
    # A 2400s prior run -> ceil(2400*1.5/60) = 60 min, above the 45 floor.
    _add_completed(db_session, PY_NONE, 2400)
    assert _estimate_run_timeout(db_session, PY_NONE, 45) == 60


def test_extension_clamped_to_three_x(db_session):
    # A very long prior run must not extend beyond 3x the configured budget.
    _add_completed(db_session, PY_NONE, 7200)  # would be 180 min uncapped
    assert _estimate_run_timeout(db_session, PY_NONE, 45) == 135  # 45 * 3


def test_exact_config_preferred_over_language(db_session):
    # Exact-config history (1800s) wins over a same-language but different cell.
    _add_completed(db_session, PY_NONE, 1800)  # ceil(1800*1.5/60)=45
    _add_completed(db_session, {**PY_NONE, "tooling": "beads"}, 7200)
    # Uses exact (1800s -> 45), not the 7200s beads run.
    assert _estimate_run_timeout(db_session, PY_NONE, 30) == 45
