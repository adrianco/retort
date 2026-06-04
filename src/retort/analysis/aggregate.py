"""Aggregate every experiment's ``retort.db`` into one master results table.

As the program accumulates experiments, per-DB analysis stops being enough —
you want to ask cross-experiment questions ("every opus-4.8 brazil run across
exp-3/4/5", "rest-api-crud vs brazil duration by model"). This builds a single
wide, tidy table (one row per run) from all ``experiment-*/retort.db`` files,
tagged with the experiment and task, so pandas/SQL can slice across the whole
program. It is rebuilt from scratch each run, so it always reflects current data
(re-run it after a re-evaluation pass to pick up new metrics).
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

# Scored response metrics, in canonical column order.
METRICS = [
    "code_quality", "test_coverage", "defect_rate", "maintainability",
    "idiomatic", "token_efficiency", "requirement_coverage",
]
# Side-channel telemetry (underscore-prefixed in run_results) -> clean column.
TELEMETRY = {
    "_duration_seconds": "duration_seconds",
    "_tokens": "tokens",
    "_cost_usd": "cost_usd",
    "_turns": "turns",
}
FACTORS = ["language", "model", "tooling", "prompt"]
TEXT_COLS = ["experiment", "task", "status", "started_at", "finished_at"] + FACTORS


def task_for(exp_dir: Path) -> str:
    """Best-effort task name for an experiment, from its workspace.yaml source."""
    wf = exp_dir / "workspace.yaml"
    if wf.exists():
        m = re.search(r"source:\s*(\S+)", wf.read_text())
        if m:
            src = m.group(1).lower()
            if "rest-api-crud" in src or "bookshop" in src:
                return "rest-api-crud"
            if "brazil" in src or "soccer" in src:
                return "brazil-soccer-mcp"
            return m.group(1)
    return "unknown"


def collect_runs(experiments_dir: Path) -> list[dict]:
    """One dict per run across all experiment DBs, wide (a column per metric)."""
    rows: list[dict] = []
    # Match both top-level (experiment-8/retort.db) and one level of nesting
    # (experiment-7/brazil/retort.db) — some experiments split one study across
    # task sub-workspaces. Dedupe in case the patterns overlap.
    db_paths = sorted(set(experiments_dir.glob("experiment-*/retort.db"))
                      | set(experiments_dir.glob("experiment-*/*/retort.db")))
    for db in db_paths:
        parent = db.parent
        # Nested DBs (parent is the task sub-dir) get a compound label so each
        # row's `experiment` is unique, e.g. experiment-7-brazil.
        exp = parent.name if parent.name.startswith("experiment-") \
            else f"{parent.parent.name}-{parent.name}"
        task = task_for(parent)
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            runs = con.execute(
                "SELECT id, replicate, status, started_at, finished_at, "
                "run_config_json FROM experiment_runs"
            ).fetchall()
        except sqlite3.OperationalError:
            con.close()
            continue
        for r in runs:
            cfg = json.loads(r["run_config_json"] or "{}")
            row: dict = {
                "experiment": exp, "task": task, "status": r["status"],
                "replicate": r["replicate"], "started_at": r["started_at"],
                "finished_at": r["finished_at"],
            }
            for f in FACTORS:
                row[f] = cfg.get(f)
            for m in METRICS:
                row[m] = None
            for c in TELEMETRY.values():
                row[c] = None
            for mr in con.execute(
                "SELECT metric_name, value FROM run_results WHERE run_id=?", (r["id"],)
            ):
                name = mr["metric_name"]
                if name in METRICS:
                    row[name] = mr["value"]
                elif name in TELEMETRY:
                    row[TELEMETRY[name]] = mr["value"]
            rows.append(row)
        con.close()
    return rows


def build_master_db(experiments_dir: Path, out_path: Path) -> int:
    """(Re)build the master DB from all experiment DBs. Returns the run count."""
    rows = collect_runs(experiments_dir)
    cols = TEXT_COLS + ["replicate"] + METRICS + list(TELEMETRY.values())

    def coltype(c: str) -> str:
        if c == "replicate":
            return "INTEGER"
        if c in TEXT_COLS:
            return "TEXT"
        return "REAL"

    if out_path.exists():
        out_path.unlink()
    con = sqlite3.connect(out_path)
    con.execute(f"CREATE TABLE runs ({', '.join(f'{c} {coltype(c)}' for c in cols)})")
    placeholders = ", ".join("?" for _ in cols)
    con.executemany(
        f"INSERT INTO runs ({', '.join(cols)}) VALUES ({placeholders})",
        [tuple(r.get(c) for c in cols) for r in rows],
    )
    con.commit()
    con.close()
    return len(rows)


def write_csv(experiments_dir: Path, out_path: Path) -> int:
    """Also emit a CSV of the same wide table (handy for pandas/sharing)."""
    import csv
    rows = collect_runs(experiments_dir)
    cols = TEXT_COLS + ["replicate"] + METRICS + list(TELEMETRY.values())
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c) for c in cols})
    return len(rows)
