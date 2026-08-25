"""The DB must record WHICH gate failed, not a hardcoded guess.

`conformance_failed` folds three different gates — tests, spec, factual — into
one boolean, and _store_run_result used to label every one of them "tests did
not run (test_coverage=0)".

exp-62's arm A is the case in point: test_coverage=1.0, requirement_coverage
=0.917, and error_message="tests did not run (test_coverage=0)". The run failed
the SPEC gate; the archive said it had no tests. The console printed the right
reason all along — only the DB lied, and the DB is what every later query reads.
"""
from __future__ import annotations

import inspect

from retort import cli


def _error_message_expr() -> str:
    src = inspect.getsource(cli._store_run_result)
    start = src.index("error_message=(")
    return src[start:start + 400]


def test_the_message_is_not_hardcoded_to_the_tests_gate():
    expr = _error_message_expr()
    assert "conformance_reason" in expr, (
        "error_message ignores which gate fired")


def test_store_accepts_a_reason():
    sig = inspect.signature(cli._store_run_result)
    assert "conformance_reason" in sig.parameters


def test_the_live_path_distinguishes_all_three_gates():
    """Each gate must supply its own wording, in the console's order."""
    src = inspect.getsource(cli)
    i = src.index("conformance_reason=(")
    window = src[i:i + 420]
    assert "test_coverage=0" in window
    assert "requirement_coverage" in window
    assert "factual_accuracy" in window


def test_a_reasonless_failure_still_says_something():
    """Absent a reason it must not fall back to naming the wrong gate."""
    expr = _error_message_expr()
    assert "conformance gate failed" in expr
    assert expr.count('"tests did not run (test_coverage=0)"') == 0
