"""Tests for auto-evaluation wiring (schema + CLI helpers)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from retort.cli import (
    _evaluation_is_current,
    _find_skill,
    _run_auto_evaluation,
    main as cli,
)
from retort.config.loader import load_workspace
from retort.config.schema import EvaluationConfig, WorkspaceConfig


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def _minimal_cfg(**extra):
    base = {
        "factors": {"a": {"levels": ["x", "y"]}, "b": {"levels": ["p", "q"]}},
        "responses": ["m"],
        "tasks": [{"source": "bundled://foo"}],
    }
    base.update(extra)
    return base


def test_evaluation_defaults_apply_when_block_absent():
    cfg = WorkspaceConfig.model_validate(_minimal_cfg())
    assert cfg.evaluation.enabled is True
    assert cfg.evaluation.model == "haiku"
    assert cfg.evaluation.min_severity_to_file == "high"
    assert cfg.evaluation.issue_tracker == "beads"


def test_evaluation_block_overrides_defaults():
    cfg = WorkspaceConfig.model_validate(
        _minimal_cfg(
            evaluation={
                "enabled": False,
                "model": "sonnet",
                "min_severity_to_file": "critical",
                "issue_tracker": "both",
            }
        )
    )
    assert cfg.evaluation.enabled is False
    assert cfg.evaluation.model == "sonnet"
    assert cfg.evaluation.min_severity_to_file == "critical"
    assert cfg.evaluation.issue_tracker == "both"


def test_evaluation_rejects_invalid_severity():
    with pytest.raises(Exception):
        WorkspaceConfig.model_validate(
            _minimal_cfg(evaluation={"min_severity_to_file": "bogus"})
        )


def test_evaluation_rejects_invalid_tracker():
    with pytest.raises(Exception):
        WorkspaceConfig.model_validate(
            _minimal_cfg(evaluation={"issue_tracker": "gitlab"})
        )


# ---------------------------------------------------------------------------
# Idempotence helper
# ---------------------------------------------------------------------------

def test_evaluation_is_current_true_when_eval_newer(tmp_path: Path):
    run = tmp_path / "rep1"
    run.mkdir()
    (run / "source.py").write_text("x=1")
    time.sleep(0.02)
    (run / "evaluation.md").write_text("# report")
    assert _evaluation_is_current(run) is True


def test_evaluation_is_current_false_when_source_newer(tmp_path: Path):
    run = tmp_path / "rep1"
    run.mkdir()
    (run / "evaluation.md").write_text("# report")
    time.sleep(0.02)
    (run / "source.py").write_text("x=1")
    assert _evaluation_is_current(run) is False


def test_evaluation_is_current_false_when_no_report(tmp_path: Path):
    run = tmp_path / "rep1"
    run.mkdir()
    (run / "source.py").write_text("x=1")
    assert _evaluation_is_current(run) is False


def test_evaluation_is_current_ignores_findings_and_summary(tmp_path: Path):
    run = tmp_path / "rep1"
    run.mkdir()
    (run / "source.py").write_text("x=1")
    time.sleep(0.02)
    (run / "evaluation.md").write_text("# report")
    time.sleep(0.02)
    # findings.jsonl and summary/ are outputs of the evaluator itself.
    (run / "findings.jsonl").write_text('{"x":1}\n')
    (run / "summary").mkdir()
    (run / "summary" / "index.md").write_text("## s")
    assert _evaluation_is_current(run) is True


# ---------------------------------------------------------------------------
# Auto-evaluation wrapper
# ---------------------------------------------------------------------------

def test_auto_evaluation_disabled_does_nothing(tmp_path: Path):
    run = tmp_path / "rep1"
    run.mkdir()
    cfg = EvaluationConfig(enabled=False)
    with patch("retort.cli._invoke_claude_skill") as m:
        _run_auto_evaluation(run, cfg, visibility="public")
        m.assert_not_called()


def test_auto_evaluation_skips_when_current(tmp_path: Path):
    run = tmp_path / "rep1"
    run.mkdir()
    (run / "source.py").write_text("x=1")
    time.sleep(0.02)
    (run / "evaluation.md").write_text("# r")
    cfg = EvaluationConfig(enabled=True)
    with patch("retort.cli._invoke_claude_skill") as m:
        _run_auto_evaluation(run, cfg, visibility="public")
        m.assert_not_called()


def test_auto_evaluation_private_forces_beads_tracker(tmp_path: Path):
    # Provide fake skills directory adjacent to run_dir so _find_skill succeeds.
    exp = tmp_path / "experiment"
    exp.mkdir()
    skills = exp / "skills"
    (skills / "evaluate-run").mkdir(parents=True)
    (skills / "evaluate-run" / "SKILL.md").write_text("# skill")
    (skills / "file-run-issues").mkdir(parents=True)
    (skills / "file-run-issues" / "SKILL.md").write_text("# skill")

    run = exp / "runs" / "cell=x" / "rep1"
    run.mkdir(parents=True)
    (run / "source.py").write_text("x=1")

    cfg = EvaluationConfig(enabled=True, issue_tracker="github")

    calls: list[dict] = []

    def fake_invoke(skill_path, params, model, timeout=300):
        calls.append({"skill": skill_path.parent.name, "params": params})
        return 0, ""

    with patch("retort.cli._invoke_claude_skill", side_effect=fake_invoke):
        _run_auto_evaluation(run, cfg, visibility="private")

    # evaluate-run fires, then file-run-issues with tracker forced to beads.
    kinds = [c["skill"] for c in calls]
    assert "evaluate-run" in kinds
    assert "file-run-issues" in kinds
    fri = next(c for c in calls if c["skill"] == "file-run-issues")
    assert fri["params"]["tracker"] == "beads"


def test_auto_evaluation_public_respects_configured_tracker(tmp_path: Path):
    exp = tmp_path / "experiment"
    (exp / "skills" / "evaluate-run").mkdir(parents=True)
    (exp / "skills" / "evaluate-run" / "SKILL.md").write_text("# skill")
    (exp / "skills" / "file-run-issues").mkdir(parents=True)
    (exp / "skills" / "file-run-issues" / "SKILL.md").write_text("# skill")

    run = exp / "runs" / "cell=x" / "rep1"
    run.mkdir(parents=True)
    (run / "source.py").write_text("x=1")

    cfg = EvaluationConfig(enabled=True, issue_tracker="both")
    calls: list[dict] = []

    def fake_invoke(skill_path, params, model, timeout=300):
        calls.append({"skill": skill_path.parent.name, "params": params})
        return 0, ""

    with patch("retort.cli._invoke_claude_skill", side_effect=fake_invoke):
        _run_auto_evaluation(run, cfg, visibility="public")

    fri = next(c for c in calls if c["skill"] == "file-run-issues")
    assert fri["params"]["tracker"] == "both"


def test_auto_evaluation_swallows_skill_failure(tmp_path: Path):
    exp = tmp_path / "experiment"
    (exp / "skills" / "evaluate-run").mkdir(parents=True)
    (exp / "skills" / "evaluate-run" / "SKILL.md").write_text("# skill")

    run = exp / "runs" / "cell=x" / "rep1"
    run.mkdir(parents=True)
    (run / "source.py").write_text("x=1")

    cfg = EvaluationConfig(enabled=True)
    with patch(
        "retort.cli._invoke_claude_skill", return_value=(1, "boom")
    ):
        # Should not raise — evaluation failure must never abort the experiment.
        _run_auto_evaluation(run, cfg, visibility="public")


# ---------------------------------------------------------------------------
# Skill lookup
# ---------------------------------------------------------------------------

def test_find_skill_walks_up_to_repo(tmp_path: Path):
    (tmp_path / "skills" / "my-skill").mkdir(parents=True)
    skill = tmp_path / "skills" / "my-skill" / "SKILL.md"
    skill.write_text("# x")
    nested = tmp_path / "runs" / "cell" / "rep1"
    nested.mkdir(parents=True)
    found = _find_skill("my-skill", start=nested)
    assert found == skill


def test_find_skill_returns_none_when_absent(tmp_path: Path):
    assert _find_skill("does-not-exist", start=tmp_path) is None


# ---------------------------------------------------------------------------
# CLI: retort evaluate and retort report compare
# ---------------------------------------------------------------------------

def _write_workspace(ws: Path) -> Path:
    ws.mkdir(parents=True, exist_ok=True)
    cfg = {
        "experiment": {"name": "t", "visibility": "public"},
        "factors": {"a": {"levels": ["x", "y"]}, "b": {"levels": ["p", "q"]}},
        "responses": ["m"],
        "tasks": [{"source": "bundled://foo"}],
        "evaluation": {"enabled": True, "model": "haiku", "issue_tracker": "beads"},
    }
    path = ws / "workspace.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_evaluate_command_invokes_skill(tmp_path: Path):
    ws = tmp_path / "exp"
    _write_workspace(ws)
    (ws / "skills" / "evaluate-run").mkdir(parents=True)
    (ws / "skills" / "evaluate-run" / "SKILL.md").write_text("# x")
    (ws / "skills" / "file-run-issues").mkdir(parents=True)
    (ws / "skills" / "file-run-issues" / "SKILL.md").write_text("# x")

    run = ws / "runs" / "cell=x" / "rep1"
    run.mkdir(parents=True)
    (run / "source.py").write_text("x=1")

    calls: list = []

    def fake_invoke(skill_path, params, model, timeout=300):
        calls.append(skill_path.parent.name)
        return 0, ""

    runner = CliRunner()
    with patch("retort.cli._invoke_claude_skill", side_effect=fake_invoke):
        result = runner.invoke(
            cli,
            ["evaluate", str(run), "--config", str(ws / "workspace.yaml")],
        )
    assert result.exit_code == 0, result.output
    assert "evaluate-run" in calls


def test_report_compare_invokes_compare_skill(tmp_path: Path):
    ws = tmp_path / "exp"
    _write_workspace(ws)
    (ws / "skills" / "compare-runs").mkdir(parents=True)
    (ws / "skills" / "compare-runs" / "SKILL.md").write_text("# x")

    calls: list = []

    def fake_invoke(skill_path, params, model, timeout=300):
        calls.append((skill_path.parent.name, params))
        return 0, "ok"

    runner = CliRunner()
    with patch("retort.cli._invoke_claude_skill", side_effect=fake_invoke):
        result = runner.invoke(
            cli,
            [
                "report", "compare",
                "--experiment-dir", str(ws),
                "--config", str(ws / "workspace.yaml"),
                "--group-by", "a,b",
            ],
        )
    assert result.exit_code == 0, result.output
    assert calls and calls[0][0] == "compare-runs"
    assert calls[0][1]["group_by"] == "a,b"
