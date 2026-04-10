"""Tests for storage models."""

from __future__ import annotations

from retort.storage.models import (
    DesignMatrix,
    DesignMatrixCell,
    DesignMatrixRow,
    ExperimentRun,
    FactorLevel,
    LifecyclePhase,
    RunResult,
    RunStatus,
)


def test_factor_level_creation(db_session):
    fl = FactorLevel(factor_name="language", level_name="python")
    db_session.add(fl)
    db_session.flush()
    assert fl.id is not None
    assert repr(fl) == "<FactorLevel language=python>"


def test_factor_level_uniqueness(db_session):
    """Same factor+level pair cannot be inserted twice."""
    import sqlalchemy.exc

    db_session.add(FactorLevel(factor_name="language", level_name="python"))
    db_session.flush()
    db_session.add(FactorLevel(factor_name="language", level_name="python"))
    try:
        db_session.flush()
        assert False, "Should have raised IntegrityError"
    except sqlalchemy.exc.IntegrityError:
        db_session.rollback()


def test_design_matrix_with_rows_and_cells(db_session):
    # Create factor levels
    py = FactorLevel(factor_name="language", level_name="python")
    claude = FactorLevel(factor_name="agent", level_name="claude-code")
    db_session.add_all([py, claude])
    db_session.flush()

    # Create design matrix
    dm = DesignMatrix(name="screening-v1", phase=LifecyclePhase.screening, resolution=3)
    db_session.add(dm)
    db_session.flush()

    # Add a row with cells
    row = DesignMatrixRow(matrix_id=dm.id, row_index=0)
    db_session.add(row)
    db_session.flush()

    cell1 = DesignMatrixCell(row_id=row.id, factor_level_id=py.id)
    cell2 = DesignMatrixCell(row_id=row.id, factor_level_id=claude.id)
    db_session.add_all([cell1, cell2])
    db_session.flush()

    assert len(row.cells) == 2
    assert dm.rows[0] is row


def test_experiment_run_lifecycle(db_session):
    # Setup minimal design
    fl = FactorLevel(factor_name="language", level_name="go")
    db_session.add(fl)
    db_session.flush()

    dm = DesignMatrix(name="test", phase=LifecyclePhase.screening)
    db_session.add(dm)
    db_session.flush()

    row = DesignMatrixRow(matrix_id=dm.id, row_index=0)
    db_session.add(row)
    db_session.flush()

    # Create run
    run = ExperimentRun(design_row_id=row.id, replicate=1)
    db_session.add(run)
    db_session.flush()

    assert run.status == RunStatus.pending
    run.status = RunStatus.running
    db_session.flush()
    assert run.status == RunStatus.running


def test_run_result(db_session):
    fl = FactorLevel(factor_name="language", level_name="rust")
    db_session.add(fl)
    db_session.flush()

    dm = DesignMatrix(name="test", phase=LifecyclePhase.trial)
    db_session.add(dm)
    db_session.flush()

    row = DesignMatrixRow(matrix_id=dm.id, row_index=0)
    db_session.add(row)
    db_session.flush()

    run = ExperimentRun(design_row_id=row.id, replicate=1, status=RunStatus.completed)
    db_session.add(run)
    db_session.flush()

    result = RunResult(run_id=run.id, metric_name="code_quality", value=0.87, unit="ratio")
    db_session.add(result)
    db_session.flush()

    assert result.value == 0.87
    assert run.results[0].metric_name == "code_quality"


def test_cascade_delete_design_matrix(db_session):
    """Deleting a design matrix cascades to rows and cells."""
    fl = FactorLevel(factor_name="agent", level_name="cursor")
    db_session.add(fl)
    db_session.flush()

    dm = DesignMatrix(name="ephemeral", phase=LifecyclePhase.screening)
    db_session.add(dm)
    db_session.flush()

    row = DesignMatrixRow(matrix_id=dm.id, row_index=0)
    db_session.add(row)
    db_session.flush()

    cell = DesignMatrixCell(row_id=row.id, factor_level_id=fl.id)
    db_session.add(cell)
    db_session.flush()

    db_session.delete(dm)
    db_session.flush()

    assert db_session.get(DesignMatrixRow, row.id) is None
    assert db_session.get(DesignMatrixCell, cell.id) is None
