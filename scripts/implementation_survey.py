#!/usr/bin/env python3
"""Classify HOW each archived brazil run implemented the task, then look for
patterns across model / effort / language.

Motivation: two runs of the SAME model at different thinking levels produced
programs whose start-up differed by 27x, and the cause was not the language —
one materialized the whole corpus at import, the other streamed it. The spec
gate cannot see that: both implement the same checklist and both score 12/12.
So the design choices are invisible in every number retort currently records.

This reads the source and classifies each run along axes that are visible in the
code and that plausibly move the runtime numbers:

  storage    in-memory structures vs an embedded database (SQLite/DETS/...)
  loading    eager materialization vs lazy/streaming iteration
  indexing   precomputed lookup maps vs linear scans at query time
  dedup      does it reconcile the five overlapping match files at all
  protocol   an MCP SDK vs hand-rolled JSON-RPC over stdio
  layout     single-file script vs multi-module package

Everything here is a HEURISTIC over source text. Treat a cell as evidence, not
proof: the point is the distribution, not any single run's label.

Usage:  python scripts/implementation_survey.py <experiment-dir> [more...]
        (writes docs/implementation-survey.json)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SRC_SUFFIXES = {".py", ".go", ".rs", ".ts", ".js", ".java", ".cs", ".cpp", ".cc",
                ".c", ".h", ".hpp", ".m", ".swift", ".clj", ".ex", ".exs", ".erl"}
SKIP_PARTS = {"_judge", "node_modules", "venv", ".venv", "target", "build",
              "dist", "deps", "_build", ".git", "obj", "bin"}


def source_files(run_dir: Path) -> list[Path]:
    out = []
    for p in run_dir.rglob("*"):
        if p.suffix.lower() not in SRC_SUFFIXES or not p.is_file():
            continue
        if SKIP_PARTS & set(p.parts):
            continue
        name = p.name.lower()
        if "test" in name or "spec" in name:      # tests are not the implementation
            continue
        out.append(p)
    return out


def classify(run_dir: Path) -> dict:
    files = source_files(run_dir)
    if not files:
        return {"classified": False}
    text = "\n".join(f.read_text(errors="replace") for f in files)
    low = text.lower()
    loc = text.count("\n")

    def any_of(*pats: str) -> bool:
        return any(re.search(p, text, re.I | re.M) for p in pats)

    # --- storage -----------------------------------------------------------
    sqlite = any_of(r"\bsqlite", r"\bSQLite3?\b", r"\bdatabase/sql\b", r"\bDETS\b",
                    r"\bMicrosoft\.Data\.Sqlite\b", r"\brusqlite\b", r"better-sqlite3")
    duckdb = any_of(r"\bduckdb\b")
    storage = "sqlite" if sqlite else ("duckdb" if duckdb else "in-memory")

    # --- graph representation ---------------------------------------------
    graph_lib = any_of(r"\bnetworkx\b", r"\bneo4j\b", r"\bigraph\b", r"\bpetgraph\b",
                       r"\bJGraphT\b", r"\bgraphology\b")
    adjacency = any_of(r"adjacen", r"\bedges?\b.{0,40}\bnodes?\b", r"\bneighbou?rs\b")
    graph = "library" if graph_lib else ("hand-rolled" if adjacency else "none/implicit")

    # --- loading strategy --------------------------------------------------
    # Eager: the whole file becomes a list/array in one call at load time.
    eager = any_of(r"list\(\s*csv\.", r"\.readAll\(", r"ReadAll\(", r"readlines\(\)",
                   r"File\.ReadAllLines", r"collect::<Vec", r"\.collect\(Collectors\.toList",
                   r"Files\.readAllLines", r"csv\.reader\(.{0,40}\)\s*\)")
    lazy = any_of(r"yield\s+from", r"\byield\b", r"for\s+row\s+in\s+csv\.DictReader",
                  r"\.Read\(\)\s*$", r"bufio\.Scanner", r"BufReader", r"Stream\.",
                  r"\.lines\(\)", r"IEnumerable", r"csv\.NewReader")
    if eager and not lazy:
        loading = "eager"
    elif lazy and not eager:
        loading = "streaming"
    elif eager and lazy:
        loading = "mixed"
    else:
        loading = "unclear"

    # --- indexing ----------------------------------------------------------
    indexed = any_of(r"index\[", r"_index\b", r"byTeam", r"by_team", r"defaultdict",
                     r"make\(map\[", r"HashMap::new", r"new HashMap", r"Dictionary<",
                     r"groupby", r"group_by", r"\.GroupBy\(")
    indexing = "precomputed-index" if indexed else "scan"

    # --- deduplication -----------------------------------------------------
    dedup = any_of(r"\bdedup", r"\bdistinct\b", r"\bunique\b", r"\bseen\b",
                   r"set\(\)", r"HashSet", r"map\[string\]bool", r"\bDISTINCT\b")
    # a date-window key is the competition-canonical reconciliation
    window = any_of(r"timedelta\(days=1\)", r"AddDate\(0,\s*0,\s*1\)", r"\+/-\s*1\s*day",
                    r"one[_ ]day", r"Duration::days\(1\)", r"days\(1\)")
    dedup_kind = ("date-window" if window else ("key-set" if dedup else "none"))

    # --- protocol ----------------------------------------------------------
    sdk = any_of(r"from\s+mcp[\s.]", r"import\s+mcp\b", r"@modelcontextprotocol",
                 r"\bFastMCP\b", r"mcp-sdk", r"ModelContextProtocol")
    handrolled = any_of(r'"jsonrpc"\s*:\s*"2\.0"', r"jsonrpc.*2\.0")
    protocol = "sdk" if sdk else ("hand-rolled" if handrolled else "unclear")

    return {
        "classified": True,
        "files": len(files),
        "loc": loc,
        "storage": storage,
        "graph": graph,
        "loading": loading,
        "indexing": indexing,
        "dedup": dedup_kind,
        "protocol": protocol,
    }


def factors(run_dir: Path) -> dict:
    return dict(x.split("=", 1) for x in run_dir.parent.name.split("_") if "=" in x)


def crosstab(rows: list[dict], axis: str, by: str) -> str:
    table: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if r.get(axis) and r.get(by):
            table[r[by]][r[axis]] += 1
    if not table:
        return ""
    vals = sorted({v for c in table.values() for v in c})
    out = [f"| {by} | " + " | ".join(vals) + " | n |",
           "|---|" + "---:|" * (len(vals) + 1)]
    for k in sorted(table):
        c = table[k]
        n = sum(c.values())
        out.append(f"| **{k}** | " + " | ".join(str(c.get(v, 0)) for v in vals)
                   + f" | {n} |")
    return "\n".join(out)


def main() -> int:
    rows: list[dict] = []
    for exp in sys.argv[1:]:
        for rd in sorted(p for p in (Path(exp) / "runs").glob("*/rep*")
                         if p.is_dir() and not p.name.endswith("-failed")):
            f = factors(rd)
            info = classify(rd)
            if not info.get("classified"):
                continue
            info.update({
                "language": f.get("language", "?"),
                "model": f.get("model", "?"),
                "effort": f.get("effort", ""),
                "experiment": Path(exp).parent.name,
                "run": str(rd),
            })
            rows.append(info)

    Path("docs/implementation-survey.json").write_text(json.dumps(rows, indent=1))
    print(f"classified {len(rows)} runs\n")

    for axis in ("loading", "storage", "indexing", "dedup", "protocol", "graph"):
        print(f"\n## {axis} by language\n")
        print(crosstab(rows, axis, "language"))
        print(f"\n## {axis} by model\n")
        print(crosstab(rows, axis, "model"))
        eff = [r for r in rows if r["effort"]]
        if eff:
            print(f"\n## {axis} by effort\n")
            print(crosstab(eff, axis, "effort"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
