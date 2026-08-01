#!/usr/bin/env python3
"""Measure produced-program runtime across an experiment's archived runs.

    python scripts/runtime_report.py <experiment-dir> [--task brazil-soccer-mcp]

Prints a per-language table of cold start and steady-state median latency for
the SAME probe (see scorers/runtime.py) — not the model's own test suite, whose
duration mostly reflects how many tests it chose to write.

Refuses to run while an experiment is live: this measures wall clock, so a busy
machine yields plausible, wrong, publishable numbers.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from retort.scoring.scorers import runtime as rt  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment_dir", type=Path)
    ap.add_argument("--task", default="brazil-soccer-mcp")
    ap.add_argument("--json", type=Path, help="also write raw results here")
    args = ap.parse_args()

    if rt._machine_is_busy():
        print("REFUSED: a `retort run` is active — wall-clock timing would be "
              "invalid. Wait for it to finish.", file=sys.stderr)
        return 2

    runs = sorted((args.experiment_dir / "runs").glob("*/rep*"))
    if not runs:
        print(f"no archived runs under {args.experiment_dir}/runs", file=sys.stderr)
        return 1

    results = []
    for rd in runs:
        lang = next((p.split("=")[1] for p in rd.parent.name.split("_")
                     if p.startswith("language=")), "?")
        res = rt.measure(rd, args.task, lang)
        results.append(res)
        print(f"  measured {lang:11s} "
              f"{'ok' if res.ok else 'NO RESULT: ' + res.note}", file=sys.stderr)

    ok = [r for r in results if r.ok]
    print(f"\n## Produced-program runtime — {args.task}")
    print(f"Probe: identical call, {rt.WARMUP_ITERS} warm-up + "
          f"{rt.TIMED_ITERS} timed iterations, median reported.\n")
    print(f"| language | cold start | steady median | min | max | n |")
    print(f"|---|---:|---:|---:|---:|---:|")
    for r in sorted(ok, key=lambda x: x.steady_median_ms or 9e9):
        print(f"| {r.language} | {r.cold_start_ms:.0f} ms | "
              f"**{r.steady_median_ms:.0f} ms** | {r.steady_min_ms:.0f} | "
              f"{r.steady_max_ms:.0f} | {r.iters} |")
    for r in results:
        if not r.ok:
            print(f"| {r.language} | — | *{r.note}* | | | |")

    if ok:
        fastest, slowest = ok[0], ok[-1]
        fastest = min(ok, key=lambda x: x.steady_median_ms)
        slowest = max(ok, key=lambda x: x.steady_median_ms)
        print(f"\nSpread: **{slowest.steady_median_ms / fastest.steady_median_ms:.1f}x** "
              f"({fastest.language} {fastest.steady_median_ms:.0f} ms → "
              f"{slowest.language} {slowest.steady_median_ms:.0f} ms), "
              f"{len(ok)}/{len(results)} languages measured.")

    if args.json:
        args.json.write_text(json.dumps([r.as_dict() for r in results], indent=1))
        print(f"\nraw → {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
