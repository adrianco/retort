"""Tests for the CLI."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from click.testing import CliRunner

from retort.cli import main as cli


def test_init_creates_workspace(tmp_path: Path):
    runner = CliRunner()
    ws = tmp_path / "my-eval"
    result = runner.invoke(cli, ["init", str(ws)])
    assert result.exit_code == 0, result.output

    assert (ws / "workspace.yaml").exists()
    assert (ws / "retort.db").exists()

    # Verify database has expected tables
    conn = sqlite3.connect(ws / "retort.db")
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()

    assert "factor_levels" in tables
    assert "design_matrices" in tables
    assert "design_matrix_rows" in tables
    assert "design_matrix_cells" in tables
    assert "experiment_runs" in tables
    assert "run_results" in tables


def test_init_refuses_existing_dir(tmp_path: Path):
    ws = tmp_path / "existing"
    ws.mkdir()
    (ws / "somefile").write_text("data")

    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(ws)])
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_init_force_overwrites(tmp_path: Path):
    ws = tmp_path / "overwrite"
    ws.mkdir()
    (ws / "old-file.txt").write_text("old")

    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(ws), "--force"])
    assert result.exit_code == 0
    assert not (ws / "old-file.txt").exists()
    assert (ws / "workspace.yaml").exists()


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_export_csv_round_trip(tmp_path: Path):
    """`retort export csv` joins runs+results and emits a header+row CSV
    that downstream tools (e.g. retort analyze) can consume."""
    import json

    from retort.storage.database import create_tables, get_engine, get_session_factory
    from retort.storage.models import ExperimentRun, RunResult, RunStatus

    db_path = tmp_path / "retort.db"
    engine = get_engine(db_path)
    create_tables(engine)
    session = get_session_factory(engine)()

    run = ExperimentRun(
        replicate=1,
        status=RunStatus.completed,
        run_config_json=json.dumps({"language": "python", "model": "opus"}),
    )
    session.add(run)
    session.flush()
    session.add(RunResult(run_id=run.id, metric_name="code_quality", value=0.85))
    session.add(RunResult(run_id=run.id, metric_name="build_time", value=1.0))
    session.commit()
    session.close()
    engine.dispose()

    runner = CliRunner()
    result = runner.invoke(cli, ["export", "csv", "--db", str(db_path)])
    assert result.exit_code == 0, result.output

    lines = [line for line in result.output.strip().splitlines() if line]
    assert lines[0].startswith("run_id,replicate,status,")
    # Factors and metrics appear as columns
    assert "language" in lines[0]
    assert "code_quality" in lines[0]
    assert "build_time" in lines[0]

    assert len(lines) == 2  # header + one row
    assert "python" in lines[1]
    assert "opus" in lines[1]
    assert "0.85" in lines[1]


class _StubExperiment:
    def __init__(self, name="test-exp"):
        self.name = name


class _StubWorkspaceConfig:
    def __init__(self, name="test-exp"):
        self.experiment = _StubExperiment(name)


def test_persist_design_matrix_creates_rows(tmp_path: Path):
    from retort.cli import _persist_design_matrix
    from retort.design.factors import FactorRegistry
    from retort.design.generator import generate_design
    from retort.storage.database import create_tables, get_engine, get_session_factory
    from retort.storage.models import (
        DesignMatrix, DesignMatrixCell, DesignMatrixRow, FactorLevel,
    )

    db_path = tmp_path / "retort.db"
    engine = get_engine(db_path)
    create_tables(engine)
    session = get_session_factory(engine)()

    registry = FactorRegistry()
    registry.add("language", ["python", "go"])
    registry.add("model", ["opus", "sonnet"])
    design = generate_design(registry, "screening")

    matrix_id, mapping = _persist_design_matrix(
        session, registry, design, "screening", _StubWorkspaceConfig(),
    )
    session.commit()

    # Matrix row created
    matrix = session.query(DesignMatrix).filter(DesignMatrix.id == matrix_id).one()
    assert matrix.name == "test-exp-screening"

    # FactorLevel rows created for every (factor, level) pair
    levels = {(fl.factor_name, fl.level_name)
              for fl in session.query(FactorLevel).all()}
    assert ("language", "python") in levels
    assert ("language", "go") in levels
    assert ("model", "opus") in levels
    assert ("model", "sonnet") in levels

    # One DesignMatrixRow per design row
    rows = session.query(DesignMatrixRow).filter(
        DesignMatrixRow.matrix_id == matrix_id,
    ).all()
    assert len(rows) == design.num_runs

    # Cells exist linking rows to factor levels
    cells = session.query(DesignMatrixCell).count()
    assert cells == len(rows) * 2  # 2 factors per row

    # Mapping covers every config
    assert len(mapping) == design.num_runs

    session.close()
    engine.dispose()


def test_persist_design_matrix_idempotent(tmp_path: Path):
    """Re-running --resume must not duplicate the matrix or its rows."""
    from retort.cli import _persist_design_matrix
    from retort.design.factors import FactorRegistry
    from retort.design.generator import generate_design
    from retort.storage.database import create_tables, get_engine, get_session_factory
    from retort.storage.models import DesignMatrix, DesignMatrixRow, FactorLevel

    db_path = tmp_path / "retort.db"
    engine = get_engine(db_path)
    create_tables(engine)
    session = get_session_factory(engine)()

    registry = FactorRegistry()
    registry.add("language", ["python", "go"])
    registry.add("model", ["opus", "sonnet"])
    design = generate_design(registry, "screening")

    id1, map1 = _persist_design_matrix(
        session, registry, design, "screening", _StubWorkspaceConfig(),
    )
    session.commit()
    id2, map2 = _persist_design_matrix(
        session, registry, design, "screening", _StubWorkspaceConfig(),
    )
    session.commit()

    assert id1 == id2  # same matrix
    assert map1 == map2  # same row IDs
    # No duplicate matrices, rows, or factor levels
    assert session.query(DesignMatrix).count() == 1
    assert session.query(DesignMatrixRow).count() == design.num_runs
    assert session.query(FactorLevel).count() == 4  # 2 factors x 2 levels

    session.close()
    engine.dispose()


class TestShardLogic:
    def test_no_shard_owns_everything(self):
        from retort.cli import _parse_shard, _shard_owns
        idx, total = _parse_shard(None)
        assert (idx, total) == (0, 1)
        assert _shard_owns("anything", 1, idx, total)

    def test_shard_partition_covers_everything(self):
        from retort.cli import _shard_owns
        # 100 (config_key, rep) pairs across 4 shards → each cell owned
        # by exactly one shard.
        keys = [(f"k{i}", r) for i in range(20) for r in range(1, 6)]
        ownership = {k: 0 for k in keys}
        for i in range(4):
            for k, r in keys:
                if _shard_owns(k, r, i, 4):
                    ownership[(k, r)] += 1
        assert all(v == 1 for v in ownership.values())

    def test_invalid_shard_format(self):
        import pytest as _pt
        from retort.cli import _parse_shard
        from click.exceptions import ClickException
        for bad in ["0", "1/0", "-1/4", "5/4", "x/4"]:
            with _pt.raises(ClickException):
                _parse_shard(bad)


def test_export_csv_excludes_failed_by_default(tmp_path: Path):
    import json

    from retort.storage.database import create_tables, get_engine, get_session_factory
    from retort.storage.models import ExperimentRun, RunStatus

    db_path = tmp_path / "retort.db"
    engine = get_engine(db_path)
    create_tables(engine)
    session = get_session_factory(engine)()
    session.add(ExperimentRun(
        replicate=1, status=RunStatus.completed,
        run_config_json=json.dumps({"language": "python"}),
    ))
    session.add(ExperimentRun(
        replicate=1, status=RunStatus.failed,
        run_config_json=json.dumps({"language": "rust"}),
    ))
    session.commit()
    session.close()
    engine.dispose()

    runner = CliRunner()
    # Default — failed excluded
    result = runner.invoke(cli, ["export", "csv", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "python" in result.output
    assert "rust" not in result.output

    # --include-failed — both present
    result = runner.invoke(cli, ["export", "csv", "--db", str(db_path), "--include-failed"])
    assert result.exit_code == 0
    assert "python" in result.output
    assert "rust" in result.output


class TestEvaluateCommand:
    """Tests for `retort evaluate` bulk evaluation."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace.yaml."""
        cfg = tmp_path / "workspace.yaml"
        cfg.write_text(
            "experiment:\n"
            "  name: test\n"
            "  visibility: private\n"
            "factors:\n"
            "  language:\n"
            "    levels: [python]\n"
            "responses:\n"
            "  - code_quality\n"
            "tasks:\n"
            "  - source: bundled://hello\n"
            "evaluation:\n"
            "  enabled: true\n"
            "  model: claude-haiku-4-5\n"
        )
        return cfg

    def test_no_args_error(self, tmp_path: Path):
        cfg = self._make_workspace(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["evaluate", "--config", str(cfg)])
        assert result.exit_code != 0
        assert "Provide at least one RUN_DIR" in result.output

    def test_both_run_dirs_and_experiment_dir_error(self, tmp_path: Path):
        cfg = self._make_workspace(tmp_path)
        run_a = tmp_path / "run-a"
        run_a.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["evaluate", str(run_a), "--experiment-dir", str(tmp_path), "--config", str(cfg)],
        )
        assert result.exit_code != 0
        assert "not both" in result.output

    def test_experiment_dir_no_runs_folder(self, tmp_path: Path):
        cfg = self._make_workspace(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli, ["evaluate", "--experiment-dir", str(tmp_path), "--config", str(cfg)]
        )
        assert result.exit_code != 0
        assert "No runs/ directory" in result.output

    def test_experiment_dir_empty_runs(self, tmp_path: Path):
        cfg = self._make_workspace(tmp_path)
        (tmp_path / "runs").mkdir()
        runner = CliRunner()
        result = runner.invoke(
            cli, ["evaluate", "--experiment-dir", str(tmp_path), "--config", str(cfg)]
        )
        assert result.exit_code != 0
        assert "No run directories" in result.output

    def test_experiment_dir_calls_evaluation_for_each_run(self, tmp_path: Path, monkeypatch):
        cfg = self._make_workspace(tmp_path)
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        run_a = runs_root / "run-a"
        run_b = runs_root / "run-b"
        run_a.mkdir()
        run_b.mkdir()

        called = []

        def _fake_eval(run_dir, eval_config, visibility, *, force=False):
            called.append(run_dir)

        monkeypatch.setattr("retort.cli._run_auto_evaluation", _fake_eval)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["evaluate", "--experiment-dir", str(tmp_path), "--config", str(cfg)]
        )
        assert result.exit_code == 0, result.output
        assert set(called) == {run_a, run_b}

    def test_multiple_run_dirs_calls_evaluation_for_each(self, tmp_path: Path, monkeypatch):
        cfg = self._make_workspace(tmp_path)
        run_a = tmp_path / "run-a"
        run_b = tmp_path / "run-b"
        run_a.mkdir()
        run_b.mkdir()

        called = []

        def _fake_eval(run_dir, eval_config, visibility, *, force=False):
            called.append(run_dir)

        monkeypatch.setattr("retort.cli._run_auto_evaluation", _fake_eval)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["evaluate", str(run_a), str(run_b), "--config", str(cfg)],
        )
        assert result.exit_code == 0, result.output
        assert set(called) == {run_a, run_b}

    def test_single_run_dir_still_works(self, tmp_path: Path, monkeypatch):
        cfg = self._make_workspace(tmp_path)
        run_a = tmp_path / "run-a"
        run_a.mkdir()

        called = []

        def _fake_eval(run_dir, eval_config, visibility, *, force=False):
            called.append(run_dir)

        monkeypatch.setattr("retort.cli._run_auto_evaluation", _fake_eval)

        runner = CliRunner()
        result = runner.invoke(cli, ["evaluate", str(run_a), "--config", str(cfg)])
        assert result.exit_code == 0, result.output
        assert called == [run_a]
