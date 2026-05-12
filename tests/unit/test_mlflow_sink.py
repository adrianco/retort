"""Tests for the MLflow result sink."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from unittest.mock import MagicMock, call, patch

import pytest

from retort.config.schema import MLflowConfig
from retort.scoring.collector import ScoreResult, ScoreVector


@dataclass
class FakeArtifacts:
    succeeded: bool = True
    stderr: str = ""
    duration_seconds: float = 42.5
    token_count: int = 1200
    metadata: dict[str, str] = field(default_factory=lambda: {
        "total_cost_usd": "0.0350",
        "num_turns": "12",
    })


def _make_scores() -> ScoreVector:
    return ScoreVector(scores=[
        ScoreResult(metric_name="code_quality", value=0.85),
        ScoreResult(metric_name="test_coverage", value=0.72),
    ])


def _make_run_config() -> dict[str, str]:
    return {"language": "python", "agent": "claude-code"}


def _call_with_mock_mlflow(
    cfg: MLflowConfig,
    experiment_name: str = "exp",
    run_config: dict[str, str] | None = None,
    phase: str = "screening",
    run_idx: int = 0,
    replicate: int = 1,
    artifacts: FakeArtifacts | None = None,
    scores: ScoreVector | None = None,
    *,
    set_token: bool = True,
) -> MagicMock:
    mock_mlflow = MagicMock()
    env_patch = {"MLFLOW_TRACKING_TOKEN": "fake-token"} if set_token else {}
    with (
        patch.dict(sys.modules, {"mlflow": mock_mlflow}),
        patch.dict(os.environ, env_patch, clear=False),
    ):
        from retort.mlflow_sink import log_run_to_mlflow
        log_run_to_mlflow(
            cfg, experiment_name,
            run_config or _make_run_config(),
            phase, run_idx, replicate,
            artifacts or FakeArtifacts(),
            scores or _make_scores(),
        )
    return mock_mlflow


def test_logs_params_metrics_tags() -> None:
    cfg = MLflowConfig(experiment="test-exp", tags={"team": "ai-eng"})
    m = _call_with_mock_mlflow(cfg, experiment_name="fallback-name")

    m.set_experiment.assert_called_once_with("test-exp")
    m.start_run.assert_called_once_with(run_name="screening-0-rep1")

    param_calls = m.log_param.call_args_list
    assert call("language", "python") in param_calls
    assert call("agent", "claude-code") in param_calls
    assert call("phase", "screening") in param_calls
    assert call("replicate", 1) in param_calls

    metric_calls = m.log_metric.call_args_list
    assert call("code_quality", 0.85) in metric_calls
    assert call("test_coverage", 0.72) in metric_calls
    assert call("duration_s", 42.5) in metric_calls
    assert call("tokens", 1200.0) in metric_calls
    assert call("cost_usd", 0.035) in metric_calls
    assert call("turns", 12.0) in metric_calls

    tag_calls = m.set_tag.call_args_list
    assert call("retort.phase", "screening") in tag_calls
    assert call("retort.status", "completed") in tag_calls
    assert call("team", "ai-eng") in tag_calls


def test_uses_tracking_uri() -> None:
    cfg = MLflowConfig(tracking_uri="http://mlflow:5000")
    m = _call_with_mock_mlflow(cfg)

    m.set_tracking_uri.assert_called_once_with("http://mlflow:5000")


def test_sets_workspace_env_var() -> None:
    cfg = MLflowConfig(workspace="evalhub")
    mock_mlflow = MagicMock()
    with (
        patch.dict(sys.modules, {"mlflow": mock_mlflow}),
        patch.dict(os.environ, {"MLFLOW_TRACKING_TOKEN": "fake"}, clear=False),
    ):
        from retort.mlflow_sink import log_run_to_mlflow
        log_run_to_mlflow(
            cfg, "exp", _make_run_config(), "screening", 0, 1,
            FakeArtifacts(), _make_scores(),
        )
        assert os.environ["MLFLOW_WORKSPACE"] == "evalhub"


def test_missing_token_raises_for_https() -> None:
    cfg = MLflowConfig(tracking_uri="https://mlflow.example.com")
    with (
        patch.dict(os.environ, {}, clear=False),
        pytest.raises(RuntimeError, match="MLFLOW_TRACKING_TOKEN"),
    ):
        os.environ.pop("MLFLOW_TRACKING_TOKEN", None)
        _call_with_mock_mlflow(cfg, set_token=False)


def test_no_token_ok_for_local_uri() -> None:
    cfg = MLflowConfig(tracking_uri="http://localhost:5000")
    os.environ.pop("MLFLOW_TRACKING_TOKEN", None)
    m = _call_with_mock_mlflow(cfg, set_token=False)
    m.set_experiment.assert_called_once()


def test_falls_back_to_experiment_name() -> None:
    cfg = MLflowConfig()
    m = _call_with_mock_mlflow(cfg, experiment_name="fallback-name")

    m.set_experiment.assert_called_once_with("fallback-name")


def test_failed_run_tags_status() -> None:
    cfg = MLflowConfig()
    artifacts = FakeArtifacts(succeeded=False, stderr="build failed")
    m = _call_with_mock_mlflow(cfg, artifacts=artifacts)

    tag_calls = m.set_tag.call_args_list
    assert call("retort.status", "failed") in tag_calls


def test_missing_telemetry_skipped() -> None:
    cfg = MLflowConfig()
    artifacts = FakeArtifacts(
        duration_seconds=0, token_count=0, metadata={},
    )
    m = _call_with_mock_mlflow(
        cfg, artifacts=artifacts, scores=ScoreVector(scores=[]),
    )

    metric_names = [c.args[0] for c in m.log_metric.call_args_list]
    assert "duration_s" not in metric_names
    assert "tokens" not in metric_names
    assert "cost_usd" not in metric_names
    assert "turns" not in metric_names


def test_mlflow_config_in_workspace_config() -> None:
    from retort.config.schema import WorkspaceConfig

    cfg = WorkspaceConfig(
        factors={"lang": {"levels": ["python"]}},
        responses=["code_quality"],
        tasks=[{"source": "bundled://rest-api-crud"}],
        mlflow={"experiment": "test", "tags": {"k": "v"}},
    )
    assert cfg.mlflow is not None
    assert cfg.mlflow.experiment == "test"
    assert cfg.mlflow.tags == {"k": "v"}


def test_mlflow_config_defaults_to_none() -> None:
    from retort.config.schema import WorkspaceConfig

    cfg = WorkspaceConfig(
        factors={"lang": {"levels": ["python"]}},
        responses=["code_quality"],
        tasks=[{"source": "bundled://rest-api-crud"}],
    )
    assert cfg.mlflow is None
