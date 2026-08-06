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
                "first_query_ms": r.first_query_ms,
                "first_query_tool": r.first_query_tool,
                "total_to_answer_ms": (
                    (r.cold_start_ms + r.first_query_ms)
                    if (r.cold_start_ms is not None and r.first_query_ms is not None)
                    else None),
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

    print("\n## Time to FIRST REAL ANSWER — cold start + first tools/call\n")
    print("Cold start alone is not comparable: an implementation that loads the")
    print("data lazily answers `tools/list` having done none of the work. This")
    print("column moves the finish line to the same place for every run.\n")
    print("| language | n | fastest | by | slowest | by | spread |")
    print("|---|---:|---:|---|---:|---|---:|")
    tot = {L: [x for x in g if x.get("total_to_answer_ms")] for L, g in by.items()}
    for lang in sorted((L for L in tot if tot[L]),
                       key=lambda L: min(x["total_to_answer_ms"] for x in tot[L])):
        g = tot[lang]
        f_ = min(g, key=lambda x: x["total_to_answer_ms"])
        s_ = max(g, key=lambda x: x["total_to_answer_ms"])
        sp = s_["total_to_answer_ms"] / f_["total_to_answer_ms"]
        print(f"| **{lang}** | {len(g)} | {f_['total_to_answer_ms']:.0f} ms | "
              f"{f_['model']}{('@' + f_['effort']) if f_['effort'] else ''} | "
              f"{s_['total_to_answer_ms']:.0f} ms | "
              f"{s_['model']}{('@' + s_['effort']) if s_['effort'] else ''} | {sp:.1f}x |")

    print("\n## Per-request latency — the SAME runs, already warm\n")
    print("Reported alongside start-up, not as a footnote. The absolute numbers")
    print("are ~1000x smaller, but the SPREAD between implementations is not:")
    print("this is per-call work with the data already in memory, so a large")
    print("spread here is structural — re-parsing per request, a linear scan")
    print("where another run built an index — and it is paid on EVERY call,")
    print("whereas start-up is paid once.\n")
    print("| language | n | fastest | by | slowest | by | spread |")
    print("|---|---:|---:|---|---:|---|---:|")
    req = {L: [x for x in g if x.get("request_ms") is not None] for L, g in by.items()}
    for lang in sorted((L for L in req if req[L]),
                       key=lambda L: min(x["request_ms"] for x in req[L])):
        g = req[lang]
        f_ = min(g, key=lambda x: x["request_ms"])
        s_ = max(g, key=lambda x: x["request_ms"])
        sp = (s_["request_ms"] / f_["request_ms"]) if f_["request_ms"] else float("inf")
        print(f"| **{lang}** | {len(g)} | {f_['request_ms']:.3f} ms | "
              f"{f_['model']}{('@' + f_['effort']) if f_['effort'] else ''} | "
              f"{s_['request_ms']:.3f} ms | "
              f"{s_['model']}{('@' + s_['effort']) if s_['effort'] else ''} | {sp:.1f}x |")

    allreq = [x for g in req.values() for x in g]
    if allreq:
        fastest = min(allreq, key=lambda x: x["request_ms"])
        slowest = max(allreq, key=lambda x: x["request_ms"])
        print(f"\n**Across the whole corpus: {fastest['request_ms']:.3f} ms "
              f"({fastest['language']}) to {slowest['request_ms']:.3f} ms "
              f"({slowest['language']}) — "
              f"{slowest['request_ms'] / fastest['request_ms']:.0f}x.** Start-up "
              f"is amortised; this is not.")

    print("\n## All three phases together\n")
    print("| language | n | cold start | + first query | = first answer | per-request |")
    print("|---|---:|---:|---:|---:|---:|")
    for lang in sorted(by, key=lambda L: statistics.median(
            [x["cold_ms"] for x in by[L]])):
        g = by[lang]
        med = lambda k: statistics.median([x[k] for x in g if x.get(k) is not None]) \
            if any(x.get(k) is not None for x in g) else None
        cold, fq, tot, rq = med("cold_ms"), med("first_query_ms"), \
            med("total_to_answer_ms"), med("request_ms")
        fmt = lambda v, d=0: f"{v:,.{d}f} ms" if v is not None else "—"
        print(f"| **{lang}** | {len(g)} | {fmt(cold)} | {fmt(fq)} | {fmt(tot)} "
              f"| {fmt(rq, 3)} |")

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
