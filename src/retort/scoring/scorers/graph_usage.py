"""Did a `tooling: graphify` run actually CONSULT the graph?

Mirrors `bead_usage` for the graphify tooling level, and exists for the reason
the queue entry states plainly: if the agent never reads the graph, `graphify` is
byte-for-byte identical to `none` and the experiment publishes a false null — a
confident "the knowledge graph does not help" that measured nothing at all.

The hook already refuses to pretend: when graphify is not installed it marks the
cell UNAVAILABLE rather than running as a silent no-op. This closes the other
half — the graph was built, but did the agent open it?

NON-APPLICABLE vs UNVERIFIABLE vs IGNORED. Three states, deliberately distinct:

  * `tooling != graphify` → 1.0. Not applicable; never penalise a run that was
    not asked to use the graph. (Same convention as bead_usage.)
  * no transcript to search → None. `agent_consulted` returns None when no
    transcript exists, and a missing log must NOT be read as "the agent ignored
    it". Non-results are NULL here, as everywhere else in this harness.
  * transcript present, no reference → 0.0. That is a real finding, and the one
    that invalidates a graphify arm.
"""
from __future__ import annotations

import logging

from retort.playpen.runner import RunArtifacts, StackConfig

logger = logging.getLogger(__name__)

#: What consulting the graph looks like in a transcript. The hook writes
#: graphify-out/{graph.json,GRAPH_REPORT.md}, and the prompt names both, so a
#: reading agent references one of them; `graphify ` catches a CLI query.
CONSULT_PATTERNS = ("GRAPH_REPORT.md", "graph.json", "graphify-out", "graphify ")


class GraphUsageScorer:
    """1.0 consulted · 0.0 ignored · None unverifiable · 1.0 not applicable."""

    @property
    def name(self) -> str:
        return "graph_usage_score"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float | None:
        if stack.extra.get("tooling", "none") != "graphify":
            return 1.0
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return None

        from retort.playpen.local_runner import agent_consulted

        consulted = agent_consulted(artifacts.output_dir, *CONSULT_PATTERNS)
        if consulted is None:
            logger.warning(
                "graph_usage_score=NULL for %s: tooling=graphify but no agent "
                "transcript to search. Cannot tell whether the graph was used, "
                "and a missing log is not evidence that it was ignored.",
                artifacts.output_dir,
            )
            return None
        if not consulted:
            logger.warning(
                "graph_usage_score=0 for %s: tooling=graphify but the transcript "
                "never references the graph. This cell is equivalent to "
                "tooling=none — do not read a null from it as 'the graph does "
                "not help'.",
                artifacts.output_dir,
            )
            return 0.0
        return 1.0
