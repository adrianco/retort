"""Compute promotion-gate evidence from measured runs.

`retort promote` evaluates a gate against three keys — `p_value`,
`posterior_confidence` and `dominated_confidence` — and until now NOTHING in the
codebase produced any of them. They had to be worked out by hand and passed as a
JSON string, so the `trial_to_production` gate every workspace.yaml carries by
default (`posterior_confidence: 0.80`) reported "missing from evidence" for
every stack, forever. A gate nothing can satisfy is not a gate.

The two Bayesian keys are computed here from `master.db`:

* ``posterior_confidence`` — P(this stack's true pass-proportion ≥ the gate's
  threshold), from a Normal-Inverse-Gamma posterior fitted to its per-run
  outcomes. NOT the observed mean: with n=1–3 replicates, which is retort's
  normal regime, the observed mean is a point estimate that a single lucky run
  can carry.

* ``dominated_confidence`` — P(this stack is Pareto-non-dominated) across
  quality, cost and speed, from `prob_pareto_non_dominated`. The name in
  `gates.py` matches that function's return value exactly; it was written as
  this gate's evidence source and never connected.

`p_value` is deliberately NOT computed here. It belongs to the ANOVA in
`retort analyze`, which needs the full design matrix rather than one stack's
rows, and inventing a second p-value from a different model would be worse than
having none.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from retort.analysis.bayesian import NormalInverseGamma
from retort.analysis.pareto import prob_pareto_non_dominated

#: Objectives for the Pareto question, and whether more is better.
#: Cost and duration are MINIMISED, so their samples are negated.
PARETO_METRICS: dict[str, bool] = {
    "requirement_coverage": True,
    "cost_usd": False,
    "duration_seconds": False,
}


def _stack_rows(db: Path, stack_id: str,
                task: str | None = None) -> dict[str, dict[str, list[float]]]:
    """Per-metric observation lists for every stack, keyed by stack label.

    `stack_id` selects the stack under test; the others are still needed,
    because "is it non-dominated" is only answerable against the field.
    """
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cols = {r[1] for r in con.execute("PRAGMA table_info(runs)")}
    label = "model" if "model" in cols else "stack"
    metrics = [m for m in PARETO_METRICS if m in cols]
    if not metrics:
        con.close()
        return {}
    where = f"{label} IS NOT NULL"
    params: list = []
    if task:
        where += " AND task LIKE ?"
        params.append(f"%{task}%")
    rows = con.execute(
        f"SELECT {label} AS label, {', '.join(metrics)} FROM runs WHERE {where}",
        params,
    ).fetchall()
    con.close()

    out: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        bucket = out.setdefault(r["label"], {m: [] for m in metrics})
        for m in metrics:
            v = r[m]
            if v is not None:
                bucket[m].append(float(v) if PARETO_METRICS[m] else -float(v))
    return out


def compute_evidence(db: Path, stack_id: str, *,
                     pass_threshold: float = 1.0,
                     task: str | None = None) -> dict[str, float]:
    """Evidence for `stack_id`, or {} when the database cannot support it.

    Returns only keys it can genuinely compute. A missing key makes the gate
    report "missing from evidence", which is the honest outcome — better than a
    number invented from too little data.

    `task` filters the runs used. WITHOUT it, evidence pools every task, which
    mixes the routine and hard tasks into one number: a stack at 1.00 on
    bookshop and 0.33 on brazil looks like 0.67 overall and promotes on the
    strength of the easy half. Pass the task when the promotion decision is
    about a specific one. `n_runs` is always returned so the caller can see how
    much data the number rests on.
    """
    if not Path(db).exists():
        return {}
    by_stack = _stack_rows(Path(db), stack_id, task)
    if stack_id not in by_stack:
        return {}

    evidence: dict[str, float] = {
        "n_runs": float(len(by_stack[stack_id].get("requirement_coverage") or []))
    }

    # posterior_confidence — P(true pass-proportion >= threshold)
    outcomes = by_stack[stack_id].get("requirement_coverage") or []
    if len(outcomes) >= 2:
        passes = [1.0 if v >= pass_threshold else 0.0 for v in outcomes]
        posterior = NormalInverseGamma().update(passes)
        # P(true pass-proportion > 0.5): "more likely than not to pass", with the
        # uncertainty of a small n folded in. 3/3 gives high confidence; 2/3 much
        # less, which is the whole point — the observed MEAN of 2/3 is 0.67 either
        # way and cannot distinguish a good stack from a lucky one.
        evidence["posterior_confidence"] = float(posterior.prob_greater_than(0.5))

    # dominated_confidence — P(non-dominated) across the objectives
    usable = {
        label: {m: NormalInverseGamma().update(vals)
                for m, vals in metrics.items() if len(vals) >= 2}
        for label, metrics in by_stack.items()
    }
    common = [m for m in PARETO_METRICS
              if all(m in v for v in usable.values() if v)]
    usable = {k: v for k, v in usable.items() if v and all(m in v for m in common)}
    if stack_id in usable and len(usable) >= 2 and common:
        probs = prob_pareto_non_dominated(usable, common, n_samples=4000)
        evidence["dominated_confidence"] = float(probs.get(stack_id, 0.0))

    return evidence
