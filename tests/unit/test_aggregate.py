"""Tests for cross-experiment aggregation into the master results DB."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from retort.analysis.aggregate import build_master_db, collect_runs


def _make_experiment(exp_dir: Path, task_source: str, runs: list[dict]) -> None:
    """Create a minimal experiment dir with a workspace.yaml + retort.db."""
    exp_dir.mkdir(parents=True)
    (exp_dir / "workspace.yaml").write_text(
        f"tasks:\n  - source: {task_source}\n"
    )
    con = sqlite3.connect(exp_dir / "retort.db")
    con.execute(
        "CREATE TABLE experiment_runs (id INTEGER PRIMARY KEY, replicate INTEGER, "
        "status TEXT, started_at TEXT, finished_at TEXT, run_config_json TEXT)"
    )
    con.execute(
        "CREATE TABLE run_results (id INTEGER PRIMARY KEY, run_id INTEGER, "
        "metric_name TEXT, value REAL)"
    )
    for i, r in enumerate(runs, start=1):
        con.execute(
            "INSERT INTO experiment_runs (id, replicate, status, run_config_json) "
            "VALUES (?,?,?,?)",
            (i, r["replicate"], r["status"], json.dumps(r["config"])),
        )
        for metric, value in r["metrics"].items():
            con.execute(
                "INSERT INTO run_results (run_id, metric_name, value) VALUES (?,?,?)",
                (i, metric, value),
            )
    con.commit()
    con.close()


def test_aggregate_combines_experiments_with_task_tags(tmp_path: Path):
    _make_experiment(
        tmp_path / "experiment-1", "bundled://rest-api-crud",
        [{"replicate": 1, "status": "completed",
          "config": {"language": "go", "model": "opus", "tooling": "none"},
          "metrics": {"code_quality": 0.9, "test_coverage": 1.0,
                      "requirement_coverage": 1.0, "_duration_seconds": 120.0}}],
    )
    _make_experiment(
        tmp_path / "experiment-2", "github://brazil-bench/x/soccer.md",
        [{"replicate": 1, "status": "failed",
          "config": {"language": "rust", "model": "sonnet", "tooling": "beads"},
          "metrics": {"code_quality": 0.0, "test_coverage": 0.0}}],
    )

    rows = collect_runs(tmp_path)
    assert len(rows) == 2
    by_exp = {r["experiment"]: r for r in rows}

    e1 = by_exp["experiment-1"]
    assert e1["task"] == "rest-api-crud"
    assert e1["language"] == "go" and e1["model"] == "opus"
    assert e1["code_quality"] == 0.9 and e1["requirement_coverage"] == 1.0
    assert e1["duration_seconds"] == 120.0  # telemetry renamed from _duration_seconds

    e2 = by_exp["experiment-2"]
    assert e2["task"] == "brazil-soccer-mcp"
    assert e2["status"] == "failed"
    assert e2["requirement_coverage"] is None  # absent metric -> None


def test_build_master_db_is_rebuildable(tmp_path: Path):
    _make_experiment(
        tmp_path / "experiment-1", "bundled://rest-api-crud",
        [{"replicate": 1, "status": "completed",
          "config": {"language": "go", "model": "opus", "tooling": "none"},
          "metrics": {"code_quality": 0.9}}],
    )
    out = tmp_path / "master.db"
    n1 = build_master_db(tmp_path, out)
    assert n1 == 1
    # rebuild is idempotent (wipes + rebuilds), not append
    n2 = build_master_db(tmp_path, out)
    assert n2 == 1
    con = sqlite3.connect(out)
    count = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    cols = [r[1] for r in con.execute("PRAGMA table_info(runs)")]
    con.close()
    assert count == 1
    assert "experiment" in cols and "task" in cols and "requirement_coverage" in cols
