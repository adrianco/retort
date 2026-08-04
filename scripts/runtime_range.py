#!/usr/bin/env python3
"""Per-language runtime RANGE across every archived brazil run, with attribution.

A single measurement per language conflates the language with the one
implementation that happened to be measured — and this corpus has already shown
implementations of the same task differing by 100x on per-request latency and by
40% on how much data they even load. So measure every run and report the SPREAD,
naming the model that produced the fastest and the slowest.

The spread is the finding. A language whose best and worst runs are 5x apart is
telling you the model mattered more than the language did.

Usage:  python scripts/runtime_range.py <experiment-dir> [more...]
        (writes docs/runtime-range.json)
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retort.scoring.scorers import runtime as rt  # noqa: E402


def factors(run_dir: Path) -> dict:
    return dict(x.split("=", 1) for x in run_dir.parent.name.split("_") if "=" in x)


def main() -> int:
    if rt._machine_is_busy():
        print("REFUSED: an experiment is running — wall-clock timing would be "
              "invalid.", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for exp in sys.argv[1:]:
        for rd in sorted(p for p in (Path(exp) / "runs").glob("*/rep*")
                         if p.is_dir() and not p.name.endswith("-failed")):
            f = factors(rd)
            lang = f.get("language", "?")
            r = rt.measure(rd, "brazil-soccer-mcp", lang, allow_busy=True)
            rows.append({
                "language": lang,
                "model": f.get("model", "?"),
                "effort": f.get("effort", ""),
                "experiment": Path(exp).parent.name,
                "ok": r.ok,
                "cold_ms": r.cold_start_ms,
                "request_ms": r.request_median_ms,
                "tools": r.tool_count,
                "rows_loaded": r.rows_loaded,
                "note": r.note,
            })
            print(f"  {lang:11s} {f.get('model','?'):16s} "
                  f"{('%.0f ms' % r.cold_start_ms) if r.ok else 'NO: ' + r.note[:45]}",
                  file=sys.stderr)

    Path("docs/runtime-range.json").write_text(json.dumps(rows, indent=1))

    ok = [r for r in rows if r["ok"]]
    by: dict[str, list[dict]] = {}
    for r in ok:
        by.setdefault(r["language"], []).append(r)

    print("\n## Cold start per language — range across implementations\n")
    print("| language | n | fastest | by | slowest | by | spread |")
    print("|---|---:|---:|---|---:|---|---:|")
    for lang in sorted(by, key=lambda L: min(x["cold_ms"] for x in by[L])):
        g = by[lang]
        f_, s_ = min(g, key=lambda x: x["cold_ms"]), max(g, key=lambda x: x["cold_ms"])
        spread = s_["cold_ms"] / f_["cold_ms"]
        print(f"| **{lang}** | {len(g)} | {f_['cold_ms']:.0f} ms | {f_['model']}"
              f"{('@' + f_['effort']) if f_['effort'] else ''} | {s_['cold_ms']:.0f} ms | "
              f"{s_['model']}{('@' + s_['effort']) if s_['effort'] else ''} | "
              f"{spread:.1f}x |")

    print("\n## Per-request latency — same runs\n")
    print("| language | n | fastest | slowest | spread |")
    print("|---|---:|---:|---:|---:|")
    for lang in sorted(by):
        g = [x for x in by[lang] if x["request_ms"] is not None]
        if not g:
            continue
        f_, s_ = min(g, key=lambda x: x["request_ms"]), max(g, key=lambda x: x["request_ms"])
        sp = s_["request_ms"] / f_["request_ms"] if f_["request_ms"] else float("inf")
        print(f"| **{lang}** | {len(g)} | {f_['request_ms']:.3f} ms | "
              f"{s_['request_ms']:.3f} ms | {sp:.1f}x |")

    langs_multi = [L for L in by if len(by[L]) > 1]
    if langs_multi:
        spreads = [max(x["cold_ms"] for x in by[L]) / min(x["cold_ms"] for x in by[L])
                   for L in langs_multi]
        print(f"\n**Median within-language spread: {statistics.median(spreads):.1f}x** "
              f"across {len(langs_multi)} languages with more than one measured run — "
              f"how much the *implementation* moves the number with the language held "
              f"fixed.")
    bad = [r for r in rows if not r["ok"]]
    if bad:
        print(f"\n{len(bad)}/{len(rows)} runs not measured:")
        seen = set()
        for r in bad:
            k = (r["language"], r["note"][:40])
            if k in seen:
                continue
            seen.add(k)
            print(f"  - {r['language']}: {r['note'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
