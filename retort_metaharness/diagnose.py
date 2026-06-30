"""Failure diagnosis — TOOLING_FALSE_FAIL vs GENUINE_MODEL_FAIL.

The invariant (from our own harness work): a failed cell that cost ~$0 and
returned ~instantly never actually engaged the model — it's a harness/tooling
bug (crash, unsupported language, empty output, provisioning error), not a model
failure. Counting those as model failures is the single biggest source of
under-scoring in custom agentic harnesses.

This module classifies every cell so the ANOVA attribution runs on *genuine*
outcomes only. It is a pure function over (status, cost, latency, tokens).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Verdict(str, Enum):
    PASS = "PASS"
    GENUINE_MODEL_FAIL = "GENUINE_MODEL_FAIL"
    TOOLING_FALSE_FAIL = "TOOLING_FALSE_FAIL"


@dataclass(frozen=True)
class DiagnosisThresholds:
    """Below *both* cost and latency thresholds, a failure is tooling, not model.

    A failure with zero tokens is always tooling (the model was never called).
    """

    min_cost_usd: float = 0.0005   # < 0.05 cent = effectively free
    min_latency_s: float = 0.5     # < 0.5 s = no real model round-trip
    require_tokens: bool = True    # zero-token failures are always tooling


def classify_row(
    *,
    status: str,
    cost_usd: float,
    latency_s: float,
    tokens: int,
    thr: DiagnosisThresholds | None = None,
) -> Verdict:
    """Classify a single cell outcome."""
    thr = thr or DiagnosisThresholds()
    if str(status).lower() == "pass":
        return Verdict.PASS
    # It's a failure — was the model actually engaged?
    if thr.require_tokens and tokens <= 0:
        return Verdict.TOOLING_FALSE_FAIL
    if cost_usd < thr.min_cost_usd and latency_s < thr.min_latency_s:
        return Verdict.TOOLING_FALSE_FAIL
    return Verdict.GENUINE_MODEL_FAIL


def diagnose_frame(
    df: pd.DataFrame,
    *,
    thr: DiagnosisThresholds | None = None,
    status_col: str = "status",
    cost_col: str = "cost_per_task",
    latency_col: str = "latency_s",
    tokens_col: str = "tokens",
) -> pd.DataFrame:
    """Add a ``verdict`` column to a results frame."""
    thr = thr or DiagnosisThresholds()
    out = df.copy()
    out["verdict"] = [
        classify_row(
            status=row[status_col],
            cost_usd=float(row.get(cost_col, 0.0)),
            latency_s=float(row.get(latency_col, 0.0)),
            tokens=int(row.get(tokens_col, 0)),
            thr=thr,
        ).value
        for _, row in out.iterrows()
    ]
    return out


def drop_tooling_fails(df: pd.DataFrame, **kw) -> pd.DataFrame:
    """Return only PASS + GENUINE_MODEL_FAIL cells (drop tooling false-fails).

    This is the correct pre-ANOVA filter: attribute variance over outcomes where
    the model was genuinely engaged.
    """
    diagnosed = diagnose_frame(df, **kw) if "verdict" not in df.columns else df
    return diagnosed[diagnosed["verdict"] != Verdict.TOOLING_FALSE_FAIL.value].copy()


def summarize(df: pd.DataFrame, **kw) -> dict[str, object]:
    """Counts + per-class breakdown for a results frame."""
    d = diagnose_frame(df, **kw) if "verdict" not in df.columns else df
    counts = d["verdict"].value_counts().to_dict()
    total = int(len(d))
    n_tool = int(counts.get(Verdict.TOOLING_FALSE_FAIL.value, 0))
    n_fail = int(counts.get(Verdict.GENUINE_MODEL_FAIL.value, 0))
    n_pass = int(counts.get(Verdict.PASS.value, 0))
    return {
        "total": total,
        "pass": n_pass,
        "genuine_model_fail": n_fail,
        "tooling_false_fail": n_tool,
        "tooling_false_fail_rate": round(n_tool / total, 4) if total else 0.0,
        "true_failure_rate": round(n_fail / (n_pass + n_fail), 4)
        if (n_pass + n_fail)
        else 0.0,
    }


def render_text(df: pd.DataFrame, **kw) -> str:
    """Human-readable diagnosis report."""
    d = diagnose_frame(df, **kw) if "verdict" not in df.columns else df
    s = summarize(d)
    lines: list[str] = ["Failure diagnosis", "=" * 40]
    lines.append(
        f"cells={s['total']}  pass={s['pass']}  "
        f"genuine_model_fail={s['genuine_model_fail']}  "
        f"tooling_false_fail={s['tooling_false_fail']}"
    )
    lines.append(
        f"tooling_false_fail_rate={s['tooling_false_fail_rate']:.1%}  "
        f"true_failure_rate (model-fail / engaged)={s['true_failure_rate']:.1%}"
    )
    tool = d[d["verdict"] == Verdict.TOOLING_FALSE_FAIL.value]
    if not tool.empty:
        lines.append("\nTOOLING_FALSE_FAIL cells (excluded from ANOVA):")
        for _, r in tool.iterrows():
            note = str(r.get("notes", ""))[:70]
            lines.append(
                f"  ⚠ {r.get('cell_id','?')} r{r.get('replicate',0)} "
                f"[{r.get('model','?')}/{r.get('harness_config','?')}/"
                f"{r.get('scaffold','?')}/{r.get('language','?')}] "
                f"${float(r.get('cost_per_task',0)):.4f} "
                f"{float(r.get('latency_s',0)):.3f}s — {note}"
            )
    return "\n".join(lines) + "\n"
