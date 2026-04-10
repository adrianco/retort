"""Tests for the Wardley map overlay reporting module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner
from sqlalchemy.orm import Session

from retort.cli import main as cli
from retort.reporting.wardley import (
    EVOLUTION_STAGES,
    StackPosition,
    WardleyMapReport,
    build_wardley_map,
    gather_stacks,
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
    """Session with stacks across multiple lifecycle phases."""
    # Candidate stack — no runs
    m1 = DesignMatrix(
        name="alpha-stack",
        phase=LifecyclePhase.candidate,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(m1)
    db_session.flush()

    # Screening stack — some runs
    m2 = DesignMatrix(
        name="beta-stack",
        phase=LifecyclePhase.screening,
        resolution=3,
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    db_session.add(m2)
    db_session.flush()

    row2 = DesignMatrixRow(matrix_id=m2.id, row_index=0)
    db_session.add(row2)
    db_session.flush()

    db_session.add_all([
        ExperimentRun(design_row_id=row2.id, replicate=1, status=RunStatus.completed),
        ExperimentRun(design_row_id=row2.id, replicate=2, status=RunStatus.completed),
        ExperimentRun(design_row_id=row2.id, replicate=3, status=RunStatus.failed),
    ])

    # Trial stack — high completion
    m3 = DesignMatrix(
        name="gamma-stack",
        phase=LifecyclePhase.trial,
        resolution=4,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    db_session.add(m3)
    db_session.flush()

    row3 = DesignMatrixRow(matrix_id=m3.id, row_index=0)
    db_session.add(row3)
    db_session.flush()

    for i in range(5):
        db_session.add(
            ExperimentRun(
                design_row_id=row3.id, replicate=i + 1, status=RunStatus.completed
            )
        )

    # Production stack
    m4 = DesignMatrix(
        name="delta-stack",
        phase=LifecyclePhase.production,
        resolution=4,
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    db_session.add(m4)
    db_session.flush()

    row4 = DesignMatrixRow(matrix_id=m4.id, row_index=0)
    db_session.add(row4)
    db_session.flush()

    for i in range(12):
        db_session.add(
            ExperimentRun(
                design_row_id=row4.id,
                replicate=i + 1,
                status=RunStatus.completed,
            )
        )

    # Retired stack
    m5 = DesignMatrix(
        name="epsilon-stack",
        phase=LifecyclePhase.retired,
        created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    db_session.add(m5)
    db_session.flush()

    db_session.commit()
    return db_session


@pytest.fixture
def empty_session(db_session: Session) -> Session:
    """Session with no data."""
    return db_session


# ---------------------------------------------------------------------------
# Unit tests — evolution stage mapping
# ---------------------------------------------------------------------------


class TestEvolutionStages:
    def test_all_phases_mapped(self):
        for phase in LifecyclePhase:
            assert phase.value in EVOLUTION_STAGES

    def test_candidate_maps_to_genesis(self):
        index, name = EVOLUTION_STAGES["candidate"]
        assert name == "Genesis"
        assert index == 1

    def test_production_maps_to_commodity(self):
        index, name = EVOLUTION_STAGES["production"]
        assert name == "Commodity"
        assert index == 4

    def test_retired_has_zero_index(self):
        index, name = EVOLUTION_STAGES["retired"]
        assert name == "Retired"
        assert index == 0


# ---------------------------------------------------------------------------
# Unit tests — data gathering
# ---------------------------------------------------------------------------


class TestGatherStacks:
    def test_returns_all_stacks(self, populated_session: Session):
        stacks = gather_stacks(populated_session)
        assert len(stacks) == 5

    def test_evolution_stages_assigned(self, populated_session: Session):
        stacks = gather_stacks(populated_session)
        by_name = {s.stack_id: s for s in stacks}

        assert by_name["alpha-stack"].evolution_stage == "Genesis"
        assert by_name["beta-stack"].evolution_stage == "Custom-Built"
        assert by_name["gamma-stack"].evolution_stage == "Product"
        assert by_name["delta-stack"].evolution_stage == "Commodity"
        assert by_name["epsilon-stack"].evolution_stage == "Retired"

    def test_run_counts(self, populated_session: Session):
        stacks = gather_stacks(populated_session)
        by_name = {s.stack_id: s for s in stacks}

        assert by_name["alpha-stack"].run_count == 0
        assert by_name["beta-stack"].run_count == 3
        assert by_name["gamma-stack"].run_count == 5
        assert by_name["delta-stack"].run_count == 12

    def test_completion_rates(self, populated_session: Session):
        stacks = gather_stacks(populated_session)
        by_name = {s.stack_id: s for s in stacks}

        assert by_name["alpha-stack"].completion_rate == 0.0
        assert by_name["beta-stack"].completion_rate == pytest.approx(2 / 3, abs=1e-3)
        assert by_name["gamma-stack"].completion_rate == 1.0
        assert by_name["delta-stack"].completion_rate == 1.0

    def test_visibility_range(self, populated_session: Session):
        stacks = gather_stacks(populated_session)
        for s in stacks:
            assert 0.0 <= s.visibility <= 1.0

    def test_empty_database(self, empty_session: Session):
        stacks = gather_stacks(empty_session)
        assert stacks == []


# ---------------------------------------------------------------------------
# Unit tests — report building
# ---------------------------------------------------------------------------


class TestBuildWardleyMap:
    def test_stage_counts(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        assert report.stage_counts["Genesis"] == 1
        assert report.stage_counts["Custom-Built"] == 1
        assert report.stage_counts["Product"] == 1
        assert report.stage_counts["Commodity"] == 1
        assert report.stage_counts["Retired"] == 1

    def test_total(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        assert report.total == 5

    def test_active_stacks(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        active = report.active_stacks
        assert len(active) == 4
        assert all(s.phase != "retired" for s in active)

    def test_retired_stacks(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        retired = report.retired_stacks
        assert len(retired) == 1
        assert retired[0].stack_id == "epsilon-stack"

    def test_empty_database(self, empty_session: Session):
        report = build_wardley_map(empty_session)
        assert report.total == 0
        assert report.active_stacks == []
        assert report.retired_stacks == []


# ---------------------------------------------------------------------------
# Unit tests — WardleyMapReport dataclass
# ---------------------------------------------------------------------------


class TestWardleyMapReport:
    def test_empty_report(self):
        report = WardleyMapReport(stacks=[], stage_counts={})
        assert report.total == 0
        assert report.active_stacks == []
        assert report.retired_stacks == []

    def test_mixed_phases(self):
        stacks = [
            StackPosition("a", "candidate", "Genesis", 1, 0.5, 0, 0.0),
            StackPosition("b", "retired", "Retired", 0, 0.1, 10, 0.5),
        ]
        report = WardleyMapReport(stacks=stacks, stage_counts={"Genesis": 1, "Retired": 1})
        assert report.total == 2
        assert len(report.active_stacks) == 1
        assert len(report.retired_stacks) == 1


# ---------------------------------------------------------------------------
# Unit tests — text rendering
# ---------------------------------------------------------------------------


class TestRenderText:
    def test_contains_header(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        text = render_text(report)
        assert "WARDLEY MAP" in text
        assert "STACK EVOLUTION OVERLAY" in text

    def test_contains_sections(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        text = render_text(report)
        assert "Evolution Stage Distribution" in text
        assert "Map Overlay" in text
        assert "Stack Details" in text

    def test_shows_stack_names(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        text = render_text(report)
        assert "alpha-stack" in text
        assert "beta-stack" in text
        assert "gamma-stack" in text
        assert "delta-stack" in text

    def test_shows_stage_names(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        text = render_text(report)
        assert "Genesis" in text
        assert "Custom-Built" in text
        assert "Product" in text
        assert "Commodity" in text

    def test_empty_database(self, empty_session: Session):
        report = build_wardley_map(empty_session)
        text = render_text(report)
        assert "WARDLEY MAP" in text
        # All counts should be 0
        assert "[ 0]" in text


# ---------------------------------------------------------------------------
# Unit tests — JSON rendering
# ---------------------------------------------------------------------------


class TestRenderJson:
    def test_valid_json(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        raw = render_json(report)
        data = json.loads(raw)
        assert "stacks" in data
        assert "stage_counts" in data
        assert "total" in data

    def test_stack_fields(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        data = json.loads(render_json(report))
        stack = data["stacks"][0]
        assert "stack_id" in stack
        assert "phase" in stack
        assert "evolution_stage" in stack
        assert "evolution_index" in stack
        assert "visibility" in stack
        assert "run_count" in stack
        assert "completion_rate" in stack

    def test_stage_counts(self, populated_session: Session):
        report = build_wardley_map(populated_session)
        data = json.loads(render_json(report))
        assert data["stage_counts"]["Genesis"] == 1
        assert data["stage_counts"]["Commodity"] == 1
        assert data["total"] == 5

    def test_empty_database(self, empty_session: Session):
        report = build_wardley_map(empty_session)
        data = json.loads(render_json(report))
        assert data["stacks"] == []
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestWardleyCLI:
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
        result = runner.invoke(cli, ["report", "wardley", "--db", str(db_path)])
        assert result.exit_code == 0, result.output
        assert "WARDLEY MAP" in result.output
        assert "test-screening" in result.output

    def test_json_output(self, tmp_path: Path):
        db_path = tmp_path / "retort.db"
        self._init_db(db_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["report", "wardley", "--db", str(db_path), "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["total"] == 1
        assert data["stacks"][0]["evolution_stage"] == "Custom-Built"

    def test_output_to_file(self, tmp_path: Path):
        db_path = tmp_path / "retort.db"
        self._init_db(db_path)
        out_path = tmp_path / "wardley.txt"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["report", "wardley", "--db", str(db_path), "-o", str(out_path)],
        )
        assert result.exit_code == 0, result.output
        assert out_path.exists()
        assert "WARDLEY MAP" in out_path.read_text()

    def test_missing_db(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["report", "wardley", "--db", "/nonexistent/retort.db"]
        )
        assert result.exit_code != 0

    def test_empty_db(self, tmp_path: Path):
        from retort.storage.database import create_tables, get_engine

        db_path = tmp_path / "empty.db"
        engine = get_engine(db_path)
        create_tables(engine)
        engine.dispose()

        runner = CliRunner()
        result = runner.invoke(cli, ["report", "wardley", "--db", str(db_path)])
        assert result.exit_code == 0, result.output
        assert "WARDLEY MAP" in result.output
