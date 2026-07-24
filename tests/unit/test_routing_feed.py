"""The retort→metaharness routing feed (report optimal --routing-json)."""
from __future__ import annotations

import sqlite3

import pytest

from retort.reporting import optimal as opt

pytestmark = pytest.mark.skipif(not opt.DB.exists(), reason="master.db not present")


def _conn():
    return opt.open_db(opt.DB)


def test_routing_config_shape():
    c = _conn()
    try:
        rc = opt.routing_config(c)
    finally:
        c.close()
    assert set(rc) == {"source", "objective", "routes"}
    assert opt.ROUTINE_TASK in rc["routes"] and opt.HARD_TASK in rc["routes"]
    routine = rc["routes"][opt.ROUTINE_TASK]
    # every entry is either None (no qualifying stack) or a routing record with a
    # stack + a numeric pass rate — the cheapest-that-qualifies decision.
    for _lang, r in routine.items():
        if r is not None:
            assert "stack" in r and 0.0 <= r["pass"] <= 1.0 and r["n"] >= 1


def test_per_language_table_still_renders_after_refactor():
    """per_language_table now derives from per_language_routing — must be unchanged
    in shape (the optimal-blog GEN marker depends on it)."""
    c = _conn()
    try:
        table = opt.per_language_table(c)
    finally:
        c.close()
    assert table.startswith("| Language |") and "cheapest qualifying" in table
