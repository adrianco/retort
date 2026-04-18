"""Scorer plugin registry.

Provides discovery and registration of scorer implementations.
Built-in scorers are registered automatically; custom scorers can be
added via the register() method.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from retort.playpen.runner import RunArtifacts, StackConfig


@runtime_checkable
class Scorer(Protocol):
    """Protocol for response metric scorers.

    A scorer examines run artifacts and produces a numeric score.
    """

    @property
    def name(self) -> str:
        """Unique metric name (e.g., 'code_quality', 'build_time')."""
        ...

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        """Compute the metric value from run artifacts."""
        ...


class ScorerRegistry:
    """Registry of available scorer implementations."""

    def __init__(self) -> None:
        self._scorers: dict[str, Scorer] = {}

    def register(self, scorer: Scorer) -> None:
        """Register a scorer instance."""
        self._scorers[scorer.name] = scorer

    def get(self, name: str) -> Scorer:
        """Get a scorer by name."""
        if name not in self._scorers:
            raise KeyError(
                f"Unknown scorer: {name!r}. "
                f"Available: {sorted(self._scorers.keys())}"
            )
        return self._scorers[name]

    def available(self) -> list[str]:
        """List registered scorer names."""
        return sorted(self._scorers.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._scorers

    def __len__(self) -> int:
        return len(self._scorers)


def create_default_registry() -> ScorerRegistry:
    """Create a registry pre-loaded with built-in and plugin scorers.

    Built-in scorers are registered first, then any scorers discovered
    via the ``retort.plugins`` entry-point group are added.  Plugin
    scorers can override built-ins by using the same ``name``.
    """
    from retort.scoring.scorers.code_quality import CodeQualityScorer
    from retort.scoring.scorers.defect_rate import DefectRateScorer
    from retort.scoring.scorers.idiomatic import IdiomaticScorer
    from retort.scoring.scorers.maintainability import MaintainabilityScorer
    from retort.scoring.scorers.test_coverage import TestCoverageScorer
    from retort.scoring.scorers.test_quality import TestQualityScorer
    from retort.scoring.scorers.token_efficiency import TokenEfficiencyScorer

    registry = ScorerRegistry()
    registry.register(CodeQualityScorer())
    registry.register(TokenEfficiencyScorer())
    registry.register(TestCoverageScorer())
    registry.register(TestQualityScorer())
    registry.register(DefectRateScorer())
    registry.register(MaintainabilityScorer())
    # Opt-in via responses: list — every invocation makes an LLM call.
    registry.register(IdiomaticScorer())
    # build_time was removed in favor of the raw `_duration_seconds`
    # telemetry written automatically by cli._store_run_result. Use that
    # column in retort analyze / report effects for timing analysis.

    # Discover and register plugin scorers
    from retort.plugins import discover_scorers

    for scorer in discover_scorers():
        registry.register(scorer)

    return registry
