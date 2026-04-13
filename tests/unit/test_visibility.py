"""Tests for experiment.visibility flag and the visibility-check command."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from retort.cli import main
from retort.config.loader import load_workspace
from retort.config.schema import ExperimentConfig, WorkspaceConfig

MINIMAL_WORKSPACE = """\
factors:
  language:
    levels: [python, go]
  agent:
    levels: [a, b]
responses:
  - code_quality
tasks:
  - source: bundled://rest-api-crud
"""


def _write(path: Path, body: str) -> Path:
    path.write_text(body)
    return path


def test_visibility_defaults_to_private(tmp_path: Path) -> None:
    cfg_path = _write(tmp_path / "workspace.yaml", MINIMAL_WORKSPACE)
    cfg = load_workspace(cfg_path)
    assert cfg.experiment.visibility == "private"


def test_visibility_explicit_public(tmp_path: Path) -> None:
    cfg_path = _write(
        tmp_path / "workspace.yaml",
        "experiment:\n  visibility: public\n" + MINIMAL_WORKSPACE,
    )
    cfg = load_workspace(cfg_path)
    assert cfg.experiment.visibility == "public"


def test_visibility_invalid_value_rejected() -> None:
    with pytest.raises(Exception):
        WorkspaceConfig.model_validate(
            {
                "experiment": {"visibility": "secret"},
                "factors": {"a": {"levels": ["x", "y"]}, "b": {"levels": ["1", "2"]}},
                "responses": ["q"],
                "tasks": [{"source": "bundled://t"}],
            }
        )


def test_experiment_config_default() -> None:
    ec = ExperimentConfig()
    assert ec.visibility == "private"
    assert ec.name is None


def test_init_writes_private_gitignore(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "ws-priv"
    result = runner.invoke(main, ["init", str(target)])
    assert result.exit_code == 0, result.output
    gitignore = (target / ".gitignore").read_text()
    assert "runs/" in gitignore
    assert "reports/" in gitignore
    assert "evaluation.md" in gitignore
    workspace_yaml = (target / "workspace.yaml").read_text()
    assert "visibility: private" in workspace_yaml


def test_init_writes_public_gitignore(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "ws-pub"
    result = runner.invoke(main, ["init", str(target), "--visibility", "public"])
    assert result.exit_code == 0, result.output
    gitignore = (target / ".gitignore").read_text()
    # Public mode should NOT ignore runs/ or reports/ as standalone entries.
    lines = {ln.strip() for ln in gitignore.splitlines() if ln.strip() and not ln.startswith("#")}
    assert "runs/" not in lines
    assert "reports/" not in lines
    workspace_yaml = (target / "workspace.yaml").read_text()
    assert "visibility: public" in workspace_yaml


def test_visibility_check_clean_private(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "ws"
    runner.invoke(main, ["init", str(target)])
    # Create a sensitive path that *is* properly ignored.
    (target / "runs").mkdir()
    (target / "runs" / "stub").write_text("data")
    result = runner.invoke(main, ["visibility-check", "--config", str(target / "workspace.yaml")])
    assert result.exit_code == 0, result.output
    assert "LOCAL" in result.output
    assert "runs" in result.output


def test_visibility_check_detects_leak(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "ws-leak"
    runner.invoke(main, ["init", str(target)])
    # Sabotage: remove runs/ from .gitignore so a private workspace leaks it.
    gi = target / ".gitignore"
    gi.write_text(gi.read_text().replace("runs/\n", ""))
    (target / "runs").mkdir()
    result = runner.invoke(main, ["visibility-check", "--config", str(target / "workspace.yaml")])
    assert result.exit_code != 0
    assert "leak" in result.output.lower() or "leak" in (result.stderr or "").lower() or "ERROR" in result.output


def test_visibility_check_public_no_leak(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "ws-pub"
    runner.invoke(main, ["init", str(target), "--visibility", "public"])
    (target / "runs").mkdir()
    (target / "runs" / "x.txt").write_text("ok")
    result = runner.invoke(main, ["visibility-check", "--config", str(target / "workspace.yaml")])
    assert result.exit_code == 0, result.output
    # runs/ should be reported as PUBLISH in public mode.
    assert "PUBLISH" in result.output
