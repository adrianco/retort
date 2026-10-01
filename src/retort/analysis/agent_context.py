"""What the agent under test had loaded BESIDES the task: the `agent_context` factor.

WHY THIS EXISTS. Until 2026-09-29 the cloud agents inherited the machine owner's
setup — Claude loaded up to 418 MCP tools (ruvnet-brain, claude-flow, claude.ai
Gmail / Docs / Drive / Calendar), user plugins, hooks and ~/.claude/CLAUDE.md;
Codex loaded ~/.codex/config.toml's MCP servers and AGENTS.md and, in exp-57..60,
actually CALLED ruvnet-brain / ruflo tools ~240 times. exp-78 measured the cost of
that on Sonnet 5.5: tokens -43%, cost -39%, wall-clock -36% once isolated, with
coverage unchanged. So a run's host context is a factor, and past runs must carry
it. It is DERIVED here from each run's archived transcript — never hand-edited
into a retort.db or provenance.json.

Levels:
    mcp-cleared   verified clean: the run's provenance records the isolation args,
                  or its Claude init event lists zero MCP tools.
    mcp-enabled   MCP tools were loaded (Claude init event) or called (any agent).
                  A plugin prompt level's own server (msec-mcp) does not count:
                  it is the treatment, recorded in provenance's prompt_plugins.
    unverified    no evidence either way (no transcript, or a Codex run that made
                  no MCP calls — Codex logs do not list the servers it loaded).
    local-harness a local agent harness (Hermes, omp, opencode, ...) — it does not
                  read ~/.claude or ~/.codex, and ~/.hermes/config.yaml had no MCP
                  servers when checked (2026-09-30), so the host leak does not apply.
"""
from __future__ import annotations

import json
from pathlib import Path

from retort.playpen.prompt_plugins import TREATMENT_MCP_SERVERS

CLEARED, ENABLED, UNVERIFIED, LOCAL = "mcp-cleared", "mcp-enabled", "unverified", "local-harness"

#: Agents that inherit the host's Claude / Codex config. A NULL agent is claude-code
#: (runs from before the `agent` factor existed).
CLOUD_AGENTS = {None, "", "claude-code", "codex"}

#: Only the head of a transcript is needed for the Claude init event and the first
#: turn's usage; MCP calls are counted over the whole file line by line.
_HEAD_BYTES = 400_000

#: A plugin prompt level's own MCP tools (atdd-skill -> msec-mcp) are the
#: treatment, not host context, so they do not make a run `mcp-enabled`.
_TREATMENT_PREFIXES = tuple(f"mcp__{s}__" for s in TREATMENT_MCP_SERVERS)


def _is_host_mcp(name: str) -> bool:
    return name.startswith("mcp__") and not name.startswith(_TREATMENT_PREFIXES)


def run_archive_dir(exp_dir: Path, run_config: dict, replicate: int) -> Path | None:
    """The archived playpen for one run (mirrors ``_archive_run_workspace``)."""
    cell = "_".join(f"{k}={v}" for k, v in sorted(run_config.items()))
    for suffix in ("", "-failed"):
        d = exp_dir / "runs" / cell / f"rep{replicate}{suffix}"
        if d.is_dir():
            return d
    return None


def isolated_by_provenance(exp_dir: Path) -> bool:
    """True when the experiment's provenance records agent isolation args."""
    try:
        prov = json.loads((exp_dir / "provenance.json").read_text())
    except (OSError, ValueError):
        return False
    cfg = prov.get("agent_config") or {}
    return any(isinstance(v, dict) and v.get("isolation_args") for v in cfg.values())


def classify_transcript(stdout_log: Path) -> dict:
    """``{agent_context, mcp_tools_loaded, mcp_calls, first_turn_prompt_tokens}``."""
    out = {"agent_context": UNVERIFIED, "mcp_tools_loaded": None,
           "mcp_calls": None, "first_turn_prompt_tokens": None}
    try:
        fh = open(stdout_log, errors="replace")
    except OSError:
        return out
    calls = 0
    saw_codex = False
    with fh:
        for line in fh:
            if not line.startswith("{"):
                continue
            compact = line.replace(" ", "")
            if out["mcp_tools_loaded"] is None and '"subtype":"init"' in compact:
                try:
                    tools = json.loads(line).get("tools") or []
                    out["mcp_tools_loaded"] = sum(1 for t in tools if _is_host_mcp(str(t)))
                except ValueError:
                    pass
            elif out["first_turn_prompt_tokens"] is None and '"type":"assistant"' in compact:
                try:
                    u = json.loads(line)["message"]["usage"]
                    out["first_turn_prompt_tokens"] = (
                        u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                        + u.get("cache_read_input_tokens", 0))
                except (ValueError, KeyError, TypeError):
                    pass
            if '"thread.started"' in compact or '"turn.started"' in compact:
                saw_codex = True
            # Claude: an MCP tool_use block. Codex: a completed mcp_tool_call item.
            if '"type":"tool_use"' in compact and '"name":"mcp__' in compact:
                calls += compact.count('"name":"mcp__') - sum(
                    compact.count(f'"name":"{p}') for p in _TREATMENT_PREFIXES)
            elif '"item.completed"' in compact and '"mcp_tool_call"' in compact:
                calls += 1
    if out["mcp_tools_loaded"] is None and not saw_codex:
        return out  # no recognisable transcript
    out["mcp_calls"] = calls
    if calls or (out["mcp_tools_loaded"] or 0) > 0:
        out["agent_context"] = ENABLED
    elif out["mcp_tools_loaded"] == 0:
        out["agent_context"] = CLEARED
    return out


def agent_context_for(exp_dir: Path, run_config: dict, replicate: int) -> dict:
    """Classify one run: provenance isolation wins, else read its transcript."""
    if run_config.get("agent") not in CLOUD_AGENTS:
        return {"agent_context": LOCAL, "mcp_tools_loaded": None,
                "mcp_calls": None, "first_turn_prompt_tokens": None}
    d = run_archive_dir(exp_dir, run_config, replicate)
    res = classify_transcript(d / "_agent_stdout.log") if d else classify_transcript(Path("/nonexistent"))
    if isolated_by_provenance(exp_dir) and res["agent_context"] != ENABLED:
        res["agent_context"] = CLEARED
    return res
