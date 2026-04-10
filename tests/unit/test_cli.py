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
