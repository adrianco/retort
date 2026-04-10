"""Integration test: full candidate lifecycle.

Exercises the complete flow from factor definition through design generation,
experiment execution (simulated), result recording, and effects reporting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from retort.cli import main
from retort.design.factors import FactorRegistry
from retort.design.generator import generate_design
from retort.reporting.effects import (
    EffectsReport,
    compute_effects,
    compute_interaction_effects,
    compute_main_effects,
)
from retort.reporting.export import to_csv, to_json, to_text
from retort.storage.models import (
    Base,
    DesignMatrix,
    DesignMatrixCell,
    DesignMatrixRow,
    ExperimentRun,
    FactorLevel,
    LifecyclePhase,
    RunResult,
    RunStatus,
)


@pytest.fixture
def lifecycle_db(tmp_path: Path):
    """Create a SQLite database with full lifecycle data.

    Sets up: factors, design matrix, experiment runs, and scored results.
    Returns (engine, session, metadata dict).
    """
    db_path = tmp_path / "lifecycle.db"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()

    # --- Factor levels ---
    factors_spec = {
        "language": ["python", "go"],
        "agent": ["claude-code", "copilot"],
        "framework": ["fastapi", "stdlib"],
    }
    factor_levels: dict[str, dict[str, FactorLevel]] = {}
    for fname, levels in factors_spec.items():
        factor_levels[fname] = {}
        for i, lname in enumerate(levels):
            fl = FactorLevel(factor_name=fname, level_name=lname, ordinal=i)
            session.add(fl)
            factor_levels[fname][lname] = fl
    session.flush()

    # --- Generate design matrix ---
    registry = FactorRegistry()
    for fname, levels in factors_spec.items():
        registry.add(fname, levels)
    design = generate_design(registry, "screening")

    dm = DesignMatrix(
        name="screening-v1",
        phase=LifecyclePhase.screening,
        resolution=3,
        description="Integration test screening design",
    )
    session.add(dm)
    session.flush()

    # --- Populate design matrix rows and cells ---
    run_configs = design.run_configs()
    design_rows: list[DesignMatrixRow] = []
    for idx, config in enumerate(run_configs):
        row = DesignMatrixRow(matrix_id=dm.id, row_index=idx)
        session.add(row)
        session.flush()

        for fname, lname in config.items():
            fl = factor_levels[fname][lname]
            cell = DesignMatrixCell(row_id=row.id, factor_level_id=fl.id)
            session.add(cell)

        design_rows.append(row)

    session.flush()

    # --- Simulate experiment runs with scored results ---
    # Use deterministic "scores" that create a clear main effect for language:
    #   python always scores higher on code_quality than go
    score_map = {
        ("python", "claude-code"): {"code_quality": 0.92, "build_time": 12.5},
        ("python", "copilot"): {"code_quality": 0.85, "build_time": 14.0},
        ("go", "claude-code"): {"code_quality": 0.78, "build_time": 8.0},
        ("go", "copilot"): {"code_quality": 0.70, "build_time": 9.5},
    }

    for row_obj, config in zip(design_rows, run_configs):
        lang = config["language"]
        agent = config["agent"]
        key = (lang, agent)
        scores = score_map.get(key, {"code_quality": 0.75, "build_time": 10.0})

        for replicate in range(1, 4):  # 3 replicates
            run = ExperimentRun(
                design_row_id=row_obj.id,
                replicate=replicate,
                status=RunStatus.completed,
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )
            session.add(run)
            session.flush()

            for metric_name, value in scores.items():
                # Add small replicate variation
                varied = value + (replicate - 2) * 0.01
                result = RunResult(
                    run_id=run.id,
                    metric_name=metric_name,
                    value=varied,
                )
                session.add(result)

    session.commit()

    yield engine, session, {
        "db_path": db_path,
        "matrix_id": dm.id,
        "design_name": dm.name,
        "n_design_rows": len(design_rows),
        "factors": list(factors_spec.keys()),
        "metrics": ["code_quality", "build_time"],
    }

    session.close()
    engine.dispose()


class TestFullLifecycle:
    """End-to-end lifecycle: design -> run -> report."""

    def test_design_generation_produces_valid_matrix(self, lifecycle_db):
        """Design generation creates a matrix with correct factor assignments."""
        engine, session, meta = lifecycle_db

        dm = session.get(DesignMatrix, meta["matrix_id"])
        assert dm is not None
        assert dm.name == "screening-v1"
        assert dm.phase == LifecyclePhase.screening
        assert len(dm.rows) == meta["n_design_rows"]

        # Each row should have cells for all 3 factors
        for row in dm.rows:
            factor_names = {c.factor_level.factor_name for c in row.cells}
            assert factor_names == set(meta["factors"])

    def test_experiment_runs_recorded(self, lifecycle_db):
        """All design rows have completed experiment runs with results."""
        engine, session, meta = lifecycle_db

        dm = session.get(DesignMatrix, meta["matrix_id"])
        for row in dm.rows:
            assert len(row.runs) == 3  # 3 replicates
            for run in row.runs:
                assert run.status == RunStatus.completed
                metric_names = {r.metric_name for r in run.results}
                assert metric_names == set(meta["metrics"])

    def test_compute_main_effects(self, lifecycle_db):
        """Main effects show language has a clear effect on code_quality."""
        engine, session, meta = lifecycle_db

        report = compute_effects(session, meta["matrix_id"], "code_quality")

        assert isinstance(report, EffectsReport)
        assert report.metric == "code_quality"
        assert report.design_name == "screening-v1"
        assert report.n_runs > 0
        assert len(report.main_effects) == 3  # language, agent, framework

        # Find the language main effect
        lang_effect = next(
            me for me in report.main_effects if me.factor == "language"
        )
        assert "python" in lang_effect.level_means
        assert "go" in lang_effect.level_means
        # Python should score higher on code_quality
        assert lang_effect.level_means["python"] > lang_effect.level_means["go"]
        assert lang_effect.effect_range > 0

    def test_compute_interaction_effects(self, lifecycle_db):
        """Interaction effects are computed for all factor pairs."""
        engine, session, meta = lifecycle_db

        report = compute_effects(session, meta["matrix_id"], "code_quality")

        # 3 factors -> C(3,2) = 3 interaction pairs
        assert len(report.interactions) == 3

        # Check language x agent interaction exists
        lang_agent = next(
            (ie for ie in report.interactions
             if {ie.factor_a, ie.factor_b} == {"language", "agent"}),
            None,
        )
        assert lang_agent is not None
        assert len(lang_agent.cell_means) > 0

    def test_grand_mean_consistency(self, lifecycle_db):
        """Grand mean is consistent across main and interaction effects."""
        engine, session, meta = lifecycle_db

        report = compute_effects(session, meta["matrix_id"], "code_quality")
        assert report.grand_mean > 0

        for me in report.main_effects:
            assert me.grand_mean == report.grand_mean
        for ie in report.interactions:
            assert ie.grand_mean == report.grand_mean

    def test_multiple_metrics(self, lifecycle_db):
        """Effects can be computed for different metrics independently."""
        engine, session, meta = lifecycle_db

        quality_report = compute_effects(session, meta["matrix_id"], "code_quality")
        time_report = compute_effects(session, meta["matrix_id"], "build_time")

        assert quality_report.metric == "code_quality"
        assert time_report.metric == "build_time"
        # They should have different grand means
        assert quality_report.grand_mean != time_report.grand_mean

    def test_invalid_metric_raises(self, lifecycle_db):
        """Requesting a nonexistent metric raises ValueError."""
        engine, session, meta = lifecycle_db

        with pytest.raises(ValueError, match="not found"):
            compute_effects(session, meta["matrix_id"], "nonexistent_metric")

    def test_invalid_matrix_raises(self, lifecycle_db):
        """Requesting a nonexistent matrix raises ValueError."""
        engine, session, meta = lifecycle_db

        with pytest.raises(ValueError, match="not found"):
            compute_effects(session, 99999, "code_quality")


class TestExportFormats:
    """Effects reports export correctly to all formats."""

    def test_text_export(self, lifecycle_db):
        engine, session, meta = lifecycle_db
        report = compute_effects(session, meta["matrix_id"], "code_quality")

        text = to_text(report)
        assert "Effects Report: screening-v1" in text
        assert "Metric: code_quality" in text
        assert "Main Effects" in text
        assert "language" in text
        assert "python" in text

    def test_json_export(self, lifecycle_db):
        engine, session, meta = lifecycle_db
        report = compute_effects(session, meta["matrix_id"], "code_quality")

        import json

        raw = to_json(report)
        data = json.loads(raw)

        assert data["metric"] == "code_quality"
        assert data["design_name"] == "screening-v1"
        assert len(data["main_effects"]) == 3
        assert len(data["interactions"]) == 3
        assert data["grand_mean"] > 0

    def test_csv_export(self, lifecycle_db):
        engine, session, meta = lifecycle_db
        report = compute_effects(session, meta["matrix_id"], "code_quality")

        csv_text = to_csv(report)
        lines = csv_text.strip().splitlines()
        assert lines[0].strip() == "factor,level,mean,delta,effect_range"
        # Should have rows for each factor-level combination
        assert len(lines) > 1


class TestCLIReportEffects:
    """CLI integration for `retort report effects`."""

    def test_text_output(self, lifecycle_db):
        engine, session, meta = lifecycle_db
        session.close()
        engine.dispose()

        runner = CliRunner()
        result = runner.invoke(main, [
            "report", "effects",
            "--db", str(meta["db_path"]),
            "--matrix-id", str(meta["matrix_id"]),
            "--metric", "code_quality",
        ])
        assert result.exit_code == 0, result.output
        assert "Main Effects" in result.output
        assert "language" in result.output

    def test_json_output(self, lifecycle_db):
        engine, session, meta = lifecycle_db
        session.close()
        engine.dispose()

        import json

        runner = CliRunner()
        result = runner.invoke(main, [
            "report", "effects",
            "--db", str(meta["db_path"]),
            "--matrix-id", str(meta["matrix_id"]),
            "--metric", "code_quality",
            "--format", "json",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["metric"] == "code_quality"

    def test_csv_output(self, lifecycle_db):
        engine, session, meta = lifecycle_db
        session.close()
        engine.dispose()

        runner = CliRunner()
        result = runner.invoke(main, [
            "report", "effects",
            "--db", str(meta["db_path"]),
            "--matrix-id", str(meta["matrix_id"]),
            "--metric", "code_quality",
            "--format", "csv",
        ])
        assert result.exit_code == 0, result.output
        assert "factor,level,mean,delta,effect_range" in result.output

    def test_file_output(self, lifecycle_db, tmp_path):
        engine, session, meta = lifecycle_db
        session.close()
        engine.dispose()

        outfile = tmp_path / "report.json"
        runner = CliRunner()
        result = runner.invoke(main, [
            "report", "effects",
            "--db", str(meta["db_path"]),
            "--matrix-id", str(meta["matrix_id"]),
            "--metric", "code_quality",
            "--format", "json",
            "-o", str(outfile),
        ])
        assert result.exit_code == 0, result.output
        assert outfile.exists()
        assert "code_quality" in outfile.read_text()

    def test_invalid_metric_error(self, lifecycle_db):
        engine, session, meta = lifecycle_db
        session.close()
        engine.dispose()

        runner = CliRunner()
        result = runner.invoke(main, [
            "report", "effects",
            "--db", str(meta["db_path"]),
            "--matrix-id", str(meta["matrix_id"]),
            "--metric", "nonexistent",
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()
