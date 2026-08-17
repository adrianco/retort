"""Promotion-gate evidence, computed rather than hand-typed.

`gates.py` checks p_value, posterior_confidence and dominated_confidence, and
until now NOTHING produced any of them — they had to be worked out by hand and
passed as JSON. Every workspace.yaml carries `trial_to_production:
{posterior_confidence: 0.80}` as the schema default, so that gate reported
"missing from evidence" for every stack, forever.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from retort.promotion.evidence import compute_evidence


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "master.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE runs (model TEXT, task TEXT, requirement_coverage REAL,"
                " cost_usd REAL, duration_seconds REAL)")

    def add(model, task, rc, cost, secs, n=1):
        con.executemany("INSERT INTO runs VALUES (?,?,?,?,?)",
                        [(model, task, rc, cost, secs)] * n)

    add("solid", "brazil", 1.0, 2.0, 300, n=6)          # always passes, pricey
    add("cheap", "brazil", 1.0, 0.1, 100, n=3)          # cheap and fast
    add("cheap", "brazil", 0.5, 0.1, 100, n=3)          # ...but half the time
    add("solid", "bookshop", 1.0, 1.0, 100, n=4)
    con.commit(); con.close()
    return path


def test_confidence_rises_with_consistent_passes(db):
    ev = compute_evidence(db, "solid", task="brazil")
    assert ev["posterior_confidence"] > 0.9
    assert ev["n_runs"] == 6


def test_confidence_is_lower_when_half_the_runs_fail(db):
    solid = compute_evidence(db, "solid", task="brazil")["posterior_confidence"]
    cheap = compute_evidence(db, "cheap", task="brazil")["posterior_confidence"]
    assert cheap < solid


def test_a_cheap_stack_stays_on_the_frontier(db):
    """Pareto is multi-objective: nothing beats `cheap` on cost.

    Worse quality does NOT make a stack dominated when it wins another
    objective — that is the difference between a frontier and a ranking, and it
    is why promotion should not be decided on pass-proportion alone.
    """
    assert compute_evidence(db, "cheap", task="brazil")["dominated_confidence"] > 0.5


def test_task_filter_changes_the_answer(db):
    """Pooling tasks mixes the routine and the hard one into a single number."""
    pooled = compute_evidence(db, "solid")
    brazil = compute_evidence(db, "solid", task="brazil")
    assert pooled["n_runs"] == 10
    assert brazil["n_runs"] == 6


def test_p_value_is_never_invented(db):
    """It belongs to the ANOVA, which needs the whole design, not one stack."""
    assert "p_value" not in compute_evidence(db, "solid")


def test_unknown_stack_yields_nothing_rather_than_a_guess(db):
    assert compute_evidence(db, "never-run") == {}


def test_missing_database_is_not_an_error(tmp_path):
    assert compute_evidence(tmp_path / "absent.db", "solid") == {}


def test_a_single_run_gives_no_posterior(db):
    """One observation cannot support a posterior; the gate should say so."""
    con = sqlite3.connect(db)
    con.execute("INSERT INTO runs VALUES ('oneshot','brazil',1.0,1.0,100)")
    con.commit(); con.close()
    ev = compute_evidence(db, "oneshot", task="brazil")
    assert "posterior_confidence" not in ev
    assert ev["n_runs"] == 1
