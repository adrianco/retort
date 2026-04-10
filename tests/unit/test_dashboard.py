"""Tests for the dashboard reporting module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner
from sqlalchemy.orm import Session

from retort.cli import main as cli
from retort.reporting.dashboard import (
    BudgetSummary,
    DashboardReport,
    ExperimentSummary,
    LifecycleSummary,
    PromotionEntry,
    build_dashboard,
    gather_budget,
    gather_experiments,
    gather_lifecycle,
    gather_promotions,
    render_json,
    render_text,
)
from retort.storage.models import (
    DesignMatrix,
    DesignMatrixRow,
    ExperimentRun,
    LifecyclePhase,
    RunStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def populated_session(db_session: Session) -> Session:
    """Session with two design matrices and several runs."""
    # Matrix 1: screening with mixed run statuses
    m1 = DesignMatrix(
        name="screening-v1",
        phase=LifecyclePhase.screening,
        resolution=3,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(m1)
    db_session.flush()

    row1 = DesignMatrixRow(matrix_id=m1.id, row_index=0)
    row2 = DesignMatrixRow(matrix_id=m1.id, row_index=1)
    db_session.add_all([row1, row2])
    db_session.flush()

    runs_m1 = [
        ExperimentRun(design_row_id=row1.id, replicate=1, status=RunStatus.completed),
        ExperimentRun(design_row_id=row1.id, replicate=2, status=RunStatus.completed),
        ExperimentRun(design_row_id=row2.id, replicate=1, status=RunStatus.failed),
        ExperimentRun(design_row_id=row2.id, replicate=2, status=RunStatus.pending),
    ]
    db_session.add_all(runs_m1)

    # Matrix 2: trial phase (counts as a promotion)
    m2 = DesignMatrix(
        name="trial-v1",
        phase=LifecyclePhase.trial,
        resolution=4,
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    db_session.add(m2)
    db_session.flush()

    row3 = DesignMatrixRow(matrix_id=m2.id, row_index=0)
    db_session.add(row3)
    db_session.flush()

    runs_m2 = [
        ExperimentRun(design_row_id=row3.id, replicate=1, status=RunStatus.completed),
        ExperimentRun(design_row_id=row3.id, replicate=2, status=RunStatus.running),
    ]
    db_session.add_all(runs_m2)

    db_session.commit()
    return db_session


@pytest.fixture
def empty_session(db_session: Session) -> Session:
    """Session with no data."""
    return db_session


# ---------------------------------------------------------------------------
# Unit tests — data gathering
# ---------------------------------------------------------------------------


class TestGatherExperiments:
    def test_returns_all_matrices(self, populated_session: Session):
        experiments = gather_experiments(populated_session)
        assert len(experiments) == 2

    def test_run_counts_correct(self, populated_session: Session):
        experiments = gather_experiments(populated_session)
        # Sorted by created_at desc, so trial-v1 first
        trial = next(e for e in experiments if e.name == "trial-v1")
        screening = next(e for e in experiments if e.name == "screening-v1")

        assert screening.total_runs == 4
        assert screening.completed == 2
        assert screening.failed == 1
        assert screening.pending == 1
        assert screening.running == 0

        assert trial.total_runs == 2
        assert trial.completed == 1
        assert trial.running == 1

    def test_empty_database(self, empty_session: Session):
        experiments = gather_experiments(empty_session)
        assert experiments == []

    def test_matrix_with_no_runs(self, db_session: Session):
        m = DesignMatrix(
            name="empty-matrix",
            phase=LifecyclePhase.candidate,
        )
        db_session.add(m)
        db_session.commit()

        experiments = gather_experiments(db_session)
        assert len(experiments) == 1
        assert experiments[0].total_runs == 0


class TestGatherBudget:
    def test_aggregate_counts(self, populated_session: Session):
        budget = gather_budget(populated_session)
        assert budget.total_runs == 6
        assert budget.completed == 3
        assert budget.failed == 1
        assert budget.pending == 1
        assert budget.running == 1
        assert budget.cancelled == 0

    def test_completion_rate(self, populated_session: Session):
        budget = gather_budget(populated_session)
        assert budget.completion_rate == pytest.approx(3 / 6)

    def test_failure_rate(self, populated_session: Session):
        budget = gather_budget(populated_session)
        # failed / (completed + failed) = 1/4
        assert budget.failure_rate == pytest.approx(1 / 4)

    def test_empty_database(self, empty_session: Session):
        budget = gather_budget(empty_session)
        assert budget.total_runs == 0
        assert budget.completion_rate == 0.0
        assert budget.failure_rate == 0.0


class TestGatherLifecycle:
    def test_counts_by_phase(self, populated_session: Session):
        lifecycle = gather_lifecycle(populated_session)
        assert lifecycle.counts.get("screening") == 1
        assert lifecycle.counts.get("trial") == 1
        assert lifecycle.total == 2

    def test_empty_database(self, empty_session: Session):
        lifecycle = gather_lifecycle(empty_session)
        assert lifecycle.total == 0


class TestGatherPromotions:
    def test_finds_promoted_matrices(self, populated_session: Session):
        promotions = gather_promotions(populated_session)
        assert len(promotions) == 1
        assert promotions[0].stack_id == "trial-v1"
        assert promotions[0].from_phase == "screening"
        assert promotions[0].to_phase == "trial"

    def test_empty_database(self, empty_session: Session):
        promotions = gather_promotions(empty_session)
        assert promotions == []

    def test_limit(self, db_session: Session):
        for i in range(5):
            m = DesignMatrix(
                name=f"prod-{i}",
                phase=LifecyclePhase.production,
                created_at=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
            )
            db_session.add(m)
        db_session.commit()

        promotions = gather_promotions(db_session, limit=3)
        assert len(promotions) == 3


# ---------------------------------------------------------------------------
# Unit tests — rendering
# ---------------------------------------------------------------------------


class TestRenderText:
    def test_contains_sections(self, populated_session: Session):
        report = build_dashboard(populated_session)
        text = render_text(report)

        assert "RETORT DASHBOARD" in text
        assert "Budget Usage" in text
        assert "Lifecycle States" in text
        assert "Active Experiments" in text
        assert "Recent Promotions" in text

    def test_shows_experiment_names(self, populated_session: Session):
        report = build_dashboard(populated_session)
        text = render_text(report)

        assert "screening-v1" in text
        assert "trial-v1" in text

    def test_shows_budget_numbers(self, populated_session: Session):
        report = build_dashboard(populated_session)
        text = render_text(report)

        assert "Total runs:    6" in text
        assert "Completed:     3" in text

    def test_empty_database(self, empty_session: Session):
        report = build_dashboard(empty_session)
        text = render_text(report)

        assert "(no experiments)" in text
        assert "(no promotions)" in text


class TestRenderJson:
    def test_valid_json(self, populated_session: Session):
        report = build_dashboard(populated_session)
        raw = render_json(report)
        data = json.loads(raw)

        assert "budget" in data
        assert "lifecycle" in data
        assert "experiments" in data
        assert "recent_promotions" in data

    def test_budget_fields(self, populated_session: Session):
        report = build_dashboard(populated_session)
        data = json.loads(render_json(report))

        assert data["budget"]["total_runs"] == 6
        assert data["budget"]["completed"] == 3

    def test_experiments_list(self, populated_session: Session):
        report = build_dashboard(populated_session)
        data = json.loads(render_json(report))

        names = {e["name"] for e in data["experiments"]}
        assert "screening-v1" in names
        assert "trial-v1" in names


# ---------------------------------------------------------------------------
# Unit tests — BudgetSummary edge cases
# ---------------------------------------------------------------------------


class TestBudgetSummary:
    def test_zero_runs(self):
        b = BudgetSummary(
            total_runs=0, completed=0, failed=0,
            pending=0, running=0, cancelled=0,
        )
        assert b.completion_rate == 0.0
        assert b.failure_rate == 0.0

    def test_all_completed(self):
        b = BudgetSummary(
            total_runs=10, completed=10, failed=0,
            pending=0, running=0, cancelled=0,
        )
        assert b.completion_rate == 1.0
        assert b.failure_rate == 0.0

    def test_all_failed(self):
        b = BudgetSummary(
            total_runs=5, completed=0, failed=5,
            pending=0, running=0, cancelled=0,
        )
        assert b.failure_rate == 1.0


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestDashboardCLI:
    def _init_db(self, db_path: Path) -> None:
        from retort.storage.database import create_tables, get_engine, get_session

        engine = get_engine(db_path)
        create_tables(engine)

        session = get_session(engine)
        m = DesignMatrix(
            name="test-screening",
            phase=LifecyclePhase.screening,
        )
        session.add(m)
        session.flush()

        row = DesignMatrixRow(matrix_id=m.id, row_index=0)
        session.add(row)
        session.flush()

        run = ExperimentRun(
            design_row_id=row.id, replicate=1, status=RunStatus.completed
        )
        session.add(run)
        session.commit()
        session.close()
        engine.dispose()

    def test_text_output(self, tmp_path: Path):
        db_path = tmp_path / "retort.db"
        self._init_db(db_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["report", "dashboard", "--db", str(db_path)])
        assert result.exit_code == 0, result.output
        assert "RETORT DASHBOARD" in result.output
        assert "test-screening" in result.output

    def test_json_output(self, tmp_path: Path):
        db_path = tmp_path / "retort.db"
        self._init_db(db_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["report", "dashboard", "--db", str(db_path), "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["budget"]["total_runs"] == 1
        assert data["budget"]["completed"] == 1

    def test_output_to_file(self, tmp_path: Path):
        db_path = tmp_path / "retort.db"
        self._init_db(db_path)
        out_path = tmp_path / "dashboard.txt"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["report", "dashboard", "--db", str(db_path), "-o", str(out_path)],
        )
        assert result.exit_code == 0, result.output
        assert out_path.exists()
        assert "RETORT DASHBOARD" in out_path.read_text()

    def test_missing_db(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["report", "dashboard", "--db", "/nonexistent/retort.db"]
        )
        assert result.exit_code != 0

    def test_empty_db(self, tmp_path: Path):
        from retort.storage.database import create_tables, get_engine

        db_path = tmp_path / "empty.db"
        engine = get_engine(db_path)
        create_tables(engine)
        engine.dispose()

        runner = CliRunner()
        result = runner.invoke(cli, ["report", "dashboard", "--db", str(db_path)])
        assert result.exit_code == 0, result.output
        assert "(no experiments)" in result.output
