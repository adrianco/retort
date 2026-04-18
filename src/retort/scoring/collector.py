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
        """Score a run across all configured metrics.

        If tests did not execute (test_coverage == 0.0), all scores are zeroed.
        A run where tests can't run is a failure regardless of code quality —
        we have no evidence the code actually works.
        """
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

        # Gate: if tests didn't run, zero everything. Also ensure test_coverage
        # is included in the result set so the gate is always visible.
        test_cov = next(
            (r.value for r in results if r.metric_name == "test_coverage"), None
        )
        if test_cov is None and "test_coverage" in self.registry:
            # test_coverage wasn't a requested metric — run it anyway for the gate.
            try:
                from retort.scoring.scorers.test_coverage import TestCoverageScorer
                test_cov = TestCoverageScorer().score(artifacts, stack)
            except Exception:
                test_cov = None

        if test_cov == 0.0:
            logger.info("test_coverage=0 — zeroing all scores (tests did not execute)")
            results = [ScoreResult(metric_name=r.metric_name, value=0.0) for r in results]

        return ScoreVector(scores=results)
