"""The retort→metaharness routing feed (report optimal --routing-json)."""
from __future__ import annotations


import re
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
    assert set(rc) == {
        "source", "generated_at", "master_db_runs", "objective", "notes",
        "models", "routes",
    }
    # STALENESS MARKERS. This file is committed for other tools to consume and
    # nothing errors when it rots -- it was found 7 weeks stale on 2026-09-24,
    # still routing to a board without Opus 5.5. A consumer needs to be able to
    # tell, so the timestamp and the row count behind it are part of the shape.
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", rc["generated_at"])
    assert rc["master_db_runs"] is None or rc["master_db_runs"] >= 0
    assert "generated_at" in rc["notes"]
    assert opt.ROUTINE_TASK in rc["routes"] and opt.HARD_TASK in rc["routes"]
    routine = rc["routes"][opt.ROUTINE_TASK]
    # Each cell reports the best CLOUD and best LOCAL option separately — merging
    # them would let a $0 local stack hide the only figure a reader without that
    # hardware can act on. Either may be None ("nothing measured qualifies").
    for _lang, cell in routine.items():
        assert set(cell) == {"cloud", "local"}
        for r in cell.values():
            if r is not None:
                assert "stack" in r and "effort" in r
                assert 0.0 <= r["pass"] <= 1.0 and r["n"] >= 1


def test_model_board_matches_the_published_table_shape():
    """`models` in the JSON and the model-blog board come from one generator, so
    they cannot drift — the board used to be hand-maintained and once showed
    Opus 4.8 at 1.00 on the hard task while the prose said 0.59."""
    c = _conn()
    try:
        board = opt.model_board(c)
    finally:
        c.close()
    assert board, "no featured stacks resolved"
    for row in board:
        assert {"stack", "short", "kind", "routine", "hard"} <= set(row)
        for half in ("routine", "hard"):
            if row[half] is not None:
                assert 0.0 <= row[half]["pass"] <= 1.0 and row[half]["n"] >= 1


def test_per_language_table_still_renders_after_refactor():
    """per_language_table now derives from per_language_routing — must be unchanged
    in shape (the optimal-blog GEN marker depends on it)."""
    c = _conn()
    try:
        table = opt.per_language_table(c)
    finally:
        c.close()
    assert table.startswith("| Language |") and "cheapest qualifying" in table
