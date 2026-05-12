"""Bead usage scorer.

Measures whether the agent used the beads issue tracker during a run.
Only meaningful when the ``tooling`` factor is set to ``"beads"``.
For all other tooling values the metric is not applicable and returns 1.0.

Detection strategy:
- Primary: check for a ``.beads/`` directory in the workspace (written by
  ``bd init``).  If present, count entries in ``interactions.jsonl`` as a
  proxy for bead operation volume.
- Fallback: count any non-config files in ``.beads/`` when the interactions
  log is absent.

A score of 0.0 means the agent was asked to use beads but produced zero
detectable bead activity.  A score of 1.0 means the agent performed at
least EXPECTED_MIN_OPS bead operations.
"""

from __future__ import annotations

import logging
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig

logger = logging.getLogger(__name__)

# Minimum bead operations for a full-credit score.  Represents a minimal
# useful beads session: bd init + a few bd create + bd update + bd close.
EXPECTED_MIN_OPS = 5


class BeadUsageScorer:
    """Scores how consistently the agent used the beads issue tracker.

    Score range: 0.0 (beads completely ignored) to 1.0 (active beads use).
    Returns 1.0 when ``tooling != "beads"`` — the metric is not applicable
    and should not penalise runs that were never expected to use beads.
    """

    @property
    def name(self) -> str:
        return "bead_usage_score"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        tooling = stack.extra.get("tooling", "none")
        if tooling != "beads":
            return 1.0

        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0.0

        bead_ops = _count_bead_ops(artifacts.output_dir)

        if bead_ops == 0:
            logger.warning(
                "bead_usage_score=0 for run in %s: agent produced no detectable "
                "bead activity despite tooling=beads.  Common cause: bd init was "
                "never called, or context window filled before the agent reached "
                "the task-tracking phase.",
                artifacts.output_dir.name,
            )
            return 0.0

        return min(1.0, bead_ops / EXPECTED_MIN_OPS)


def _count_bead_ops(workspace: Path) -> int:
    """Count bead operations recorded in the workspace's .beads directory."""
    beads_dir = workspace / ".beads"
    if not beads_dir.exists():
        return 0

    # Primary signal: interactions log written by every bd command.
    interactions = beads_dir / "interactions.jsonl"
    if interactions.exists():
        try:
            lines = [l for l in interactions.read_text().splitlines() if l.strip()]
            return len(lines)
        except OSError:
            pass

    # Secondary signal: audit log (written by higher-level operations).
    audit = beads_dir / "audit.log"
    if audit.exists():
        try:
            lines = [l for l in audit.read_text().splitlines() if l.strip()]
            return len(lines)
        except OSError:
            pass

    # Fallback: treat any files beyond a lone config as evidence of activity.
    try:
        files = [f for f in beads_dir.iterdir() if f.name != "config.yaml"]
        return len(files)
    except OSError:
        return 0
