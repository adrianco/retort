"""Build time scorer.

Measures wall-clock time to first green build / successful completion.
Lower is better.
"""

from __future__ import annotations

from retort.playpen.runner import RunArtifacts, StackConfig

# Target: complete a task in under 5 minutes
TARGET_SECONDS = 300.0

# Maximum allowed time (for normalization)
MAX_SECONDS = 1800.0


class BuildTimeScorer:
    """Scores based on how quickly the agent completes the task.

    Score range: 0.0 (slowest/failed) to 1.0 (fastest).
    Uses inverse linear scaling against the target time.
    """

    @property
    def name(self) -> str:
        return "build_time"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if not artifacts.succeeded:
            return 0.0

        duration = artifacts.duration_seconds
        if duration <= 0:
            return 0.5  # No timing data

        if duration <= TARGET_SECONDS:
            # Linear scale from target (1.0) down to fast bonus region
            return min(1.0, 1.0 - (duration / TARGET_SECONDS) * 0.2 + 0.2)

        # Beyond target — linear decay to 0
        if duration >= MAX_SECONDS:
            return 0.0

        return max(0.0, 1.0 - (duration - TARGET_SECONDS) / (MAX_SECONDS - TARGET_SECONDS))
