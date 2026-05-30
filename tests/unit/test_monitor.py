"""Tests for the live run monitor (retort.reporting.monitor)."""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta, timezone

from retort.reporting.monitor import (
    build_snapshot,
    render_json,
    render_text,
)
from retort.storage.models import (
    DesignMatrix,
    DesignMatrixRow,
    ExperimentRun,
    LifecyclePhase,
    RunResult,
    RunStatus,
)

T0 = datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc)
NOW = T0 + timedelta(hours=1)


def _add_design_cells(session, n: int) -> None:
    dm = DesignMatrix(name="t", phase=LifecyclePhase.screening, resolution=3)
    session.add(dm)
    session.flush()
    for i in range(n):
        session.add(DesignMatrixRow(matrix_id=dm.id, row_index=i))
    session.flush()


def _add_run(
    session, factors, replicate, status, metrics, *, finished=None, error=None
):
    run = ExperimentRun(
        design_row_id=None,
        replicate=replicate,
        status=status,
        started_at=T0,
        finished_at=finished,
        error_message=error,
        run_config_json=_json.dumps(factors),
    )
    session.add(run)
    session.flush()
    for name, val in metrics.items():
        session.add(RunResult(run_id=run.id, metric_name=name, value=val))
    session.flush()
    return run


def _seed(session):
    _add_design_cells(session, 2)  # 2 cells
    a = {"language": "go", "model": "claude-opus-4-7", "tooling": "none"}
    b = {"language": "python", "model": "claude-opus-4-8", "tooling": "beads"}
    _add_run(
        session, a, 1, RunStatus.completed,
        {"code_quality": 1.0, "test_coverage": 0.8, "_cost_usd": 5.0,
         "_tokens": 6_000_000, "_duration_seconds": 1000},
        finished=T0 + timedelta(seconds=1000),
    )
    _add_run(
        session, a, 2, RunStatus.completed,
        {"code_quality": 1.0, "test_coverage": 0.6, "_cost_usd": 5.0,
         "_tokens": 4_000_000, "_duration_seconds": 900},
        finished=T0 + timedelta(seconds=2000),
    )
    _add_run(
        session, b, 1, RunStatus.completed,
        {"code_quality": 0.83, "test_coverage": 0.9, "_cost_usd": 4.0,
         "_tokens": 5_000_000, "_duration_seconds": 800},
        finished=T0 + timedelta(seconds=3000),
    )
    _add_run(session, b, 2, RunStatus.failed, {}, error="boom: tests did not run")


def test_counts_and_progress(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    assert snap.completed == 3
    assert snap.failed == 1
    assert snap.design_cells == 2
    assert snap.expected_total == 6  # 2 cells × 3 reps
    assert snap.terminal == 4
    assert snap.remaining == 2
    assert round(snap.pct_complete, 2) == round(4 / 6 * 100, 2)
    assert snap.is_done is False


def test_resource_totals(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    assert snap.total_cost_usd == 14.0
    assert snap.total_tokens == 15_000_000
    assert snap.mean_duration_s == (1000 + 900 + 800) / 3


def test_per_cell_aggregation(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    cells = {c.label: c for c in snap.cells}
    go = cells["go/claude-opus-4-7/none"]
    assert go.completed == 2
    assert go.cost_usd == 10.0
    assert go.metric_means["code_quality"] == 1.0
    assert abs(go.metric_means["test_coverage"] - 0.7) < 1e-9
    py = cells["python/claude-opus-4-8/beads"]
    assert py.completed == 1
    assert py.failed == 1
    # resource metrics must not leak into quality means
    assert "_cost_usd" not in go.metric_means


def test_throughput_and_eta(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    # wall elapsed = 1h from T0 to NOW; 3 completed -> 3 runs/hr
    assert abs(snap.throughput_per_hour - 3.0) < 1e-9
    # 2 remaining at 3/hr -> 2400s
    assert abs(snap.eta_seconds - 2400.0) < 1e-6
    assert snap.eta_finish == NOW + timedelta(seconds=2400)


def test_expected_total_override(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, expected_total=10, now=NOW)
    assert snap.expected_total == 10
    assert snap.remaining == 6  # 10 - 4 terminal


def test_unknown_total_when_no_hint(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, now=NOW)
    assert snap.expected_total is None
    assert snap.remaining is None
    assert snap.pct_complete is None


def test_is_done_when_all_terminal(db_session):
    _add_design_cells(db_session, 1)
    f = {"language": "go", "model": "claude-opus-4-8", "tooling": "none"}
    _add_run(
        db_session, f, 1, RunStatus.completed,
        {"_cost_usd": 1.0, "_duration_seconds": 10},
        finished=T0 + timedelta(seconds=10),
    )
    snap = build_snapshot(db_session, replicates=1, now=NOW)
    assert snap.is_done is True
    assert snap.remaining == 0
    assert snap.eta_seconds == 0.0


def test_failures_captured(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    assert len(snap.failures) == 1
    assert snap.failures[0]["label"] == "python/claude-opus-4-8/beads"
    assert "boom" in snap.failures[0]["error"]


def test_render_text_contains_key_fields(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    out = render_text(snap, db_path="/tmp/retort.db")
    assert "Retort run monitor" in out
    assert "4 / 6" in out  # terminal / expected
    assert "$14.00" in out
    assert "Failures (1)" in out
    assert "go/claude-opus-4-7/none" in out


def test_render_json_roundtrip(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    data = _json.loads(render_json(snap))
    assert data["completed"] == 3
    assert data["failed"] == 1
    assert data["remaining"] == 2
    assert data["expected_total"] == 6
    assert data["is_done"] is False
    assert any(c["label"] == "go/claude-opus-4-7/none" for c in data["cells"])
