"""Tests for the live run monitor (retort.reporting.monitor)."""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta, timezone

from retort.reporting.monitor import (
    build_snapshot,
    render_active,
    render_json,
    render_text,
    resolve_target,
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
    assert snap.terminal == 4  # rows with a terminal status (completed + failed)
    # Progress counts completed only; the failed run is pending retry, not done.
    assert snap.remaining == 3  # 6 expected - 3 completed
    assert round(snap.pct_complete, 2) == round(3 / 6 * 100, 2)
    assert snap.all_terminal is False  # 4 terminal < 6 expected
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
    assert go.mean_duration_s == (1000 + 900) / 2  # mean per-run duration
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
    # 3 remaining (6 expected - 3 completed) at 3/hr -> 3600s
    assert abs(snap.eta_seconds - 3600.0) < 1e-6
    assert snap.eta_finish == NOW + timedelta(seconds=3600)


def test_throughput_uses_recent_session_only(db_session):
    """A --resume run's pace ignores the idle gap before old completed runs."""
    _add_design_cells(db_session, 24)  # expected 72
    old = T0 - timedelta(days=2)  # prior session, long ago
    for i in range(2):
        _add_run(
            db_session, {"language": "go", "tooling": f"old{i}"}, 1,
            RunStatus.completed, {"_duration_seconds": 600},
        )
    # Overwrite their started_at to the old session.
    for run in db_session.query(ExperimentRun).all():
        run.started_at = old
        run.finished_at = old + timedelta(seconds=600)
    db_session.flush()
    # New session: 2 runs started this hour.
    for i in range(2):
        r = ExperimentRun(
            design_row_id=None, replicate=1, status=RunStatus.completed,
            started_at=T0, finished_at=T0 + timedelta(seconds=600),
            run_config_json=_json.dumps({"language": "rust", "tooling": f"new{i}"}),
        )
        db_session.add(r)
        db_session.flush()
        db_session.add(
            RunResult(run_id=r.id, metric_name="_duration_seconds", value=600)
        )
    db_session.flush()
    snap = build_snapshot(db_session, replicates=3, now=NOW)  # NOW = T0 + 1h
    # Recent session = 2 runs over 1h -> 2/hr, NOT 4 runs / 2 days.
    assert abs(snap.throughput_per_hour - 2.0) < 1e-6


def test_expected_total_override(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, expected_total=10, now=NOW)
    assert snap.expected_total == 10
    assert snap.remaining == 7  # 10 expected - 3 completed (failed != progress)


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


def test_is_done_false_when_failures_pending_retry(db_session):
    """Regression: all slots terminal but completed < expected must NOT be done
    (the --watch one-shot bug: completed+failed==expected exited after 1 render).
    """
    _add_design_cells(db_session, 2)  # 2 cells x 3 reps = 6
    for i in range(2):
        _add_run(db_session, {"language": "go", "tooling": f"c{i}"}, 1,
                 RunStatus.completed, {"_duration_seconds": 60},
                 finished=T0 + timedelta(seconds=60 * (i + 1)))
    for i in range(4):
        _add_run(db_session, {"language": "rust", "tooling": f"f{i}"}, 1,
                 RunStatus.failed, {}, error="Timeout")
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    assert snap.completed == 2
    assert snap.failed == 4
    assert snap.terminal == 6          # all slots hold a terminal row...
    assert snap.all_terminal is True   # ...so all_terminal is True...
    assert snap.is_done is False       # ...but the run is NOT done (4 to retry)


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
    assert "3 / 6" in out  # completed / expected (not 4 — failed isn't progress)
    assert "~dur" in out  # cells table has a per-run duration column
    assert "15m50s" in out  # go cell mean duration (1000+900)/2 = 950s
    assert "Recent completions:" in out
    # date stamp on recent completions (finished_at), shown in LOCAL time
    latest_local = (T0 + timedelta(seconds=3000)).astimezone().strftime("%m-%d %H:%M")
    assert latest_local in out
    assert "1 failed, pending retry" in out
    assert "$14.00" in out
    assert "Failures (1)" in out
    assert "go/claude-opus-4-7/none" in out


def test_render_text_caps_failures(db_session):
    """Text report shows only the last 5 failures (full list stays in --json)."""
    _add_design_cells(db_session, 24)
    for i in range(8):
        _add_run(db_session, {"language": "go", "tooling": f"f{i}"}, 1,
                 RunStatus.failed, {}, error=f"Timeout {i}")
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    out = render_text(snap)
    assert "Failures (8) — showing last 5 of 8" in out
    assert out.count("✗ go/f") == 5         # only 5 failure lines rendered
    assert len(_json.loads(render_json(snap))["failures"]) == 8  # JSON keeps all


def test_render_json_roundtrip(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    data = _json.loads(render_json(snap))
    assert data["completed"] == 3
    assert data["failed"] == 1
    assert data["remaining"] == 3  # 6 expected - 3 completed
    assert data["expected_total"] == 6
    assert data["is_done"] is False
    assert any(c["label"] == "go/claude-opus-4-7/none" for c in data["cells"])


def test_stale_failures_are_not_progress(db_session):
    """Regression: a --retry-failed run with mostly stale failures must not
    read as 'almost done' (the exp-5 bug: 9 completed + 62 failed showed 98.6%).
    """
    _add_design_cells(db_session, 24)  # 24 cells x 3 reps = 72
    # 3 completed, 9 failed (stale, awaiting retry)
    for i in range(3):
        _add_run(
            db_session, {"language": "go", "tooling": f"c{i}"}, 1,
            RunStatus.completed, {"_duration_seconds": 600, "code_quality": 1.0},
            finished=T0 + timedelta(seconds=600 * (i + 1)),
        )
    for i in range(9):
        _add_run(db_session, {"language": "rust", "tooling": f"f{i}"}, 1,
                 RunStatus.failed, {}, error="Timeout")
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    assert snap.completed == 3
    assert snap.failed == 9
    assert snap.expected_total == 72
    assert snap.remaining == 69        # 72 - 3 completed, NOT 72 - 12
    assert round(snap.pct_complete) == 4  # ~4%, not ~17%
    assert snap.is_done is False
    out = render_text(snap)
    assert "3 / 72" in out
    assert "9 failed, pending retry" in out


def test_render_active_empty():
    assert render_active([]) == []


def test_render_active_lists_running_and_evaluating():
    active = [
        {"label": "go/claude-opus-4-8/none", "replicate": None,
         "elapsed_s": 800, "evaluating": False},
        {"label": "python/claude-opus-4-8/none", "replicate": None,
         "elapsed_s": 120, "evaluating": True},
    ]
    out = "\n".join(render_active(active))
    assert "Active now (2):" in out
    assert "▶ go/claude-opus-4-8/none  running 13m20s" in out
    assert "▶ python/claude-opus-4-8/none  evaluating 2m00s" in out


def test_render_text_includes_active_section(db_session):
    _seed(db_session)
    snap = build_snapshot(db_session, replicates=3, now=NOW)
    active = [{"label": "rust/claude-opus-4-8/none", "elapsed_s": 300,
               "evaluating": False}]
    out = render_text(snap, active=active)
    assert "Active now (1):" in out
    assert "rust/claude-opus-4-8/none  running 5m00s" in out
    # and JSON carries it too
    data = _json.loads(render_json(snap, active=active))
    assert data["active"][0]["label"] == "rust/claude-opus-4-8/none"


def test_etime_to_seconds():
    from retort.cli import _etime_to_seconds
    assert _etime_to_seconds("05:30") == 330
    assert _etime_to_seconds("01:02:03") == 3723
    assert _etime_to_seconds("2-01:00:00") == 2 * 86400 + 3600
    assert _etime_to_seconds("") is None


def test_resolve_target_directory(tmp_path):
    exp = tmp_path / "experiment-5"
    exp.mkdir()
    (exp / "retort.db").write_text("")
    (exp / "workspace.yaml").write_text("x")
    db, cfg = resolve_target(str(exp))
    assert db == exp / "retort.db"
    assert cfg == exp / "workspace.yaml"


def test_resolve_target_db_file(tmp_path):
    exp = tmp_path / "experiment-6"
    exp.mkdir()
    dbf = exp / "retort.db"
    dbf.write_text("")
    (exp / "workspace.yaml").write_text("x")
    db, cfg = resolve_target(str(dbf))
    assert db == dbf
    assert cfg == exp / "workspace.yaml"


def test_resolve_target_explicit_overrides(tmp_path):
    exp = tmp_path / "experiment-7"
    exp.mkdir()
    other = tmp_path / "other.db"
    other.write_text("")
    db, cfg = resolve_target(str(exp), db=str(other), config=None)
    assert db == other  # explicit --db wins over inferred


def test_resolve_target_requires_something():
    import pytest

    with pytest.raises(ValueError):
        resolve_target(None, None, None)
