"""Stack maturity scoring.

A *stack* in retort is a unique combination of factor levels (e.g.
``language=rust, model=opus, tooling=beads``). Replicates measure noise
within a stack; multiple stacks measure the design space.

Maturity is a composite ∈ [0, 1] that combines four signals visible in
the run database:

  - **Replicate agreement** — how much do scores vary across replicates
    of the same stack? Low variance = the stack is reproducible.
  - **Completion rate** — fraction of attempted runs that completed
    successfully. Stacks that frequently fail are immature.
  - **Score level** — the mean of the headline metric (default
    ``code_quality``). High scores indicate the stack consistently
    produces good output.
  - **Coverage of replicates** — does the stack have enough replicates
    to trust its variance estimate? n ≥ 3 → 1.0, scales down toward 0.

These signals are deliberately derivable from the existing run database
(no extra evaluation needed). Future work can enrich with
``findings.jsonl`` data once auto-evaluation has run on a corpus.

The maturity score is intended as input to the existing
``promotion/lifecycle.py`` gates — wire it in via a ``maturity_score``
threshold in ``workspace.yaml`` once the corpus exists to validate
threshold values.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Iterable

from retort.storage.models import ExperimentRun, RunResult, RunStatus


# Default headline metric — what we use when callers don't pick one.
_DEFAULT_HEADLINE_METRIC = "code_quality"

# Replicate-coverage saturation point: a stack with at least this many
# completed replicates gets full credit on the coverage component.
_REPLICATE_SATURATION = 3


@dataclass(frozen=True)
class StackMaturity:
    """Maturity assessment for one stack (factor-level combination)."""

    stack_signature: str
    factors: dict[str, str]
    n_replicates: int
    n_completed: int
    n_failed: int
    headline_metric: str
    headline_mean: float | None
    headline_stdev: float | None
    headline_cv: float | None  # coefficient of variation
    completion_rate: float
    replicate_agreement: float
    score_level: float
    coverage: float
    maturity: float
    components: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stack_signature": self.stack_signature,
            "factors": self.factors,
            "n_replicates": self.n_replicates,
            "n_completed": self.n_completed,
            "n_failed": self.n_failed,
            "headline_metric": self.headline_metric,
            "headline_mean": self.headline_mean,
            "headline_stdev": self.headline_stdev,
            "headline_cv": self.headline_cv,
            "completion_rate": self.completion_rate,
            "replicate_agreement": self.replicate_agreement,
            "score_level": self.score_level,
            "coverage": self.coverage,
            "maturity": self.maturity,
            "components": self.components,
        }


def compute_stack_maturity(
    session,
    *,
    headline_metric: str = _DEFAULT_HEADLINE_METRIC,
    weights: dict[str, float] | None = None,
) -> list[StackMaturity]:
    """Compute maturity for every distinct stack in the run database.

    Args:
        session: An open SQLAlchemy session bound to a retort.db engine.
        headline_metric: The metric whose level/variance dominates the
            score-based components. Defaults to ``code_quality``.
        weights: Optional override for the four-component weighting.
            Keys: ``replicate_agreement``, ``completion_rate``,
            ``score_level``, ``coverage``. Values are normalized so they
            need not sum to 1.

    Returns:
        A list of StackMaturity objects, sorted by descending maturity.
    """
    weights = _normalize_weights(weights)

    # Group runs by their stable stack signature (sorted-json of run_config).
    runs_by_stack: dict[str, list[ExperimentRun]] = {}
    for run in session.query(ExperimentRun).all():
        sig = _signature(run.run_config_json)
        if sig is None:
            continue
        runs_by_stack.setdefault(sig, []).append(run)

    if not runs_by_stack:
        return []

    # Pre-load all results to avoid N+1.
    results_by_run: dict[int, list[RunResult]] = {}
    for r in session.query(RunResult).all():
        results_by_run.setdefault(r.run_id, []).append(r)

    out: list[StackMaturity] = []
    for sig, runs in runs_by_stack.items():
        out.append(_score_stack(
            sig, runs, results_by_run, headline_metric, weights,
        ))

    out.sort(key=lambda s: s.maturity, reverse=True)
    return out


def _signature(run_config_json: str | None) -> str | None:
    if not run_config_json:
        return None
    try:
        data = json.loads(run_config_json)
    except (TypeError, ValueError):
        return None
    return json.dumps(data, sort_keys=True)


def _normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    default = {
        "replicate_agreement": 0.30,
        "completion_rate": 0.30,
        "score_level": 0.25,
        "coverage": 0.15,
    }
    if weights:
        merged = {k: weights.get(k, v) for k, v in default.items()}
    else:
        merged = default
    total = sum(merged.values())
    if total <= 0:
        return default
    return {k: v / total for k, v in merged.items()}


def _score_stack(
    sig: str,
    runs: list[ExperimentRun],
    results_by_run: dict[int, list[RunResult]],
    headline_metric: str,
    weights: dict[str, float],
) -> StackMaturity:
    n_replicates = len(runs)
    n_completed = sum(1 for r in runs if r.status == RunStatus.completed)
    n_failed = sum(1 for r in runs if r.status == RunStatus.failed)

    # Pull headline metric values from completed runs only.
    headline_values: list[float] = []
    for run in runs:
        if run.status != RunStatus.completed:
            continue
        for res in results_by_run.get(run.id, []):
            if res.metric_name == headline_metric and res.value is not None:
                headline_values.append(float(res.value))
                break

    headline_mean = mean(headline_values) if headline_values else None
    headline_stdev = stdev(headline_values) if len(headline_values) > 1 else None
    headline_cv = (
        headline_stdev / headline_mean
        if headline_mean and headline_mean > 0 and headline_stdev is not None
        else None
    )

    # Component scores in [0, 1].
    completion_rate = n_completed / n_replicates if n_replicates else 0.0

    if headline_cv is None:
        # Single replicate or no scores — neutral, can't measure agreement.
        replicate_agreement = 0.5
    else:
        # CV of 0 → 1.0; CV of 0.3 or worse → 0.0. Linear in between.
        replicate_agreement = max(0.0, min(1.0, 1.0 - headline_cv / 0.30))

    if headline_mean is None:
        score_level = 0.0
    else:
        # Headline metric is already in [0, 1] convention for retort scorers.
        score_level = max(0.0, min(1.0, headline_mean))

    coverage = min(1.0, n_completed / _REPLICATE_SATURATION)

    components = {
        "replicate_agreement": replicate_agreement,
        "completion_rate": completion_rate,
        "score_level": score_level,
        "coverage": coverage,
    }
    maturity = sum(weights[k] * components[k] for k in weights)

    factors = _factors_from_signature(sig)

    return StackMaturity(
        stack_signature=sig,
        factors=factors,
        n_replicates=n_replicates,
        n_completed=n_completed,
        n_failed=n_failed,
        headline_metric=headline_metric,
        headline_mean=headline_mean,
        headline_stdev=headline_stdev,
        headline_cv=headline_cv,
        completion_rate=completion_rate,
        replicate_agreement=replicate_agreement,
        score_level=score_level,
        coverage=coverage,
        maturity=maturity,
        components=components,
    )


def _factors_from_signature(sig: str) -> dict[str, str]:
    try:
        data = json.loads(sig)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except (TypeError, ValueError):
        pass
    return {}


def classify_phase(maturity: float) -> str:
    """Suggest a lifecycle phase given a maturity score.

    These thresholds are *defaults* — the actual promotion is gated by
    ``promotion/gates.py`` which reads thresholds from workspace.yaml.
    The mapping here is for human-readable summaries only.
    """
    if maturity >= 0.85:
        return "production"
    if maturity >= 0.65:
        return "trial"
    if maturity >= 0.40:
        return "screening"
    return "candidate"


def render_text(report: Iterable[StackMaturity]) -> str:
    """Render a table of stack maturity scores for terminal output."""
    rows = list(report)
    if not rows:
        return "No stacks found in the database.\n"

    lines: list[str] = []
    lines.append(
        f"{'Maturity':>9}  {'Phase':>10}  {'Stack'}"
    )
    lines.append("-" * 80)
    for r in rows:
        factors_str = ", ".join(f"{k}={v}" for k, v in r.factors.items())
        lines.append(
            f"{r.maturity:>9.3f}  {classify_phase(r.maturity):>10}  {factors_str}"
        )
        lines.append(
            f"{'':>9}  {'':>10}  "
            f"n={r.n_replicates} (✓{r.n_completed}/✗{r.n_failed})  "
            f"{r.headline_metric}: "
            + (f"{r.headline_mean:.3f}±{r.headline_stdev:.3f}" if r.headline_stdev is not None else
               f"{r.headline_mean:.3f}" if r.headline_mean is not None else "n/a")
            + f"  agreement={r.replicate_agreement:.2f}"
            + f"  completion={r.completion_rate:.2f}"
            + f"  coverage={r.coverage:.2f}"
        )
    return "\n".join(lines) + "\n"


def render_json(report: Iterable[StackMaturity]) -> str:
    return json.dumps([r.to_dict() for r in report], indent=2)
