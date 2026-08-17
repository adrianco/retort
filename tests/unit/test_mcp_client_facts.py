"""Golden answers read by a real MCP client instead of a hand-written parser.

The point of this scorer is to delete the guessing that produced every false
failure on brazil-bench. The point of these tests is the confound it introduces
in exchange: the 2019 Série A table is famous, so a judge can answer perfectly
while the server sits broken and unused.
"""
from __future__ import annotations

import json

import pytest

from retort.scoring.scorers import mcp_client_facts as mcf


def _stream(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events)


def _tool_use(name: str, args: dict) -> dict:
    return {"message": {"content": [{"type": "tool_use", "name": name,
                                     "input": args}]}}


def _said(text: str) -> dict:
    return {"type": "result", "result": text}


class TestTheMemoryGuard:
    """A correct answer with no tool call is not a measurement of the server."""

    def test_no_mcp_tool_call_scores_zero(self, tmp_path, monkeypatch):
        """Flamengo's 90 points is in every frontier model's training data.

        A judge that never touched the server can still produce the exact right
        JSON. Trusting the prose here would score a dead server 1.00.
        """
        monkeypatch.setattr(mcf.rt, "_build_then_entry",
                            lambda d, l, resolved=None: (["/bin/true"], ""))
        perfect = json.dumps({"played": 38, "points": 90, "clubs": 20,
                              "tool": "standings"})
        monkeypatch.setattr(mcf.subprocess, "run", lambda *a, **k: type(
            "P", (), {"stdout": _stream(_said(perfect)), "stderr": "",
                      "returncode": 0})())
        res = mcf.measure(tmp_path, "rust")
        assert res.score == 0.0
        assert "without calling a single MCP tool" in res.note

    def test_a_self_reported_tool_name_is_not_evidence(self, tmp_path, monkeypatch):
        """The verdict names a tool, but the transcript shows none was called."""
        monkeypatch.setattr(mcf.rt, "_build_then_entry",
                            lambda d, l, resolved=None: (["/bin/true"], ""))
        claimed = json.dumps({"played": 38, "points": 90, "clubs": 20,
                              "tool": "mcp__brazil__standings"})
        monkeypatch.setattr(mcf.subprocess, "run", lambda *a, **k: type(
            "P", (), {"stdout": _stream(_said(claimed)), "stderr": "",
                      "returncode": 0})())
        assert mcf.measure(tmp_path, "rust").score == 0.0

    def test_a_non_mcp_tool_does_not_count(self):
        """Reading the CSVs off disk is not using the server."""
        stream = _stream(_tool_use("Read", {"file_path": "data/matches.csv"}),
                         _tool_use("ToolSearch", {"query": "brazil"}))
        assert mcf._tool_calls_of(stream, "mcp__brazil__") == []

    def test_real_mcp_calls_are_collected_with_their_arguments(self):
        """Observed against the rust binary: the client retries the competition
        string on its own — the exact step whose hand-rolled version shipped the
        `Brasileirao` vs `Brasileirão` bug."""
        stream = _stream(
            _tool_use("mcp__brazil__standings", {"competition": "Serie A"}),
            _tool_use("mcp__brazil__team_record", {"team": "Flamengo"}))
        calls = mcf._tool_calls_of(stream, "mcp__brazil__")
        assert [c["tool"] for c in calls] == ["mcp__brazil__standings",
                                              "mcp__brazil__team_record"]
        assert calls[0]["args"] == {"competition": "Serie A"}


class TestVerdict:
    def test_a_null_figure_fails_that_assertion_only(self):
        """The rust cell really scores this: played and points right, clubs
        null, because `standings` is a tool a real client rejects."""
        v = mcf._verdict_of('{"played": 38, "points": 90, "clubs": null, '
                            '"tool": "team_record"}')
        assert v["played"] == 38 and v["clubs"] is None

    def test_the_verdict_is_found_after_prose(self):
        v = mcf._verdict_of('I had to use team_record because standings was '
                            'rejected.\n{"played": 38, "points": 90, "clubs": 20}')
        assert v == {"played": 38, "points": 90, "clubs": 20}

    def test_no_verdict_is_not_a_pass(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mcf.rt, "_build_then_entry",
                            lambda d, l, resolved=None: (["/bin/true"], ""))
        monkeypatch.setattr(mcf.subprocess, "run", lambda *a, **k: type(
            "P", (), {"stdout": _stream(
                _tool_use("mcp__brazil__standings", {}),
                _said("I could not work it out.")),
                "stderr": "", "returncode": 0})())
        res = mcf.measure(tmp_path, "rust")
        assert res.score == 0.0 and "no parseable verdict" in res.note

    def test_a_double_counting_server_is_caught(self, tmp_path, monkeypatch):
        """76 played is exactly 2x38 — the corpus's five overlapping match files
        concatenated. The client reports what the server said, so this fails."""
        monkeypatch.setattr(mcf.rt, "_build_then_entry",
                            lambda d, l, resolved=None: (["/bin/true"], ""))
        monkeypatch.setattr(mcf.subprocess, "run", lambda *a, **k: type(
            "P", (), {"stdout": _stream(
                _tool_use("mcp__brazil__standings", {"season": 2019}),
                _said('{"played": 76, "points": 180, "clubs": 20}')),
                "stderr": "", "returncode": 0})())
        res = mcf.measure(tmp_path, "rust")
        assert res.score == pytest.approx(1 / 3)
        assert "expected 38, server said 76" in res.note


def test_the_client_is_isolated_from_the_hosts_own_mcp_servers():
    """Without --strict-mcp-config the judge inherits whatever the run host has
    configured, and the number stops being a property of the produced server."""
    import inspect

    src = inspect.getsource(mcf.measure)
    assert "--strict-mcp-config" in src


def test_the_config_carries_no_cwd_key():
    """`cwd` is not honoured; a server that cannot find data/ starts and then
    fails to connect, which reads identically to a broken program. The client is
    launched with cwd=run_dir instead."""
    cfg = json.loads(mcf._mcp_config(["/path/to/server", "--flag"]))
    entry = cfg["mcpServers"][mcf.SERVER_NAME]
    assert "cwd" not in entry
    assert entry["command"] == "/path/to/server" and entry["args"] == ["--flag"]
