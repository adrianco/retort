"""Prompt levels whose treatment is a Claude Code PLUGIN, not just prompt text.

The claude-code agent runs isolated from the host (see
``local_runner.CLAUDE_AGENT_ISOLATION_ARGS``): no user plugins, no MCP servers. A
prompt level like ``atdd-skill`` tells the agent to invoke Dave Farley's
``msec:atdd-build`` skill, which pulls the course lessons from an OAuth-protected
MCP server. Isolated, that level would load the prompt text but be unable to reach
the skill's content — measuring the words, not the method.

Probed 2026-10-01 (msec 0.6.0, Haiku 4.5): ``--plugin-dir`` alone loads the
plugin's skills but NOT the MCP server its manifest declares — ``--strict-mcp-config``
drops it — so ``list_catalog`` was simply missing. With the server named in
``--mcp-config`` as well, it answered ``caller_tier={"atdd-course":"paid"}``,
``disclosure=full``: the owner's OAuth token reaches the isolated agent.

So a plugin level adds back EXACTLY the plugin dir and the servers its own
manifest declares, nothing else from the host, and every other level stays as
isolated as before.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

#: prompt level -> installed plugin directory (the version is pinned in the path).
PROMPT_PLUGINS: dict[str, Path] = {
    "atdd-skill": Path.home() / ".claude/plugins/cache/cd-training/msec/0.6.0",
}

#: prompt level -> (MCP tool to probe, its args, regex the result must match).
#: The preflight fails the run unless the isolated agent's tool_result matches.
_PREFLIGHT: dict[str, tuple[str, dict, str]] = {
    "atdd-skill": ("mcp__msec-mcp__list_catalog",
                   {"source": "atdd-course", "limit": 1},
                   r'"caller_tier"\s*:\s*\{[^}]*"atdd-course"\s*:\s*"paid"'),
}

#: MCP servers that are a prompt level's TREATMENT, not a host leak. Hard-coded
#: (not read from the manifests) so classifying an archived run never depends on
#: the plugin still being installed. Keep in step with PROMPT_PLUGINS.
TREATMENT_MCP_SERVERS: frozenset[str] = frozenset({"msec-mcp"})

_EMPTY_MCP = '{"mcpServers":{}}'


def plugin_for(prompt_level: str | None) -> dict | None:
    """The plugin a prompt level adds back, read from its own manifest, or None.

    Raises FileNotFoundError when the level IS a plugin level but the plugin is
    not installed: running it anyway would silently measure the prompt text alone.
    """
    if not prompt_level or prompt_level not in PROMPT_PLUGINS:
        return None
    pdir = PROMPT_PLUGINS[prompt_level]
    manifest = pdir / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        raise FileNotFoundError(
            f"prompt level {prompt_level!r} needs the plugin at {pdir}, but {manifest} "
            "is missing. Install it (`/plugin install`) at that version, or update "
            "PROMPT_PLUGINS in retort/playpen/prompt_plugins.py."
        )
    m = json.loads(manifest.read_text())
    return {
        "plugin_dir": str(pdir),
        "name": m.get("name"),
        "version": m.get("version"),
        "git_commit": _installed_commit(pdir),
        "mcp_servers": m.get("mcpServers") or {},
    }


def _installed_commit(pdir: Path) -> str | None:
    """The marketplace commit the plugin was installed from (installed_plugins.json)."""
    reg = Path.home() / ".claude/plugins/installed_plugins.json"
    try:
        data = json.loads(reg.read_text())
    except (OSError, ValueError):
        return None
    for entries in (data.get("plugins", data) or {}).values():
        for e in entries if isinstance(entries, list) else []:
            if Path(e.get("installPath", "")) == pdir:
                return e.get("gitCommitSha")
    return None


def claude_isolation_args(prompt_level: str | None, base: tuple[str, ...]) -> list[str]:
    """``base`` isolation args, with a plugin level's plugin + MCP servers added back."""
    plugin = plugin_for(prompt_level)
    if plugin is None:
        return list(base)
    args = list(base)
    i = args.index("--mcp-config") + 1
    assert args[i] == _EMPTY_MCP, "isolation base must start from an empty mcp-config"
    args[i] = json.dumps({"mcpServers": plugin["mcp_servers"]}, separators=(",", ":"))
    return [*args, "--plugin-dir", plugin["plugin_dir"]]


def provenance(prompt_levels: list[str]) -> dict[str, dict]:
    """{prompt level -> plugin record} for the plugin levels a design runs."""
    return {lvl: plugin_for(lvl) for lvl in sorted(set(prompt_levels))
            if lvl in PROMPT_PLUGINS}


def preflight(prompt_level: str, base: tuple[str, ...],
              model: str = "claude-haiku-4-5-20251001",
              timeout: int = 180) -> tuple[bool, str]:
    """Prove an isolated agent can reach the plugin's MCP server at the right tier.

    Runs ONE short ``claude -p`` with exactly the args a cell will get, asks it to
    call the probe tool, and checks the raw tool_result — not the model's retelling.
    A billed call (a few cents on Haiku), but it is what stands between the grid
    and a run where every atdd-skill cell quietly lacked the course content.
    """
    tool, tool_args, pattern = _PREFLIGHT[prompt_level]
    prompt = (f"Call the tool {tool} with arguments {json.dumps(tool_args)} and "
              "reply with its raw result. Do nothing else.")
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--max-turns", "3", "--dangerously-skip-permissions", "--model", model,
           *claude_isolation_args(prompt_level, base)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=Path.home())
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"probe did not complete: {exc}"
    return check_probe_output(proc.stdout, tool, pattern)


def check_probe_output(stream: str, tool: str, pattern: str) -> tuple[bool, str]:
    """Judge a probe transcript: was ``tool`` loaded, called, and did it match?"""
    loaded, use_ids, results = False, set(), []
    for line in stream.splitlines():
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("subtype") == "init":
            loaded = tool in (ev.get("tools") or [])
        for block in ((ev.get("message") or {}).get("content") or []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == tool:
                use_ids.add(block.get("id"))
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in use_ids:
                results.append(json.dumps(block.get("content")))
    if not loaded:
        return False, f"{tool} was not loaded in the isolated agent"
    if not results:
        return False, f"{tool} was loaded but never returned a result"
    # tool_result content arrives JSON-encoded inside a string; unescape once.
    text = " ".join(results).replace('\\"', '"')
    if not re.search(pattern, text):
        return False, f"{tool} answered, but not at the required tier: {text[:300]}"
    return True, f"{tool} reachable at the required tier"
