"""Tests for optimal-stack selection (`retort report optimal`)."""

from __future__ import annotations

import sqlite3

import pytest

from retort.reporting import optimal as opt

# Columns the module reads. Kept minimal but faithful to master.db's flat schema.
_COLS = (
    "experiment, task, language, model, prompt, requirement_coverage, "
    "cost_usd, duration_seconds, max_context_tokens, test_coverage, tokens"
)


def _db(rows: list[tuple]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE runs (experiment TEXT, task TEXT, language TEXT, model TEXT, "
        "prompt TEXT, requirement_coverage REAL, cost_usd REAL, duration_seconds REAL, "
        "max_context_tokens REAL, test_coverage REAL, tokens REAL)"
    )
    conn.executemany(
        f"INSERT INTO runs ({_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    return conn


def _cloud_row(lang, model, cov, cost, exp="experiment-6"):
    return (exp, "rest-api-crud", lang, model, "none", cov, cost, 200.0, None, cov, 1e6)


def _local_row(lang, cov, exp="experiment-27-sampling-ff-bookshop"):
    # blank model, tuned-sampling experiment -> attributed to the local stack by slug
    return (exp, "rest-api-crud", lang, "", "none", cov, 0.0, 300.0, None, cov, 1e6)


def test_leading_stacks_table_reports_per_task_reliability():
    conn = _db([
        _cloud_row("python", "claude-fable-5", 1.0, 1.0),
        ("experiment-10-brazil", "brazil-soccer-mcp", "python", "claude-fable-5",
         "BDD", 1.0, 9.0, 1000.0, None, 1.0, 1e6),
        _cloud_row("python", "claude-opus-4-8", 1.0, 0.9),
        # A local (80B) hard-task run — the leading table shows the measured hard
        # number (0.00 here), not a blanket "n/q". Uses the featured 0.9 hard
        # experiment (exp-39; the featured 80B where is exp-38 routine + exp-39 hard).
        ("experiment-39-brazil-80b-fullctx", "brazil-soccer-mcp", "go",
         "mlxlocal/mlx-community--Qwen3-Coder-Next-4bit", "none",
         0.83, 0.0, 1600.0, None, 0.6, 5e6),
    ])
    out = opt.leading_stacks_table(conn)
    assert "Claude Fable 5" in out
    assert "Qwen3-Coder-Next 80B (local" in out
    assert "1.00 · 1.00" in out
    # 80B has one hard run scoring < 1.0 -> hard column shows 0.00 (measured), not n/q.
    assert "0.00" in out
    # The 35B has no hard run here -> its hard column is "—", never "n/q".
    assert "n/q" not in out


def test_routine_scope_limits_leading_aggregate_not_matrix(monkeypatch):
    """A local stack's leading-table headline is scoped to its recommended languages,
    but the per-language matrix stays unscoped (still shows the failing languages)."""
    # A local stack that aces python but flunks a niche language it shouldn't be used for.
    stack = {
        "name": "Local Test 80B",
        "short": "Local 80B",
        "where": "experiment LIKE '%exp-test%'",
        "kind": "local",
        "pass_bar": 0.50,
        "cost_override": 0.0,
        "routine_scope": ["python"],
    }
    monkeypatch.setattr(opt, "FEATURED_STACKS", [stack])
    conn = _db([
        ("exp-test", "rest-api-crud", "python", "", "none", 1.0, 0.0, 300.0, None, 1.0, 1e6),
        ("exp-test", "rest-api-crud", "python", "", "none", 1.0, 0.0, 300.0, None, 1.0, 1e6),
        ("exp-test", "rest-api-crud", "clojure", "", "none", 0.0, 0.0, 300.0, None, 0.0, 1e6),
        ("exp-test", "rest-api-crud", "clojure", "", "none", 0.0, 0.0, 300.0, None, 0.0, 1e6),
    ])
    # Leading table: scoped to python only -> 1.00, NOT the 0.50 all-language blend.
    lead = opt.leading_stacks_table(conn)
    assert "1.00 ·" in lead
    assert "0.50 ·" not in lead
    # Matrix: unscoped -> the clojure 0.00 row is still visible.
    matrix = opt.per_language_matrix(conn)
    assert "| **clojure** | 0.00 (2) |" in matrix
    assert "| **python** | 1.00 (2) |" in matrix


def test_per_language_matrix_shows_pass_and_n_per_cell():
    conn = _db([
        _cloud_row("python", "claude-opus-4-8", 1.0, 0.5),
        _cloud_row("python", "claude-opus-4-8", 1.0, 0.5),
        _local_row("python", 1.0),
        _local_row("python", 0.0),   # one local miss -> pass 0.50 over n=2
    ])
    out = opt.per_language_matrix(conn)
    assert "| **python** |" in out
    assert "1.00 (2)" in out   # Opus 4.8 python: 2/2
    assert "0.50 (2)" in out   # local python: 1/2


def test_repair_runs_excluded_from_headline():
    """Self-repair second attempts (prompt=repair) must not inflate pass rates."""
    conn = _db([
        ("experiment-21-repair-lcm-bookshop", "rest-api-crud", "go", "", "repair",
         1.0, 0.0, 300.0, None, 1.0, 1e6),
        _local_row("go", 0.0),
    ])
    out = opt.per_language_matrix(conn)
    # only the non-repair miss counts -> 0.00 (1), not 0.50 (2)
    assert "0.00 (1)" in out


def test_health_flags_blank_model_and_missing_columns(tmp_path):
    conn = _db([_local_row("python", 1.0)])
    report = opt.health_report(conn, repo_root=tmp_path)
    assert "blank model" in report
    assert "No sampling columns" in report
    # tmp_path has no experiments/ dir -> the orphan check simply doesn't fire
    assert "Data health" in report


def test_health_flags_unmapped_model(tmp_path):
    conn = _db([_cloud_row("python", "brand-new-model-9", 1.0, 1.0)])
    report = opt.health_report(conn, repo_root=tmp_path)
    assert "Unmapped model strings" in report
    assert "brand-new-model-9" in report


def test_splice_is_idempotent(tmp_path):
    conn = _db([
        _cloud_row("python", "claude-opus-4-8", 1.0, 0.5),
        _local_row("python", 1.0),
    ])
    blog = tmp_path / "blog.md"
    blog.write_text(
        "intro\n"
        "<!-- GEN:per-language-matrix START -->\nOLD\n<!-- GEN:per-language-matrix END -->\n"
        "outro\n"
    )
    changed1, skipped1 = opt.splice(blog, conn)
    assert changed1 == 1
    # the other three keys have no markers here -> reported as skipped, not an error
    assert set(skipped1) == {"leading-stacks", "per-language", "prompt-method"}
    first = blog.read_text()
    assert "OLD" not in first and "| Language |" in first

    changed2, _ = opt.splice(blog, conn)
    assert blog.read_text() == first   # second run is a no-op
