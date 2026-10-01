"""A plugin prompt level adds back exactly its plugin + manifest MCP servers."""
import json
from pathlib import Path

import pytest

from retort.analysis.agent_context import ENABLED, CLEARED, classify_transcript
from retort.playpen.runner import StackConfig, TaskSpec
from retort.playpen import prompt_plugins as pp
from retort.playpen.local_runner import CLAUDE_AGENT_ISOLATION_ARGS, LocalRunner

_SERVERS = {"msec-mcp": {"type": "http", "url": "https://msec.example/mcp"}}


@pytest.fixture
def fake_plugin(tmp_path, monkeypatch):
    pdir = tmp_path / "msec" / "0.6.0"
    (pdir / ".claude-plugin").mkdir(parents=True)
    (pdir / ".claude-plugin" / "plugin.json").write_text(json.dumps(
        {"name": "msec", "version": "0.6.0", "mcpServers": _SERVERS}))
    monkeypatch.setitem(pp.PROMPT_PLUGINS, "atdd-skill", pdir)
    return pdir


def _cmd(prompt_level, prompts_dir):
    (prompts_dir / f"{prompt_level}.md").write_text("Use the skill.")
    runner = LocalRunner(prompts_dir=prompts_dir)
    stack = StackConfig(language="python", agent="claude-code", framework="none",
                        extra={"model": "claude-opus-5-5", "prompt": prompt_level})
    return runner._build_agent_command(stack, TaskSpec(name="t", description="d", prompt="p"),
                                       Path("/tmp"))


def test_plugin_level_adds_plugin_dir_and_manifest_servers(fake_plugin, tmp_path):
    cmd = _cmd("atdd-skill", tmp_path)
    assert cmd[cmd.index("--plugin-dir") + 1] == str(fake_plugin)
    assert json.loads(cmd[cmd.index("--mcp-config") + 1]) == {"mcpServers": _SERVERS}
    # Still isolated from everything else on the host.
    assert "--strict-mcp-config" in cmd
    assert cmd[cmd.index("--setting-sources") + 1] == "project,local"
    assert cmd.count("--mcp-config") == 1


def test_other_levels_stay_fully_isolated(fake_plugin, tmp_path):
    cmd = _cmd("neutral", tmp_path)
    assert "--plugin-dir" not in cmd
    assert cmd[cmd.index("--mcp-config") + 1] == '{"mcpServers":{}}'


def test_missing_plugin_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.setitem(pp.PROMPT_PLUGINS, "atdd-skill", tmp_path / "absent")
    with pytest.raises(FileNotFoundError, match="atdd-skill"):
        pp.claude_isolation_args("atdd-skill", CLAUDE_AGENT_ISOLATION_ARGS)


def test_provenance_records_only_plugin_levels(fake_plugin):
    rec = pp.provenance(["neutral", "atdd-skill"])
    assert list(rec) == ["atdd-skill"]
    assert rec["atdd-skill"]["version"] == "0.6.0"
    assert rec["atdd-skill"]["mcp_servers"] == _SERVERS


_TOOL = "mcp__msec-mcp__list_catalog"
_PAID = r'"caller_tier"\s*:\s*\{[^}]*"atdd-course"\s*:\s*"paid"'


def _stream(tools, result_text=None):
    lines = [json.dumps({"type": "system", "subtype": "init", "tools": tools})]
    if result_text is not None:
        lines.append(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": _TOOL, "input": {}}]}}))
        lines.append(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1",
             "content": [{"type": "text", "text": result_text}]}]}}))
    return "\n".join(lines)


def test_probe_passes_on_paid_tier():
    ok, _ = pp.check_probe_output(
        _stream([_TOOL], '{"caller_tier":{"atdd-course":"paid"},"disclosure":"full"}'),
        _TOOL, _PAID)
    assert ok


@pytest.mark.parametrize("stream,why", [
    (_stream([]), "not loaded"),
    (_stream([_TOOL]), "never returned"),
    (_stream([_TOOL], '{"caller_tier":{"atdd-course":"free"}}'), "required tier"),
])
def test_probe_fails_when_unreachable_or_wrong_tier(stream, why):
    ok, msg = pp.check_probe_output(stream, _TOOL, _PAID)
    assert not ok and why in msg


def test_treatment_mcp_is_not_a_host_leak(tmp_path):
    log = tmp_path / "_agent_stdout.log"
    log.write_text(_stream(["Bash", _TOOL], '{"caller_tier":{}}') + "\n")
    assert classify_transcript(log)["agent_context"] == CLEARED
    log.write_text(_stream(["Bash", _TOOL, "mcp__gmail__send"]) + "\n")
    assert classify_transcript(log)["agent_context"] == ENABLED
