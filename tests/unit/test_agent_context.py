"""The derived `agent_context` factor: what the agent had loaded besides the task."""

from __future__ import annotations

import json

from retort.analysis.agent_context import (
    CLEARED, ENABLED, LOCAL, UNVERIFIED, agent_context_for, classify_transcript,
)


def _claude_log(path, mcp_tools: int, mcp_calls: int = 0, prompt: int = 20000):
    tools = ["Bash", "Read"] + [f"mcp__srv__t{i}" for i in range(mcp_tools)]
    lines = [
        {"type": "system", "subtype": "init", "tools": tools},
        {"type": "assistant", "message": {"usage": {
            "input_tokens": 2, "cache_creation_input_tokens": prompt - 2,
            "cache_read_input_tokens": 0}, "content": [
            {"type": "tool_use", "name": "mcp__srv__t0"} for _ in range(mcp_calls)]}},
    ]
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return path


def _codex_log(path, mcp_calls: int):
    lines = [{"type": "thread.started"}, {"type": "turn.started"}]
    lines += [{"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "ruflo",
               "tool": "memory_search", "status": "failed"}} for _ in range(mcp_calls)]
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return path


def test_claude_with_mcp_tools_loaded_is_enabled(tmp_path):
    r = classify_transcript(_claude_log(tmp_path / "o.log", mcp_tools=418, prompt=34000))
    assert r == {"agent_context": ENABLED, "mcp_tools_loaded": 418, "mcp_calls": 0,
                 "first_turn_prompt_tokens": 34000}


def test_claude_with_zero_mcp_tools_is_cleared(tmp_path):
    r = classify_transcript(_claude_log(tmp_path / "o.log", mcp_tools=0))
    assert r["agent_context"] == CLEARED and r["mcp_tools_loaded"] == 0


def test_codex_that_called_mcp_is_enabled(tmp_path):
    r = classify_transcript(_codex_log(tmp_path / "o.log", mcp_calls=3))
    assert r["agent_context"] == ENABLED and r["mcp_calls"] == 3


def test_codex_without_calls_is_unverified_not_cleared(tmp_path):
    # Codex logs do not list the servers it loaded, so no calls proves nothing.
    r = classify_transcript(_codex_log(tmp_path / "o.log", mcp_calls=0))
    assert r["agent_context"] == UNVERIFIED and r["mcp_calls"] == 0


def test_missing_transcript_is_unverified(tmp_path):
    assert classify_transcript(tmp_path / "absent.log")["agent_context"] == UNVERIFIED


def _archive(exp, cfg, rep=1):
    d = exp / "runs" / "_".join(f"{k}={v}" for k, v in sorted(cfg.items())) / f"rep{rep}"
    d.mkdir(parents=True)
    return d


def test_provenance_isolation_marks_a_codex_run_cleared(tmp_path):
    cfg = {"agent": "codex", "language": "go", "model": "gpt-6-luna"}
    _codex_log(_archive(tmp_path, cfg) / "_agent_stdout.log", mcp_calls=0)
    (tmp_path / "provenance.json").write_text(json.dumps(
        {"agent_config": {"codex": {"isolation_args": ["--ignore-user-config"]}}}))
    assert agent_context_for(tmp_path, cfg, 1)["agent_context"] == CLEARED


def test_observed_mcp_use_beats_a_provenance_isolation_claim(tmp_path):
    cfg = {"language": "go", "model": "claude-sonnet-5-5"}
    _claude_log(_archive(tmp_path, cfg) / "_agent_stdout.log", mcp_tools=5)
    (tmp_path / "provenance.json").write_text(json.dumps(
        {"agent_config": {"claude_code": {"isolation_args": ["--strict-mcp-config"]}}}))
    assert agent_context_for(tmp_path, cfg, 1)["agent_context"] == ENABLED


def test_failed_rep_archive_is_found(tmp_path):
    cfg = {"language": "go", "model": "m"}
    d = _archive(tmp_path, cfg).parent / "rep2-failed"
    d.mkdir()
    _claude_log(d / "_agent_stdout.log", mcp_tools=7)
    assert agent_context_for(tmp_path, cfg, 2)["agent_context"] == ENABLED


def test_local_harness_is_its_own_level(tmp_path):
    cfg = {"agent": "hermes-0205", "language": "python"}
    assert agent_context_for(tmp_path, cfg, 1)["agent_context"] == LOCAL
