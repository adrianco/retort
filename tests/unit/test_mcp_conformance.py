"""Would a real MCP client accept the produced server's replies?

Every check here is anchored to something observed on the wire, not imagined.
The headline case is exp-60's rust cell: `factual_accuracy` scores it 1.00 — the
correct 2019 table, all 20 clubs, Flamengo 38 played and 90 points — while
Claude Code, registered against the same binary as a genuine MCP client, rejects
two of its six tools. The text-reading probes cannot see that, because MCP
leaves the tool result's *text* free-form and pins only the envelope.
"""
from __future__ import annotations

import json

import pytest

from retort.scoring.scorers.mcp_conformance import (
    ConformanceResult,
    _check_result_envelope,
    _is_schema_object,
)


def _reply(**result) -> dict:
    return {"jsonrpc": "2.0", "id": 1, "result": result}


class TestStructuredContent:
    """The check that fails a server every other probe here calls perfect."""

    def test_a_top_level_array_is_rejected(self):
        """Verified on the wire against exp-60's rust binary.

        `standings` returns `{"content":[…], "structuredContent":[…20 rows…]}`.
        A league table is a list, so an array is the natural thing to return —
        and the spec requires an object, so a real client refuses the tool. The
        server is otherwise correct, which is exactly why this needs its own
        column rather than a note in someone's head.
        """
        res = ConformanceResult()
        tool = {"name": "standings", "inputSchema": {"type": "object"}}
        rows = [{"team": "Flamengo-RJ", "points": 90}, {"team": "Santos-SP"}]
        _check_result_envelope(res, tool, _reply(
            content=[{"type": "text", "text": json.dumps(rows)}],
            structuredContent=rows))

        sc = next(c for c in res.checks if c.name == "structuredContent is an object")
        assert sc.passed is False
        assert "list" in sc.detail and "rejects" in sc.detail
        assert sc.tool == "standings"

    def test_an_object_is_accepted(self):
        res = ConformanceResult()
        tool = {"name": "standings", "inputSchema": {"type": "object"},
                "outputSchema": {"type": "object"}}
        _check_result_envelope(res, tool, _reply(
            content=[{"type": "text", "text": "{}"}],
            structuredContent={"standings": [{"team": "Flamengo"}]}))
        assert all(c.passed for c in res.checks), [c.as_dict() for c in res.checks
                                                   if not c.passed]

    def test_structured_content_without_an_output_schema_is_flagged(self):
        """The rust server does this too — a client cannot know what it is."""
        res = ConformanceResult()
        tool = {"name": "standings", "inputSchema": {"type": "object"}}
        _check_result_envelope(res, tool, _reply(
            content=[{"type": "text", "text": "{}"}], structuredContent={"a": 1}))
        c = next(c for c in res.checks
                 if c.name == "structuredContent has a declared outputSchema")
        assert c.passed is False

    def test_a_declared_output_schema_must_actually_be_honoured(self):
        res = ConformanceResult()
        tool = {"name": "standings", "inputSchema": {"type": "object"},
                "outputSchema": {"type": "object"}}
        _check_result_envelope(res, tool, _reply(
            content=[{"type": "text", "text": "a table"}]))
        c = next(c for c in res.checks if c.name == "declared outputSchema is honoured")
        assert c.passed is False


class TestResultEnvelope:
    def test_content_must_be_a_list_of_typed_blocks(self):
        res = ConformanceResult()
        tool = {"name": "t", "inputSchema": {"type": "object"}}
        _check_result_envelope(res, tool, _reply(content="just a string"))
        assert not next(c for c in res.checks if c.name == "content is a list").passed

    def test_an_untyped_block_is_caught(self):
        res = ConformanceResult()
        tool = {"name": "t", "inputSchema": {"type": "object"}}
        _check_result_envelope(res, tool, _reply(content=[{"text": "no type field"}]))
        c = next(c for c in res.checks if c.name == "content blocks are well typed")
        assert c.passed is False

    def test_a_non_object_result_is_caught(self):
        res = ConformanceResult()
        _check_result_envelope(res, {"name": "t"}, {"jsonrpc": "2.0", "result": []})
        assert not res.checks[0].passed


class TestInputSchema:
    """A client builds the argument form from this; it has to be usable."""

    @pytest.mark.parametrize("schema,ok", [
        ({"type": "object", "properties": {"season": {"type": "integer"}}}, True),
        ({"type": "object"}, True),                       # a no-argument tool
        ({"type": "object", "required": ["season"]}, True),   # required, no props
        ("a string", False),
        ({"type": "object", "properties": ["season"]}, False),
        ({"type": "object", "required": "season"}, False),
        ({"type": "object", "properties": {"a": {}}, "required": ["b"]}, False),
    ])
    def test_shapes(self, schema, ok):
        assert _is_schema_object(schema)[0] is ok


def test_a_dead_server_scores_zero_not_none(tmp_path, monkeypatch):
    """Same rule as factual_accuracy: a server that will not start is a failed
    deliverable, not an unmeasurable one. runtime is the opposite on purpose."""
    from retort.scoring.scorers import mcp_conformance as mc

    monkeypatch.setattr(mc.rt, "_build_then_entry",
                        lambda d, l, resolved=None: (None, "no entrypoint"))
    res = mc.measure(tmp_path, "rust")
    assert res.score == 0.0 and res.ok is False
    assert "no entrypoint" in res.note


def test_the_score_is_the_proportion_of_checks_passed():
    res = ConformanceResult()
    res.add("a", True)
    res.add("b", False, "because")
    res.add("c", True)
    passed = sum(1 for c in res.checks if c.passed)
    assert passed / len(res.checks) == pytest.approx(2 / 3)


def test_it_is_scored_but_not_gated():
    """Gating a new measurement before the sweep would retroactively fail runs
    on a dimension they were never measured against. Measure, then decide."""
    import inspect

    from retort import cli

    src = inspect.getsource(cli)
    gate = src.split("conformance_failed", 1)
    assert len(gate) > 1, "the gate expression moved — re-check this test"
    window = gate[1][:400]
    assert "mcp_conformance" not in window
