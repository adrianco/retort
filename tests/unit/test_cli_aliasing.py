"""CLI integration tests for the report aliasing command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from retort.cli import main as cli


@pytest.fixture
def workspace_yaml(tmp_path: Path) -> Path:
    """Create a minimal workspace YAML for testing."""
    config = tmp_path / "workspace.yaml"
    config.write_text("""\
factors:
  language:
    levels: [python, go]
  agent:
    levels: [claude, copilot]
  framework:
    levels: [fastapi, stdlib]
  app_type:
    levels: [rest-api, cli-tool]
""")
    return config


class TestReportAliasingCli:
    def test_text_output(self, workspace_yaml: Path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["report", "aliasing", "--config", str(workspace_yaml), "--phase", "screening"],
        )
        assert result.exit_code == 0, result.output
        assert "Aliasing / Confounding Report" in result.output
        assert "language" in result.output

    def test_json_output(self, workspace_yaml: Path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "report", "aliasing",
                "--config", str(workspace_yaml),
                "--phase", "screening",
                "--format", "json",
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["n_factors"] == 4
        assert "alias_groups" in data

    def test_characterization_phase(self, workspace_yaml: Path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "report", "aliasing",
                "--config", str(workspace_yaml),
                "--phase", "characterization",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Aliasing / Confounding Report" in result.output

    def test_max_order_option(self, workspace_yaml: Path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "report", "aliasing",
                "--config", str(workspace_yaml),
                "--max-order", "1",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_output_to_file(self, workspace_yaml: Path, tmp_path: Path):
        out_file = tmp_path / "aliasing.txt"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "report", "aliasing",
                "--config", str(workspace_yaml),
                "-o", str(out_file),
            ],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        content = out_file.read_text()
        assert "Aliasing / Confounding Report" in content
