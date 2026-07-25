#!/usr/bin/env python3
"""exp-49 summary: the version x thinking-level grid.

Reads a run DB (cloud or local half) and prints the tables the write-up needs:
  1. version x effort grid for turns / tokens / cost / seconds / pass
  2. the effort main effect, averaged over versions
  3. the version main effect at DEFAULT effort only -- the in-batch replacement
     for versions-blog's cross-batch table
  4. a like-for-like check against the historical (cross-batch) numbers

Usage:  python summarize.py [path/to/retort.db]
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

EFFORT_ORDER = {"default": 0, "low": 1, "medium": 2, "high": 3, "max": 4}
MODEL_ORDER = {
    "claude-opus-4-7": 0,
    "claude-opus-4-8": 1,
    "claude-opus-4-8-fast": 2,
    "claude-fable-5": 3,
    "claude-opus-5": 4,
}
# versions-blog's published figures, all from OTHER experiments (exp-6/7/10/46).
# Kept here to make the cross-batch drift visible rather than assumed.
HISTORICAL_DEFAULT_TURNS = {
    "claude-opus-4-7": 17.2,
    "claude-opus-4-8": 17.3,
    "claude-opus-4-8-fast": 11.3,
    "claude-fable-5": 10.7,
    "claude-opus-5": 36.0,
}

METRICS = ("_turns", "_tokens", "_cost_usd", "_duration_seconds")


def load(db: Path) -> list[dict]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    out = []
    for r in conn.execute("select id, status, run_config_json from experiment_runs"):
        cfg = json.loads(r["run_config_json"] or "{}")
        f = cfg.get("factors", cfg)
        m = {
            x["metric_name"]: x["value"]
            for x in conn.execute(
                "select metric_name, value from run_results where run_id=?", (r["id"],)
            )
        }
        if "_turns" not in m:
            continue  # not finished, or a crash with no telemetry
        out.append(
            {
                "model": f.get("model", "?"),
                "effort": f.get("effort", "default"),
                "status": r["status"],
                "pass": 1.0 if (m.get("requirement_coverage") or 0) >= 1.0 else 0.0,
                **{k: m.get(k, 0.0) for k in METRICS},
            }
        )
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def grid(rows, metric, fmt="{:.1f}"):
    models = sorted({r["model"] for r in rows}, key=lambda m: MODEL_ORDER.get(m, 9))
    efforts = sorted({r["effort"] for r in rows}, key=lambda e: EFFORT_ORDER.get(e, 9))
    print(f"\n### {metric}")
    print(f"  {'model':<24}" + "".join(f"{e:>10}" for e in efforts) + f"{'n':>5}")
    for mdl in models:
        cells = []
        n = 0
        for e in efforts:
            sel = [r[metric] for r in rows if r["model"] == mdl and r["effort"] == e]
            n += len(sel)
            cells.append(fmt.format(mean(sel)) if sel else "—")
        print(f"  {mdl:<24}" + "".join(f"{c:>10}" for c in cells) + f"{n:>5}")


def main() -> None:
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "cloud/retort.db"
    )
    rows = load(db)
    if not rows:
        print(f"no completed runs with telemetry in {db}")
        return
    print(f"exp-49 — {len(rows)} runs with telemetry from {db}")

    grid(rows, "_turns")
    grid(rows, "_tokens", "{:,.0f}")
    grid(rows, "_cost_usd", "${:.2f}")
    grid(rows, "_duration_seconds", "{:.0f}s")
    grid(rows, "pass", "{:.2f}")

    print("\n### effort main effect (averaged over versions)")
    print(f"  {'effort':<10}{'turns':>8}{'tokens':>12}{'cost':>9}{'sec':>7}{'pass':>7}{'n':>5}")
    for e in sorted({r["effort"] for r in rows}, key=lambda x: EFFORT_ORDER.get(x, 9)):
        sel = [r for r in rows if r["effort"] == e]
        print(
            f"  {e:<10}{mean([r['_turns'] for r in sel]):>8.1f}"
            f"{mean([r['_tokens'] for r in sel]):>12,.0f}"
            f"{mean([r['_cost_usd'] for r in sel]):>9.2f}"
            f"{mean([r['_duration_seconds'] for r in sel]):>7.0f}"
            f"{mean([r['pass'] for r in sel]):>7.2f}{len(sel):>5}"
        )

    print("\n### version effect AT DEFAULT EFFORT — the in-batch control")
    print("    (compare `turns` against `hist`, which is versions-blog's cross-batch figure)")
    print(f"  {'model':<24}{'turns':>8}{'hist':>8}{'drift':>9}{'n':>5}")
    for mdl in sorted({r["model"] for r in rows}, key=lambda m: MODEL_ORDER.get(m, 9)):
        sel = [r for r in rows if r["model"] == mdl and r["effort"] == "default"]
        if not sel:
            continue
        t = mean([r["_turns"] for r in sel])
        h = HISTORICAL_DEFAULT_TURNS.get(mdl)
        drift = f"{t / h:.2f}x" if h else "—"
        print(f"  {mdl:<24}{t:>8.1f}{(h if h else float('nan')):>8.1f}{drift:>9}{len(sel):>5}")
    print(
        "\n  A drift far from 1.00x means the historical number and this one were not\n"
        "  measuring the same thing — different harness era, not a different model."
    )


if __name__ == "__main__":
    main()
