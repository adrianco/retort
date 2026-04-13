"""Build time scorer.

Measures wall-clock time to first green build / successful completion.
Lower duration → higher score. Continuous and monotonic in duration so
ANOVA captures real per-cell differences.

The previous formula collapsed every run under ~5 minutes to score=1.0,
which made build_time a useless constant for any experiment whose runs
finish quickly (which is most of them). The new formula gives a smooth
inverse linear from 1.0 at 0s down to 0.0 at MAX_SECONDS — every cell
gets a distinct score in proportion to how long it took.
"""

from __future__ import annotations

from retort.playpen.runner import RunArtifacts, StackConfig

# Score 0.0 at this many seconds — anything slower is treated as
# "essentially timed out" for scoring purposes (the actual playpen timeout
# is configured separately in workspace.yaml). 1800s = 30 min.
MAX_SECONDS = 1800.0


class BuildTimeScorer:
    """Scores based on how quickly the agent completes the task.

    Score range: 0.0 (slowest/failed) to 1.0 (instant).
    Linear inverse against MAX_SECONDS so every duration produces a
    distinct score — ANOVA can find effects.
    """

    @property
    def name(self) -> str:
        return "build_time"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if not artifacts.succeeded:
            return 0.0

        duration = artifacts.duration_seconds
        if duration <= 0:
            return 0.5  # no timing data

        return max(0.0, 1.0 - duration / MAX_SECONDS)
