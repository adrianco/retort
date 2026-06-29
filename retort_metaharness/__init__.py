"""retort-metaharness — DoE/ANOVA methodology layer for benchmarking
agentic-orchestration harnesses on top of Retort.

This package is the *methodology / feature* layer. It does NOT reimplement
Retort's design-matrix generation, ANOVA engine, Pareto sorter, or the
per-cell `playpen` runner — it *composes* them:

- factors.py   : our factors (model / harness-config / scaffold / language /
                 task) as first-class Retort DoE factors, with documented levels.
- design.py    : fractional-factorial screening + full-factorial confirmation
                 over those factors, with aliasing/confounding reported.
                 (wraps retort.design.generator + retort.design.aliasing)
- runner.py    : glue that invokes the per-cell metaharness `playpen` runner
                 (built separately) toggling model routing / agenticow memory /
                 darwin genome per the factor levels; plus a $0 LocalStubRunner
                 for end-to-end pipeline smoke tests.
- analysis.py  : Type-II ANOVA variance decomposition (% variance per factor),
                 i.e. "how much of any lift is the memory branching vs the raw
                 model". (wraps retort.analysis.anova)
- diagnose.py  : TOOLING_FALSE_FAIL vs GENUINE_MODEL_FAIL classification via the
                 "$0 / instant failure = harness bug" invariant.
- report.py    : effects table + accuracy-vs-cost Pareto + Wardley/maturity
                 overlay. (wraps retort.analysis.pareto, reuses classify_phase)
- cli.py       : retort-metaharness design | run | analyze | diagnose | report
"""

from __future__ import annotations

__version__ = "0.1.0"

# Canonical response (output) metric names used across the package.
RESP_REQUIREMENT_COVERAGE = "requirement_coverage"
RESP_CODE_QUALITY = "code_quality"
RESP_COST_PER_TASK = "cost_per_task"
RESP_LATENCY = "latency_s"

DEFAULT_RESPONSES = (
    RESP_REQUIREMENT_COVERAGE,
    RESP_CODE_QUALITY,
    RESP_COST_PER_TASK,
    RESP_LATENCY,
)

# "Higher is better" direction per response — used by the Pareto sorter, which
# assumes maximisation (cost/latency are negated before ranking).
RESPONSE_MAXIMIZE = {
    RESP_REQUIREMENT_COVERAGE: True,
    RESP_CODE_QUALITY: True,
    RESP_COST_PER_TASK: False,
    RESP_LATENCY: False,
}

__all__ = [
    "__version__",
    "RESP_REQUIREMENT_COVERAGE",
    "RESP_CODE_QUALITY",
    "RESP_COST_PER_TASK",
    "RESP_LATENCY",
    "DEFAULT_RESPONSES",
    "RESPONSE_MAXIMIZE",
]
