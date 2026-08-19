"""Summarise an MCP conformance sweep: base rate, breakdown, gating verdict.

The question the sweep exists to answer is whether `mcp_conformance` should
graduate from a scored column to a gating one. That is a decision about a BASE
RATE, so this reports it three ways — overall, by language, by model era — and
keeps unmeasurable runs out of every denominator. A run whose archive could not
be resurrected is not evidence about conformance in either direction.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HARD_CHECKS = {"structuredContent is an object", "declared outputSchema is honoured",
               "result is an object", "content is a list",
               "content blocks are well typed", "inputSchema is a usable JSON Schema",
               "tool has a name", "answers tools/call",
               "completes the MCP handshake", "advertises at least one tool"}


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def hard_failures(rec: dict) -> list[dict]:
    """Hard failures for a row, tolerating rows written before severities existed."""
    out = []
    for c in rec.get("failed_checks", []):
        sev = c.get("severity")
        if sev == "advisory":
            continue
        if sev is None and c.get("name") not in HARD_CHECKS:
            continue
        out.append(c)
    return out


def advisories(rec: dict) -> list[dict]:
    out = []
    for c in rec.get("failed_checks", []):
        sev = c.get("severity")
        if sev == "advisory" or (sev is None and c.get("name") not in HARD_CHECKS):
            out.append(c)
    return out


def main() -> int:
    path = Path(sys.argv[1])
    rows = load(path)
    measured = [r for r in rows if r.get("measured")]
    unmeasurable = [r for r in rows if not r.get("measured")]

    print(f"MCP CONFORMANCE SWEEP — {len(rows)} archived brazil runs")
    print(f"  measured      {len(measured):3d}")
    print(f"  unmeasurable  {len(unmeasurable):3d}  (archive could not be resurrected;")
    print( "                     NOT evidence about conformance either way)")
    print()

    clean = [r for r in measured if not hard_failures(r)]
    dirty = [r for r in measured if hard_failures(r)]
    rate = len(dirty) / len(measured) if measured else 0.0
    print(f"HARD VIOLATIONS: {len(dirty)}/{len(measured)} measured runs ({rate:.0%})")
    print(f"  a real client rejects a tool, or the server breaks its own declared contract")
    print()

    print("by hard check:")
    for name, n in collections.Counter(
            c["name"] for r in measured for c in hard_failures(r)).most_common():
        print(f"  {n:3d}  {name}")
    print()
    print("advisories (reported, never scored):")
    for name, n in collections.Counter(
            c["name"] for r in measured for c in advisories(r)).most_common():
        print(f"  {n:3d}  {name}")
    print()

    print(f"{'language':12s} {'measured':>8s} {'clean':>6s} {'hard':>5s}  rate")
    by_lang = collections.defaultdict(list)
    for r in measured:
        by_lang[r["language"]].append(r)
    for lang, rs in sorted(by_lang.items(), key=lambda kv: -len(kv[1])):
        bad = [r for r in rs if hard_failures(r)]
        print(f"  {lang:10s} {len(rs):8d} {len(rs)-len(bad):6d} {len(bad):5d}  "
              f"{len(bad)/len(rs):.0%}")
    print()

    print("worst offenders:")
    for r in sorted(dirty, key=lambda r: r["score"])[:10]:
        hf = hard_failures(r)
        tools = sorted({c.get("tool", "") for c in hf if c.get("tool")})
        print(f"  {r['language']:11s} {r['score']:.2f}  {r['experiment'][:26]:26s} "
              f"{len(hf)} hard on {', '.join(tools)[:40]}")
    print()

    print("why runs were unmeasurable:")
    for note, n in collections.Counter(
            r["note"][:52] for r in unmeasurable).most_common(10):
        print(f"  {n:3d}  {note}")
    print()

    print("GATING VERDICT")
    if rate > 0.25:
        print(f"  DO NOT GATE yet: {rate:.0%} of measured runs have a hard violation.")
        print( "  Gating now would retroactively fail a large fraction of the archive on")
        print( "  a dimension it was never measured against. Report it, publish the base")
        print( "  rate, and revisit once models have seen the feedback.")
    elif rate > 0.0:
        print(f"  CANDIDATE for gating: only {rate:.0%} of measured runs violate.")
        print( "  Small enough to be a real defect signal rather than a norm — but check")
        print( "  the per-language table first: a violation concentrated in one language")
        print( "  is a toolchain story, not a capability one.")
    else:
        print("  No hard violations found. Nothing to gate on yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
