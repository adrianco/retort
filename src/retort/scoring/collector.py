"""Score collector — orchestrates scorer plugins for a run."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring.registry import ScorerRegistry, create_default_registry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoreResult:
    """A single scored metric."""

    metric_name: str
    value: float


@dataclass
class ScoreVector:
    """All scored metrics for a single run."""

    scores: list[ScoreResult]

    def to_dict(self) -> dict[str, float]:
        return {s.metric_name: s.value for s in self.scores}

    def get(self, metric_name: str) -> float | None:
        for s in self.scores:
            if s.metric_name == metric_name:
                return s.value
        return None


class ScoreCollector:
    """Orchestrates scorer execution for experiment runs.

    Runs all requested scorers against run artifacts and collects
    the results into a ScoreVector.
    """

    def __init__(
        self,
        metrics: list[str] | None = None,
        registry: ScorerRegistry | None = None,
    ) -> None:
        self.registry = registry or create_default_registry()
        self.metrics = metrics or self.registry.available()

    def collect(self, artifacts: RunArtifacts, stack: StackConfig) -> ScoreVector:
        """Score a run across all configured metrics."""
        results: list[ScoreResult] = []

        for metric_name in self.metrics:
            if metric_name not in self.registry:
                logger.debug("Scorer %r not found, skipping", metric_name)
                continue

            scorer = self.registry.get(metric_name)
            try:
                value = scorer.score(artifacts, stack)
                results.append(ScoreResult(metric_name=metric_name, value=value))
            except Exception:
                logger.exception("Scorer %r failed on run", metric_name)
                results.append(ScoreResult(metric_name=metric_name, value=0.0))

        return ScoreVector(scores=results)
