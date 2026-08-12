"""What counts as a PASS must include every gate that can fail a run.

`report optimal` generates optimal-blog.md and optimal.json — this project's
headline recommendations. Its pass-proportion was `requirement_coverage >= 1.0`
alone, so when the factual gate shipped, exp-57's three wrong-answer runs were
counted as PASSES there. The gate had already failed them in the run, in the DB
status, and as a master.db column; only the metric everyone actually reads still
said "pass".

That is the fourth instance of one pattern in a single day — a gate that fires
locally and evaporates downstream (DB status, `rescore`, `aggregate`, and here).
Each was invisible because the run itself looked correct.
"""
from __future__ import annotations

import sqlite3

from retort.reporting.optimal import PASS_SQL, PASS_SQL_NO_FACTUAL, pass_sql


def _db():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE runs (name TEXT, requirement_coverage REAL, "
                "factual_accuracy REAL)")
    return con


def _passes(con, name) -> bool:
    row = con.execute(
        f"SELECT CASE WHEN {PASS_SQL} THEN 1 ELSE 0 END FROM runs WHERE name=?",
        (name,)).fetchone()
    return bool(row[0])


def test_checklist_and_facts_both_required():
    con = _db()
    con.executemany("INSERT INTO runs VALUES (?,?,?)", [
        ("both_ok",        1.0,  1.0),
        ("wrong_answers",  1.0,  0.5),
        ("very_wrong",     1.0,  0.0),
        ("incomplete",     0.92, 1.0),
    ])
    assert _passes(con, "both_ok")
    assert not _passes(con, "wrong_answers")   # the exp-57 case
    assert not _passes(con, "very_wrong")
    assert not _passes(con, "incomplete")


def test_ungated_runs_are_not_rebased():
    """NULL factual_accuracy must still pass.

    It is NULL for every run predating the gate and for every task with no
    golden answers. A run may only lose its pass if its answers were actually
    checked and found wrong — otherwise adding the gate would silently rewrite
    284 historical brazil results and every bookshop run ever measured.
    """
    con = _db()
    con.executemany("INSERT INTO runs VALUES (?,?,?)", [
        ("pre_gate_pass", 1.0,  None),
        ("pre_gate_fail", 0.5,  None),
    ])
    assert _passes(con, "pre_gate_pass")
    assert not _passes(con, "pre_gate_fail")


def test_a_database_without_the_column_still_works():
    """An older master.db has no factual_accuracy; a missing column is an
    OperationalError, not a NULL, so the clause must be chosen from the schema."""
    old = sqlite3.connect(":memory:")
    old.execute("CREATE TABLE runs (name TEXT, requirement_coverage REAL)")
    old.execute("INSERT INTO runs VALUES ('x', 1.0)")
    assert pass_sql(old) == PASS_SQL_NO_FACTUAL
    assert old.execute(
        f"SELECT CASE WHEN {pass_sql(old)} THEN 1 ELSE 0 END FROM runs").fetchone()[0] == 1

    new = _db()
    assert pass_sql(new) == PASS_SQL
