"""Findings scorer — reads assessment.json produced by the file-run-issues skill."""

from __future__ import annotations

import json

from retort.playpen.runner import RunArtifacts, StackConfig


class FindingsScorer:
    """Scores a run using the penalty_score from assessment.json.

    Returns the penalty_score directly (1.0 = no findings, 0.0 = critical failures).
    Returns 0.5 (neutral) when assessment.json is absent — evaluate-run not yet run.
    Never raises; all exceptions return 0.5.
    """

    @property
    def name(self) -> str:
        return "findings"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        try:
            if artifacts.output_dir is None or not artifacts.output_dir.exists():
                return 0.5
            assessment_path = artifacts.output_dir / "assessment.json"
            if not assessment_path.exists():
                return 0.5
            data = json.loads(assessment_path.read_text())
            return float(data["penalty_score"])
        except Exception:
            return 0.5
