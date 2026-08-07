#!/usr/bin/env python3
"""Regenerate every runtime table and figure in tasks-blog.md from the data.

These are wall-clock measurements, so re-running the sweep moves them slightly —
the same 53 runs measured twice gave medians differing by a few percent, which
is enough to make a hand-copied table quietly disagree with the JSON it came
from. Every number in the runtime section is therefore generated here from
docs/runtime-range.json + docs/implementation-survey.json and written between
GEN markers, so the prose can never drift from the data again.

Usage:  python scripts/regen_runtime_tables.py [--check]
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

BLOG = Path("tasks-blog.md")


def load():
    rows = [r for r in json.loads(Path("docs/runtime-range.json").read_text()) if r["ok"]]
    surv = {(s["language"], s["model"], s.get("effort", "")): s
            for s in json.loads(Path("docs/implementation-survey.json").read_text())}
    return rows, surv


def tag(r: dict) -> str:
    m = r["model"].replace("claude-", "").replace("gpt-5.6-", "")
    return f"{m}{('@' + r['effort']) if r['effort'] else ''}"


def med(vals):
    v = [x for x in vals if x is not None]
    return statistics.median(v) if v else None


def build(rows, surv) -> dict[str, str]:
    by = defaultdict(list)
    for r in rows:
        by[r["language"]].append(r)
    out: dict[str, str] = {}

    # --- time to first answer -------------------------------------------------
    tot = {L: [x for x in g if x.get("total_to_answer_ms")] for L, g in by.items()}
    lines = ["| language | n | fastest | by | slowest | by | spread |",
             "|---|---:|---:|---|---:|---|---:|"]
    for L in sorted((L for L in tot if tot[L]),
                    key=lambda L: min(x["total_to_answer_ms"] for x in tot[L])):
        g = tot[L]
        f_ = min(g, key=lambda x: x["total_to_answer_ms"])
        s_ = max(g, key=lambda x: x["total_to_answer_ms"])
        if len(g) == 1:
            lines.append(f"| **{L}** | 1 | {f_['total_to_answer_ms']:,.0f} ms | {tag(f_)} | — | — | — |")
        else:
            lines.append(
                f"| **{L}** | {len(g)} | {f_['total_to_answer_ms']:,.0f} ms | {tag(f_)} "
                f"| {s_['total_to_answer_ms']:,.0f} ms | {tag(s_)} "
                f"| {s_['total_to_answer_ms'] / f_['total_to_answer_ms']:.1f}× |")
    out["first-answer-table"] = "\n".join(lines)

    allt = [x["total_to_answer_ms"] for g in tot.values() for x in g]
    spreads = [max(x["total_to_answer_ms"] for x in g) / min(x["total_to_answer_ms"] for x in g)
               for g in tot.values() if len(g) > 1]
    order = sorted((L for L in tot if tot[L]),
                   key=lambda L: min(x["total_to_answer_ms"] for x in tot[L]))
    exceed = 0
    for i, L in enumerate(order[:-1]):
        g = tot[L]
        if len(g) < 2:
            continue
        spread = max(x["total_to_answer_ms"] for x in g) / min(x["total_to_answer_ms"] for x in g)
        gap = min(x["total_to_answer_ms"] for x in tot[order[i + 1]]) / \
            min(x["total_to_answer_ms"] for x in g)
        if spread > gap:
            exceed += 1
    out["first-answer-summary"] = (
        f"Across the corpus, {min(allt):,.0f} ms to {max(allt):,.0f} ms. The "
        f"**median within-language spread is {statistics.median(spreads):.1f}×** — that is the "
        f"implementation moving the number with the language held fixed, and in "
        f"{exceed} of the {len(by)} it is larger than the gap to the next language along.")

    # --- the lazy/eager pair (start-up ranks them backwards) ------------------
    pair = {r["effort"]: r for r in rows
            if r["language"] == "python" and r["model"] == "claude-opus-5"
            and r["effort"] in ("high", "low")}
    if "high" in pair and "low" in pair:
        lz, eg = pair["high"], pair["low"]
        out["lazy-eager"] = (
            f"**Start-up alone would rank these wrongly**, so it is not the headline. "
            f"`tools/list` is protocol metadata: an implementation that parses all 42k rows at "
            f"import answers it having done the work, one that streams lazily answers having done "
            f"none. Two Python runs of the same model at different thinking levels make the point "
            f"— the lazy one (`yield from csv.DictReader(...)`) starts in {lz['cold_ms']:.0f} ms "
            f"and takes {lz['first_query_ms']:.0f} ms to answer a real question; the eager one "
            f"(`rows = list(csv.DictReader(...))`) starts in {eg['cold_ms']:,.0f} ms and answers "
            f"in {eg['first_query_ms']:.0f} ms. Measured to first answer they are "
            f"{eg['total_to_answer_ms'] / lz['total_to_answer_ms']:.1f}× apart; measured to "
            f"start-up, {eg['cold_ms'] / lz['cold_ms']:.0f}× apart *in the opposite order*.")
        out["lazy-eager-intro"] = (
            f"Every run in this section scored **12/12**. The checklist tests whether a capability "
            f"exists, not how it was built — so the design decisions behind these programs are "
            f"invisible in every number retort records. That is worth looking at directly, because "
            f"two runs of the same model at different thinking levels produced programs "
            f"{eg['cold_ms'] / lz['cold_ms']:.0f}× apart in start-up that disagreed about whether "
            f"the data needed deduplicating at all.")

    # --- per-request ----------------------------------------------------------
    req = {L: [x for x in g if x.get("request_ms") is not None] for L, g in by.items()}
    lines = ["| language | n | fastest | by | slowest | by | spread |",
             "|---|---:|---:|---|---:|---|---:|"]
    for L in sorted((L for L in req if req[L]),
                    key=lambda L: min(x["request_ms"] for x in req[L])):
        g = req[L]
        f_ = min(g, key=lambda x: x["request_ms"])
        s_ = max(g, key=lambda x: x["request_ms"])
        if len(g) == 1:
            lines.append(f"| **{L}** | 1 | {f_['request_ms']:.3f} ms | {tag(f_)} | — | — | — |")
        else:
            lines.append(
                f"| **{L}** | {len(g)} | {f_['request_ms']:.3f} ms | {tag(f_)} "
                f"| {s_['request_ms']:.3f} ms | {tag(s_)} "
                f"| {s_['request_ms'] / f_['request_ms']:.0f}× |")
    out["per-request-table"] = "\n".join(lines)

    alq = [x["request_ms"] for g in req.values() for x in g]
    cold = {L: med([x["cold_ms"] for x in g]) for L, g in by.items()}
    cold_range = max(cold.values()) / min(cold.values())
    n_exceed = sum(1 for L, g in req.items() if len(g) > 1
                   and max(x["request_ms"] for x in g) / min(x["request_ms"] for x in g) > cold_range)
    out["per-request-summary"] = (
        f"**Across the corpus: {min(alq):.3f} ms to {max(alq):.0f} ms — {max(alq) / min(alq):,.0f}×.** "
        f"The absolute numbers are three orders of magnitude below start-up and the spread is "
        f"far wider. {n_exceed} languages vary more between their own implementations here "
        f"than the entire language ranking varies at start-up ({cold_range:.0f}× from "
        f"{min(cold, key=cold.get)} to {max(cold, key=cold.get)}).")

    # --- model pattern --------------------------------------------------------
    fast = slow = 0
    multi = 0
    for L, g in req.items():
        if len(g) < 2:
            continue
        multi += 1
        if min(g, key=lambda x: x["request_ms"])["model"] == "claude-opus-5":
            fast += 1
        if max(g, key=lambda x: x["request_ms"])["model"] == "gpt-5.6-terra":
            slow += 1
    mm = {m: med([r["request_ms"] for r in rows if r["model"] == m and r.get("request_ms") is not None])
          for m in {r["model"] for r in rows}}
    cm = {m: med([r["cold_ms"] for r in rows if r["model"] == m]) for m in mm}
    out["model-pattern"] = (
        f"**And the pattern is not about languages.** Opus-5 produced the fastest per-request "
        f"implementation in {fast} of the {multi} languages with more than one run; Terra the "
        f"slowest in {slow}. By model median: opus **{mm['claude-opus-5']:.3f} ms**, fable "
        f"**{mm['claude-fable-5']:.3f} ms**, terra **{mm['gpt-5.6-terra']:.3f} ms** — a "
        f"{mm['gpt-5.6-terra'] / mm['claude-opus-5']:.0f}× gap between models whose *cold starts* "
        f"sit within {max(cm.values()) / min(cm.values()):.1f}× of each other "
        f"({min(cm.values()):.0f}–{max(cm.values()):.0f} ms). Two models write programs that boot "
        f"about the same and then answer queries a hundred times apart.")

    # --- indexing -------------------------------------------------------------
    ix = defaultdict(list)
    for r in rows:
        s = surv.get((r["language"], r["model"], r.get("effort", "")))
        if s:
            ix[s["indexing"]].append(r)
    lines = ["| indexing | n | per-request median | cold-start median |", "|---|---:|---:|---:|"]
    for key, label in (("precomputed-index", "precomputed index"), ("scan", "linear scan")):
        g = ix[key]
        lines.append(f"| {label} | {len(g)} | {med([x['request_ms'] for x in g]):.3f} ms "
                     f"| {med([x['cold_ms'] for x in g]):.0f} ms |")
    out["indexing-table"] = "\n".join(lines)
    ratio = med([x["request_ms"] for x in ix["scan"]]) / med([x["request_ms"] for x in ix["precomputed-index"]])
    out["indexing-ratio"] = (
        f"Indexing accounts for about {ratio:.1f}× of a "
        f"{mm['gpt-5.6-terra'] / mm['claude-opus-5']:.0f}× gap, so most of Terra's cost lies "
        f"elsewhere, with re-parsing per call the obvious candidate.")

    # --- design-choice table --------------------------------------------------
    g2 = defaultdict(list)
    for r in rows:
        s = surv.get((r["language"], r["model"], r.get("effort", "")))
        if not s:
            continue
        for axis in ("dedup", "indexing", "protocol"):
            g2[f"{axis}: {s[axis]}"].append(r)
    lines = ["| choice | n | median time to first answer | median per-request |",
             "|---|---:|---:|---:|"]
    for k in ("dedup: date-window", "dedup: key-set", "dedup: none",
              "indexing: precomputed-index", "indexing: scan",
              "protocol: sdk", "protocol: hand-rolled"):
        g = g2.get(k, [])
        if not g:
            continue
        label = k.replace("precomputed-index", "precomputed").replace("sdk", "SDK")
        lines.append(f"| {label} | {len(g)} | {med([x['total_to_answer_ms'] for x in g]):.0f} ms "
                     f"| {med([x['request_ms'] for x in g]):.3f} ms |")
    out["design-choice-table"] = "\n".join(lines)

    # --- three phases ---------------------------------------------------------
    lines = ["| language | n | cold start | + first query | = first answer | per-request |",
             "|---|---:|---:|---:|---:|---:|"]
    for L in sorted(by, key=lambda L: med([x["cold_ms"] for x in by[L]])):
        g = by[L]
        f = lambda v, d=0: f"{v:,.{d}f} ms" if v is not None else "—"
        lines.append(f"| **{L}** | {len(g)} | {f(med([x['cold_ms'] for x in g]))} "
                     f"| {f(med([x['first_query_ms'] for x in g]))} "
                     f"| {f(med([x['total_to_answer_ms'] for x in g]))} "
                     f"| {f(med([x['request_ms'] for x in g]), 3)} |")
    out["three-phase-table"] = "\n".join(lines)

    # inversions between the two orderings
    q = {L: med([x["request_ms"] for x in by[L]]) for L in by}
    inv = [(A, B) for i, A in enumerate(sorted(cold, key=cold.get))
           for B in sorted(cold, key=cold.get)[i + 1:] if q[A] > q[B]]
    best = max(inv, key=lambda ab: min(cold[ab[1]] / cold[ab[0]], q[ab[0]] / q[ab[1]]))
    A, B = best
    worst_cold = max(cold, key=cold.get)
    out["three-phase-summary"] = (
        f"Medians per language. **Which column matters depends entirely on process lifetime, and "
        f"the two orderings disagree — {len(inv)} language pairs swap places between them.** The "
        f"sharpest is {A} against {B}: {A} boots **{cold[B] / cold[A]:.1f}× faster** "
        f"({cold[A]:,.0f} ms vs {cold[B]:,.0f} ms) and then serves requests "
        f"**{q[A] / q[B]:.1f}× slower** ({q[A]:.3f} ms vs {q[B]:.3f} ms). A CLI invoked per command "
        f"should read the start-up column; a long-lived server answering a million queries should "
        f"read the last one, and would be badly misled by the first.\n\n"
        f"The disagreement is not universal, and the ends of the table are stable: "
        f"{worst_cold} is last on both, at {cold[worst_cold]:,.0f} ms to boot and "
        f"{q[worst_cold]:.1f} ms per request.")

    # --- dedup ground truth ---------------------------------------------------
    rl = [r for r in rows if r.get("rows_loaded")]
    ded = [r for r in rl if r["rows_loaded"] < 20000]
    raw = [r for r in rl if r["rows_loaded"] >= 20000]
    lines = ["| | n | matches loaded |", "|---|---:|---|",
             f"| reconciled | {len(ded)} | {min(r['rows_loaded'] for r in ded):,} – "
             f"{max(r['rows_loaded'] for r in ded):,} |",
             f"| not reconciled | {len(raw)} | {min(r['rows_loaded'] for r in raw):,} – "
             f"{max(r['rows_loaded'] for r in raw):,} (file sum: 23,954) |"]
    out["dedup-table"] = "\n".join(lines)
    agree = sum(1 for r in rl if (surv.get((r["language"], r["model"], r.get("effort", "")), {})
                                  .get("dedup", "none") != "none") == (r["rows_loaded"] < 20000))
    out["dedup-summary"] = (
        f"So **{len(raw)} of {len(rl)} measurable runs double-count the overlapping fixtures**, and "
        f"the rest land in a tight band around "
        f"{statistics.median([r['rows_loaded'] for r in ded]) / 1000:.1f}k despite reconciling "
        f"independently, in different languages, with different keys. That agreement across "
        f"implementations is itself evidence the figure is right.\n\n"
        f"It also lets the source-reading classifier used later in this post be checked: its "
        f"labels agree with the measured counts on **{agree} of {len(rl)} runs "
        f"({100 * agree / len(rl):.0f}%)**. Good enough to report distributions from, not good "
        f"enough to hang a causal claim on — which is exactly what happened to the deduplication "
        f"row in the per-request table.")
    q_d = med([r["request_ms"] for r in ded])
    q_r = med([r["request_ms"] for r in raw])
    out["dedup-contradiction"] = (
        f"**But the deduplication row does not survive checking, and it is worth showing why "
        f"rather than quietly dropping it.** {len(rl)} of the {len(rows)} servers announce how many "
        f"matches they loaded in their own start-up banner, which is ground truth for whether they "
        f"reconciled the files. Against that measured signal the direction reverses: the {len(ded)} "
        f"runs that demonstrably reconciled have a per-request median of **{q_d:.3f} ms**, and the "
        f"{len([r for r in raw if r.get('request_ms') is not None])} measurable runs that did not "
        f"are **{q_r:.3f} ms** — faster, not slower. The large figure in the table comes from "
        f"source-text labels over all {len(rows)}, and it does not hold where the truth is "
        f"observable. Fewer rows to scan is a real effect and it is small; whatever those runs are "
        f"paying for, it is not the row count.")
    return out


def main() -> int:
    rows, surv = load()
    blocks = build(rows, surv)
    text = BLOG.read_text()
    missing, changed = [], []
    for name, body in blocks.items():
        start, end = f"<!-- GEN:{name} -->", f"<!-- /GEN:{name} -->"
        if start not in text or end not in text:
            missing.append(name)
            continue
        i, j = text.index(start) + len(start), text.index(end)
        if text[i:j].strip() != body.strip():
            changed.append(name)
        text = text[:i] + "\n" + body + "\n" + text[j:]
    if missing:
        print(f"markers not found for: {', '.join(missing)}", file=sys.stderr)
        return 2
    if "--check" in sys.argv:
        print(f"stale: {', '.join(changed)}" if changed else "all generated blocks match the data")
        return 1 if changed else 0
    BLOG.write_text(text)
    print(f"regenerated {len(blocks)} blocks; updated: {', '.join(changed) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
