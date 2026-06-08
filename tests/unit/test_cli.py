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


def test_bundled_tasks_ship_requirements_json():
    # Regression: experiment-9 was set up without a REQUIREMENTS.json, so the
    # spec gate fell back to ad-hoc TASK.md extraction and graded on a varying
    # denominator. Every bundled task must ship a pinned checklist.
    from retort.playpen.task_loader import BUNDLED_TASKS_DIR, task_requirements_path
    import json as _json
    task_dirs = [d for d in BUNDLED_TASKS_DIR.iterdir()
                 if d.is_dir() and (d / "task.yaml").exists()]
    assert task_dirs
    for d in task_dirs:
        req = task_requirements_path(f"bundled://{d.name}")
        assert req is not None, f"{d.name} is missing REQUIREMENTS.json"
        data = _json.loads(req.read_text())
        assert data["requirements"], f"{d.name} has an empty checklist"


def test_ensure_requirements_json(tmp_path: Path):
    from retort.cli import _ensure_requirements_json, _generate_requirements_from_prompt
    from retort.playpen.task_loader import load_task, task_requirements_path
    import json as _json

    task = load_task("bundled://rest-api-crud")

    # Missing → copies the task's pinned checklist verbatim (not generated).
    _ensure_requirements_json(tmp_path, task, "bundled://rest-api-crud", task_requirements_path)
    data = _json.loads((tmp_path / "REQUIREMENTS.json").read_text())
    assert data["task"] == "rest-api-crud"
    assert not data.get("generated")
    assert len(data["requirements"]) == 12

    # Existing → respected, never overwritten.
    (tmp_path / "REQUIREMENTS.json").write_text('{"requirements": [{"id": "ONLY"}]}')
    _ensure_requirements_json(tmp_path, task, "bundled://rest-api-crud", task_requirements_path)
    assert _json.loads((tmp_path / "REQUIREMENTS.json").read_text())["requirements"] == [{"id": "ONLY"}]

    # No pinned checklist (e.g. github task) → generate from the prompt + flag it.
    gen = _generate_requirements_from_prompt(task)
    assert gen["generated"] is True
    assert len(gen["requirements"]) >= 3
    fresh = tmp_path / "sub"
    fresh.mkdir()
    _ensure_requirements_json(fresh, task, "github://o/r", task_requirements_path)
    assert _json.loads((fresh / "REQUIREMENTS.json").read_text())["generated"] is True


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
        assert "No rep directories" in result.output

    def test_experiment_dir_calls_evaluation_for_each_run(self, tmp_path: Path, monkeypatch):
        cfg = self._make_workspace(tmp_path)
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        # CLI walks two levels: runs/<cell>/<rep> — rep dirs start with "rep"
        cell_a = runs_root / "cell-a"
        cell_b = runs_root / "cell-b"
        cell_a.mkdir()
        cell_b.mkdir()
        rep_a = cell_a / "rep-0"
        rep_b = cell_b / "rep-0"
        rep_a.mkdir()
        rep_b.mkdir()

        called = []

        def _fake_eval(run_dir, eval_config, visibility, *, force=False):
            called.append(run_dir)

        monkeypatch.setattr("retort.cli._run_auto_evaluation", _fake_eval)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["evaluate", "--experiment-dir", str(tmp_path), "--config", str(cfg)]
        )
        assert result.exit_code == 0, result.output
        assert set(called) == {rep_a, rep_b}

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


class TestDesignGenerateCommand:
    """Tests for `retort design generate`."""

    def _make_workspace(self, tmp_path: Path, fraction: float | None = None) -> Path:
        cfg = tmp_path / "workspace.yaml"
        fraction_line = f"  fraction: {fraction}\n" if fraction is not None else ""
        cfg.write_text(
            "experiment:\n"
            "  name: test\n"
            "factors:\n"
            "  language:\n"
            "    levels: [python, typescript, go, rust, java, clojure]\n"
            "  model:\n"
            "    levels: [opus-4-6, opus-4-7]\n"
            "  tooling:\n"
            "    levels: [none, beads]\n"
            "responses:\n"
            "  - code_quality\n"
            "tasks:\n"
            "  - source: bundled://rest-api-crud\n"
            "design:\n"
            f"{fraction_line}"
            "  screening_resolution: 3\n"
        )
        return cfg

    def test_generate_outputs_csv(self, tmp_path: Path):
        cfg = self._make_workspace(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["design", "generate", "--phase", "screening", "--config", str(cfg), "-o", str(tmp_path / "design.csv")],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / "design.csv").exists()

    def test_generate_stdout_csv(self, tmp_path: Path):
        cfg = self._make_workspace(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["design", "generate", "--phase", "screening", "--config", str(cfg)],
        )
        assert result.exit_code == 0, result.output
        # Output should contain CSV header
        assert "language" in result.output

    def test_generate_with_fraction_reduces_rows(self, tmp_path: Path):
        """design.fraction = 0.25 should produce 6 rows for 6×2×2 design."""
        cfg = self._make_workspace(tmp_path, fraction=0.25)
        out_csv = tmp_path / "design.csv"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["design", "generate", "--phase", "screening", "--config", str(cfg), "-o", str(out_csv)],
        )
        assert result.exit_code == 0, result.output
        assert out_csv.exists()
        import pandas as pd
        df = pd.read_csv(out_csv, index_col="run")
        assert len(df) == 6

    def test_generate_fraction_summary_in_output(self, tmp_path: Path):
        cfg = self._make_workspace(tmp_path, fraction=0.25)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["design", "generate", "--phase", "screening", "--config", str(cfg), "-o", str(tmp_path / "d.csv")],
        )
        assert result.exit_code == 0, result.output
        assert "6/24" in result.output


class TestRunDesignFlag:
    """Tests for `retort run --design`."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        cfg = tmp_path / "workspace.yaml"
        cfg.write_text(
            "experiment:\n"
            "  name: test\n"
            "factors:\n"
            "  language:\n"
            "    levels: [python, typescript, go]\n"
            "  model:\n"
            "    levels: [opus, sonnet]\n"
            "responses:\n"
            "  - code_quality\n"
            "tasks:\n"
            "  - source: bundled://rest-api-crud\n"
            "playpen:\n"
            "  runner: local\n"
            "  replicates: 1\n"
        )
        return cfg

    def _make_design_csv(self, tmp_path: Path) -> Path:
        """Write a minimal 2-row design CSV."""
        import pandas as pd
        df = pd.DataFrame([
            {"language": "python", "model": "opus"},
            {"language": "typescript", "model": "sonnet"},
        ])
        path = tmp_path / "design.csv"
        df.to_csv(path, index_label="run")
        return path

    def test_dry_run_with_design_csv(self, tmp_path: Path):
        """--design csv + --dry-run should list only the CSV rows."""
        cfg = self._make_workspace(tmp_path)
        design_csv = self._make_design_csv(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run",
                "--phase", "screening",
                "--config", str(cfg),
                "--design", str(design_csv),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        # Should see exactly 2 run entries in dry-run output
        assert result.output.count("[RUN ]") == 2

    def test_design_csv_must_exist(self, tmp_path: Path):
        """--design pointing to a missing file should fail with exit code != 0."""
        cfg = self._make_workspace(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run",
                "--phase", "screening",
                "--config", str(cfg),
                "--design", str(tmp_path / "nonexistent.csv"),
                "--dry-run",
            ],
        )
        assert result.exit_code != 0

    def test_design_csv_overrides_fraction(self, tmp_path: Path):
        """--design csv should be used even if workspace has design.fraction set."""
        cfg = tmp_path / "workspace.yaml"
        cfg.write_text(
            "experiment:\n"
            "  name: test\n"
            "factors:\n"
            "  language:\n"
            "    levels: [python, typescript, go]\n"
            "  model:\n"
            "    levels: [opus, sonnet]\n"
            "responses:\n"
            "  - code_quality\n"
            "tasks:\n"
            "  - source: bundled://rest-api-crud\n"
            "playpen:\n"
            "  runner: local\n"
            "  replicates: 1\n"
            "design:\n"
            "  fraction: 0.25\n"
        )
        design_csv = self._make_design_csv(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run",
                "--phase", "screening",
                "--config", str(cfg),
                "--design", str(design_csv),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        # CSV has 2 rows, not the fraction-reduced count
        assert result.output.count("[RUN ]") == 2

    def test_dry_run_accepts_configured_local_agents(self, tmp_path: Path):
        """Spec1 local harness profiles should pass run planning."""
        cfg = tmp_path / "workspace.yaml"
        cfg.write_text(
            "experiment:\n"
            "  name: test\n"
            "factors:\n"
            "  language:\n"
            "    levels: [python, go]\n"
            "  agent:\n"
            "    levels: [qwen-local, pi-dense]\n"
            "  model:\n"
            "    levels: [moe, dense]\n"
            "  thinking:\n"
            "    levels: [off, minimal]\n"
            "responses:\n"
            "  - code_quality\n"
            "tasks:\n"
            "  - source: bundled://rest-api-crud\n"
            "playpen:\n"
            "  runner: local\n"
            "  replicates: 1\n"
            "  local_agents:\n"
            "    qwen-local:\n"
            "      harness: omp\n"
            "    pi-dense:\n"
            "      harness: omp\n"
            "      model: dense\n"
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["run", "--phase", "screening", "--config", str(cfg), "--dry-run"],
        )

        assert result.exit_code == 0, result.output
        assert "agent': 'qwen-local'" in result.output
        assert "agent': 'pi-dense'" in result.output


class TestPromptFactor:
    """Tests for the prompt factor and file injection."""

    def _make_workspace_with_prompt(self, tmp_path: Path, prompt_levels: list[str]) -> Path:
        cfg = tmp_path / "workspace.yaml"
        levels_yaml = "[" + ", ".join(prompt_levels) + "]"
        cfg.write_text(
            "experiment:\n"
            "  name: test\n"
            "factors:\n"
            "  language:\n"
            "    levels: [python, go]\n"
            "  prompt:\n"
            f"    levels: {levels_yaml}\n"
            "responses:\n"
            "  - code_quality\n"
            "tasks:\n"
            "  - source: bundled://rest-api-crud\n"
            "playpen:\n"
            "  runner: local\n"
            "  replicates: 1\n"
        )
        return cfg

    def test_none_level_needs_no_file(self, tmp_path: Path):
        """prompt: none must work even when prompts_dir is None (no prompts/ directory)."""
        from retort.playpen.local_runner import LocalRunner
        from retort.playpen.runner import StackConfig, TaskSpec

        runner = LocalRunner(prompts_dir=None)
        stack = StackConfig(language="python", agent="claude-code", framework="unknown",
                            extra={"prompt": "none"})
        task = TaskSpec(name="t", description="d", prompt="Do the thing.")

        cmd = runner._build_agent_command(stack, task)
        assert cmd is not None
        # Base prompt only — no extra text from a file
        prompt_arg = cmd[cmd.index("-p") + 1]
        assert "none" not in prompt_arg  # level name itself should not appear

    def test_named_prompt_injected_into_command(self, tmp_path: Path):
        """A named prompt level appends the file text to the agent prompt."""
        from retort.playpen.local_runner import LocalRunner
        from retort.playpen.runner import StackConfig, TaskSpec

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "concise.md").write_text("Be concise. Minimise token usage.")

        runner = LocalRunner(prompts_dir=prompts_dir)
        stack = StackConfig(language="python", agent="claude-code", framework="unknown",
                            extra={"prompt": "concise"})
        task = TaskSpec(name="t", description="d", prompt="Do the thing.")

        cmd = runner._build_agent_command(stack, task)
        assert cmd is not None
        prompt_arg = cmd[cmd.index("-p") + 1]
        assert "Be concise" in prompt_arg

    def test_missing_prompt_file_raises(self, tmp_path: Path):
        """A non-none prompt level with no matching file must raise FileNotFoundError."""
        import pytest
        from retort.playpen.local_runner import LocalRunner
        from retort.playpen.runner import StackConfig, TaskSpec

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()  # directory exists but file does not

        runner = LocalRunner(prompts_dir=prompts_dir)
        stack = StackConfig(language="python", agent="claude-code", framework="unknown",
                            extra={"prompt": "tdd"})
        task = TaskSpec(name="t", description="d", prompt="Do the thing.")

        with pytest.raises(FileNotFoundError, match="tdd"):
            runner._build_agent_command(stack, task)

    def test_no_prompts_dir_with_named_level_raises(self, tmp_path: Path):
        """Named prompt level with no prompts_dir configured must raise immediately."""
        import pytest
        from retort.playpen.local_runner import LocalRunner
        from retort.playpen.runner import StackConfig, TaskSpec

        runner = LocalRunner(prompts_dir=None)
        stack = StackConfig(language="python", agent="claude-code", framework="unknown",
                            extra={"prompt": "verbose"})
        task = TaskSpec(name="t", description="d", prompt="Do the thing.")

        with pytest.raises(FileNotFoundError, match="prompts directory"):
            runner._build_agent_command(stack, task)


def test_playpen_accepts_local_agent_defaults():
    from retort.config.loader import load_workspace_dict

    cfg = load_workspace_dict(
        {
            "factors": {"language": {"levels": ["python"]}},
            "responses": ["code_quality"],
            "tasks": [{"source": "bundled://rest-api-crud"}],
            "playpen": {
                "runner": "local",
                "model": "moe",
                "thinking": "minimal",
                "local_agents": {
                    "qwen-local": {
                        "harness": "omp",
                        "model": "dense",
                        "thinking": False,
                    },
                },
            },
        }
    )

    assert cfg.playpen.model == "moe"
    assert cfg.playpen.thinking == "minimal"
    assert cfg.playpen.local_agents["qwen-local"].harness == "omp"
    assert cfg.playpen.local_agents["qwen-local"].model == "dense"
    assert cfg.playpen.local_agents["qwen-local"].thinking == "off"


class TestCostLimitEnforcement:
    """Tests for cost_limit_usd enforcement in retort run."""

    def _make_workspace(self, tmp_path: Path, cost_limit: float | None = None) -> Path:
        cfg = tmp_path / "workspace.yaml"
        limit_line = f"  cost_limit_usd: {cost_limit}\n" if cost_limit is not None else ""
        cfg.write_text(
            "experiment:\n"
            "  name: test\n"
            "factors:\n"
            "  language:\n"
            "    levels: [python, go]\n"
            "  model:\n"
            "    levels: [opus, sonnet]\n"
            "responses:\n"
            "  - code_quality\n"
            "tasks:\n"
            "  - source: bundled://rest-api-crud\n"
            "playpen:\n"
            "  runner: local\n"
            "  replicates: 1\n"
            + limit_line
        )
        return cfg

    def _patch_runner(self, monkeypatch, cost_per_run: float = 0.04):
        """Patch LocalRunner + helpers so no real execution happens."""
        from retort.playpen.runner import RunArtifacts, TaskSpec
        from retort.scoring.collector import ScoreVector

        monkeypatch.setattr(
            "retort.playpen.local_runner.LocalRunner.provision",
            lambda *a, **k: "env-1",
        )
        monkeypatch.setattr(
            "retort.playpen.local_runner.LocalRunner.execute",
            lambda *a, **k: RunArtifacts(
                exit_code=0,
                duration_seconds=0.1,
                token_count=10,
                metadata={"total_cost_usd": str(cost_per_run)},
            ),
        )
        monkeypatch.setattr(
            "retort.playpen.local_runner.LocalRunner.teardown",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "retort.scoring.collector.ScoreCollector.collect",
            lambda *a, **k: ScoreVector(scores=[]),
        )
        monkeypatch.setattr(
            "retort.playpen.task_loader.load_task",
            lambda source: TaskSpec(name="test", description="test task", prompt="Do it."),
        )

    def test_run_aborts_when_cost_limit_exceeded(self, tmp_path: Path, monkeypatch):
        """Accumulated cost exceeding cost_limit_usd aborts the run with a clear error."""
        # 2 runs at $0.04 each = $0.08 > $0.05 limit; should abort after first run
        cfg = self._make_workspace(tmp_path, cost_limit=0.05)
        self._patch_runner(monkeypatch, cost_per_run=0.04)

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--phase", "screening", "--config", str(cfg)])

        assert result.exit_code != 0
        assert "cost_limit_usd" in result.output

    def test_run_completes_when_no_cost_limit(self, tmp_path: Path, monkeypatch):
        """Without cost_limit_usd, all runs complete regardless of accumulated cost."""
        cfg = self._make_workspace(tmp_path)  # no cost_limit
        self._patch_runner(monkeypatch, cost_per_run=100.0)

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--phase", "screening", "--config", str(cfg)])

        assert result.exit_code == 0, result.output
        assert "cost_limit_usd" not in result.output


class TestConformanceGate:
    """A run whose tests never executed (test_coverage == 0) is not a valid
    success — the gate marks it failed rather than a zero-scored completion."""

    @staticmethod
    def _scores(**metrics):
        from types import SimpleNamespace
        return SimpleNamespace(
            scores=[SimpleNamespace(metric_name=k, value=v) for k, v in metrics.items()]
        )

    def test_tests_ran_passes(self):
        from retort.cli import _tests_did_not_run
        assert _tests_did_not_run(self._scores(test_coverage=1.0, code_quality=0.8)) is False

    def test_tests_did_not_run_fails(self):
        from retort.cli import _tests_did_not_run
        assert _tests_did_not_run(self._scores(test_coverage=0.0, code_quality=0.0)) is True

    def test_partial_coverage_is_not_gated(self):
        from retort.cli import _tests_did_not_run
        assert _tests_did_not_run(self._scores(test_coverage=0.46)) is False

    def test_no_test_coverage_metric_no_gate(self):
        from retort.cli import _tests_did_not_run
        assert _tests_did_not_run(self._scores(code_quality=0.8)) is False


class TestSecondOpinionGate:
    """The opus second-opinion spec gate: pass if the first eval reaches 1.0;
    else take one more opinion; fail only if both fall short."""

    @staticmethod
    def _patch(monkeypatch, covs):
        import retort.cli as cli
        seq = list(covs)
        calls = {"n": 0}

        def fake_eval(*a, **k):
            calls["n"] += 1

        monkeypatch.setattr(cli, "_run_auto_evaluation", fake_eval)
        monkeypatch.setattr(cli, "_read_requirement_coverage", lambda run_dir: seq.pop(0))
        return calls

    def test_first_pass_short_circuits(self, monkeypatch, tmp_path):
        from retort.cli import _spec_conformance_passes
        calls = self._patch(monkeypatch, [1.0])
        passed, cov = _spec_conformance_passes(tmp_path, object(), "public")
        assert passed is True and cov == 1.0 and calls["n"] == 1

    def test_second_opinion_rescues(self, monkeypatch, tmp_path):
        from retort.cli import _spec_conformance_passes
        calls = self._patch(monkeypatch, [0.83, 1.0])
        passed, cov = _spec_conformance_passes(tmp_path, object(), "public")
        assert passed is True and cov == 1.0 and calls["n"] == 2

    def test_both_fail(self, monkeypatch, tmp_path):
        from retort.cli import _spec_conformance_passes
        calls = self._patch(monkeypatch, [0.83, 0.92])
        passed, cov = _spec_conformance_passes(tmp_path, object(), "public")
        assert passed is False and cov == 0.92 and calls["n"] == 2  # best of the two

    def test_both_none_inconclusive(self, monkeypatch, tmp_path):
        from retort.cli import _spec_conformance_passes
        calls = self._patch(monkeypatch, [None, None])
        verdict, cov = _spec_conformance_passes(tmp_path, object(), "public")
        assert verdict is None and cov is None and calls["n"] == 2

    def test_one_real_one_none_is_inconclusive(self, monkeypatch, tmp_path):
        # One real short eval + one that couldn't run -> inconclusive, NOT a fail
        # (the usage-limit case that must not record a false failure).
        from retort.cli import _spec_conformance_passes
        calls = self._patch(monkeypatch, [0.83, None])
        verdict, cov = _spec_conformance_passes(tmp_path, object(), "public")
        assert verdict is None and cov == 0.83 and calls["n"] == 2


class TestReevaluatePersist:
    """Non-destructive persistence of requirement_coverage onto archived runs."""

    @staticmethod
    def _make_db(path):
        import sqlite3, json
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE experiment_runs (id INTEGER PRIMARY KEY, replicate INTEGER, "
                    "status TEXT, finished_at TEXT, run_config_json TEXT)")
        con.execute("CREATE TABLE run_results (id INTEGER PRIMARY KEY, run_id INTEGER, "
                    "metric_name TEXT, value REAL)")
        cfg = json.dumps({"language": "go", "model": "claude-opus-4-8", "tooling": "none"})
        con.execute("INSERT INTO experiment_runs (id, replicate, status, finished_at, run_config_json) "
                    "VALUES (1, 2, 'completed', '2026-06-01', ?)", (cfg,))
        con.execute("INSERT INTO run_results (run_id, metric_name, value) VALUES (1, 'code_quality', 0.9)")
        con.commit(); con.close()

    def test_persist_and_detect(self, tmp_path):
        from retort.cli import _persist_requirement_coverage, _run_has_requirement_coverage
        db = tmp_path / "retort.db"
        self._make_db(db)
        cfg = {"language": "go", "model": "claude-opus-4-8", "tooling": "none"}
        assert _run_has_requirement_coverage(db, cfg, 2) is False
        assert _persist_requirement_coverage(db, cfg, 2, 0.917) is True
        assert _run_has_requirement_coverage(db, cfg, 2) is True
        import sqlite3
        v = sqlite3.connect(db).execute(
            "SELECT value FROM run_results WHERE metric_name='requirement_coverage'").fetchone()[0]
        assert v == 0.917

    def test_persist_is_idempotent_replace(self, tmp_path):
        from retort.cli import _persist_requirement_coverage
        db = tmp_path / "retort.db"
        self._make_db(db)
        cfg = {"language": "go", "model": "claude-opus-4-8", "tooling": "none"}
        _persist_requirement_coverage(db, cfg, 2, 0.5)
        _persist_requirement_coverage(db, cfg, 2, 1.0)  # replace, not duplicate
        import sqlite3
        rows = sqlite3.connect(db).execute(
            "SELECT value FROM run_results WHERE metric_name='requirement_coverage'").fetchall()
        assert rows == [(1.0,)]

    def test_persist_no_match_returns_false(self, tmp_path):
        from retort.cli import _persist_requirement_coverage
        db = tmp_path / "retort.db"
        self._make_db(db)
        cfg = {"language": "rust", "model": "x", "tooling": "none"}  # no such run
        assert _persist_requirement_coverage(db, cfg, 2, 1.0) is False

    @staticmethod
    def _make_db_no_tooling(path):
        """A run whose run_config_json has NO tooling key (exp-7/8 shape)."""
        import sqlite3, json
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE experiment_runs (id INTEGER PRIMARY KEY, replicate INTEGER, "
                    "status TEXT, finished_at TEXT, run_config_json TEXT)")
        con.execute("CREATE TABLE run_results (id INTEGER PRIMARY KEY, run_id INTEGER, "
                    "metric_name TEXT, value REAL)")
        cfg = json.dumps({"language": "erlang", "model": "claude-opus-4-7"})  # no tooling
        con.execute("INSERT INTO experiment_runs (id, replicate, status, finished_at, run_config_json) "
                    "VALUES (1, 1, 'completed', '2026-06-04', ?)", (cfg,))
        con.commit(); con.close()

    def test_tooling_free_design_matches(self, tmp_path):
        """Regression: a design without a tooling factor must still match.

        run_config is {language, model} with no tooling; the matcher used to do
        `json_extract(...,'$.tooling') = NULL` (never true in SQL), so reevaluate
        found 0 runs and persisted nothing for exp-7/8. The IS NULL fix restores
        matching.
        """
        from retort.cli import (
            _run_completed_exists, _run_has_requirement_coverage,
            _persist_requirement_coverage, _factor_match_sql,
        )
        db = tmp_path / "retort.db"
        self._make_db_no_tooling(db)
        cfg = {"language": "erlang", "model": "claude-opus-4-7"}  # no tooling key

        # the SQL fragment uses IS NULL for the absent tooling factor
        where, params = _factor_match_sql(cfg)
        assert "tooling') IS NULL" in where
        assert params == ["erlang", "claude-opus-4-7"]

        assert _run_completed_exists(db, cfg, 1) is True
        assert _run_has_requirement_coverage(db, cfg, 1) is False
        assert _persist_requirement_coverage(db, cfg, 1, 1.0) is True
        assert _run_has_requirement_coverage(db, cfg, 1) is True

    def test_tooling_free_config_does_not_match_tooled_run(self, tmp_path):
        """A {language,model} query must NOT match a row that has tooling set
        (IS NULL only matches genuinely-absent tooling)."""
        from retort.cli import _run_completed_exists
        db = tmp_path / "retort.db"
        self._make_db(db)  # this run HAS tooling=none
        cfg = {"language": "go", "model": "claude-opus-4-8"}  # no tooling key
        assert _run_completed_exists(db, cfg, 2) is False
