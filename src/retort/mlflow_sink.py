"""Optional MLflow result sink.

Logs each experiment run's factor levels, scores, and telemetry to MLflow.
The ``mlflow`` package is imported lazily so this module is safe to reference
even when mlflow is not installed — callers should only invoke
``log_run_to_mlflow`` when the workspace config has an ``mlflow`` block.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from retort.config.schema import MLflowConfig
    from retort.playpen.runner import RunArtifacts
    from retort.scoring.collector import ScoreVector


def _requires_token(tracking_uri: str | None) -> bool:
    """HTTPS endpoints need a bearer token; local/file URIs do not."""
    if not tracking_uri:
        return False
    return tracking_uri.startswith("https://")


def log_run_to_mlflow(
    mlflow_config: MLflowConfig,
    experiment_name: str,
    run_config: dict[str, str],
    phase: str,
    run_idx: int,
    replicate: int,
    artifacts: RunArtifacts,
    scores: ScoreVector,
) -> None:
    """Log a single experiment run to MLflow."""
    import os

    import mlflow  # lazy — optional dependency

    if mlflow_config.tracking_uri:
        mlflow.set_tracking_uri(mlflow_config.tracking_uri)

    if mlflow_config.workspace:
        os.environ["MLFLOW_WORKSPACE"] = mlflow_config.workspace

    if _requires_token(mlflow_config.tracking_uri):
        if not os.environ.get("MLFLOW_TRACKING_TOKEN"):
            raise RuntimeError(
                "MLFLOW_TRACKING_TOKEN is not set. "
                "Set it before running retort:\n"
                "  export MLFLOW_TRACKING_TOKEN=$(oc whoami -t)"
            )

    mlflow.set_experiment(mlflow_config.experiment or experiment_name)

    run_name = f"{phase}-{run_idx}-rep{replicate}"
    with mlflow.start_run(run_name=run_name):
        for factor, level in run_config.items():
            mlflow.log_param(factor, level)
        mlflow.log_param("phase", phase)
        mlflow.log_param("run_idx", run_idx)
        mlflow.log_param("replicate", replicate)

        for score in scores.scores:
            mlflow.log_metric(score.metric_name, score.value)

        if artifacts.duration_seconds:
            mlflow.log_metric("duration_s", float(artifacts.duration_seconds))
        if artifacts.token_count:
            mlflow.log_metric("tokens", float(artifacts.token_count))

        meta = artifacts.metadata or {}
        cost = meta.get("total_cost_usd")
        if cost is not None:
            try:
                mlflow.log_metric("cost_usd", float(cost))
            except (TypeError, ValueError):
                pass
        turns = meta.get("num_turns")
        if turns is not None:
            try:
                val = float(turns)
                if val > 0:
                    mlflow.log_metric("turns", val)
            except (TypeError, ValueError):
                pass

        status = "completed" if artifacts.succeeded else "failed"
        mlflow.set_tag("retort.phase", phase)
        mlflow.set_tag("retort.status", status)
        for key, val in mlflow_config.tags.items():
            mlflow.set_tag(key, val)
