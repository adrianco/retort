"""atdd_review: Dave's review skill grades the tests; unmeasured is NULL, never a guess."""
import json
import subprocess

import pytest

from retort.playpen import prompt_plugins as pp
from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring.registry import create_default_registry
from retort.scoring.scorers import atdd_review as ar

_ALL3 = {c: 3 for c in ar.CATEGORIES}


def _stream(*, skill=True, fetches=2, block=None, extra_text="Overall assessment ..."):
    content = []
    if skill:
        content.append({"type": "tool_use", "id": "s", "name": "Skill",
                        "input": {"skill": "msec:atdd-review", "args": "x"}})
    content += [{"type": "tool_use", "id": f"m{i}", "name": "mcp__msec-mcp__find_by_topic",
                 "input": {"topic": "bdd"}} for i in range(fetches)]
    result = extra_text
    if block is not None:
        result += "\n```json\n" + json.dumps(block) + "\n```"
    return "\n".join([json.dumps({"type": "assistant", "message": {"content": content}}),
                      json.dumps({"type": "result", "result": result})])


def test_score_is_sum_of_ratings_over_28():
    v = ar.parse_review(_stream(block={"acceptance_tests_found": True, "ratings": _ALL3,
                                       "disclosure": "full"}))
    assert v["score"] == pytest.approx(21 / 28, abs=1e-4)
    assert v["skill_invoked"] and v["course_fetches"] == 2 and v["disclosure"] == "full"


def test_no_acceptance_tests_is_a_real_zero():
    v = ar.parse_review(_stream(block={"acceptance_tests_found": False,
                                       "ratings": {c: 0 for c in ar.CATEGORIES}}))
    assert v["score"] == 0.0 and v["acceptance_tests_found"] is False


@pytest.mark.parametrize("kw,why", [
    ({"skill": False, "block": {"ratings": _ALL3}}, "never invoked"),
    ({"fetches": 0, "block": {"ratings": _ALL3}}, "no course content"),
    ({"block": None}, "no parseable"),
    ({"block": {"ratings": {**_ALL3, "G": 7}}}, "out of range"),
    ({"block": {"ratings": {"A": 3}}}, "no parseable"),
])
def test_unmeasured_reviews_score_none(kw, why):
    v = ar.parse_review(_stream(**kw))
    assert v["score"] is None and why in v["note"]


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    pdir = tmp_path / "plugin"
    (pdir / ".claude-plugin").mkdir(parents=True)
    (pdir / ".claude-plugin" / "plugin.json").write_text(json.dumps(
        {"name": "msec", "version": "0.6.0",
         "mcpServers": {"msec-mcp": {"type": "http", "url": "https://x/mcp"}}}))
    monkeypatch.setitem(pp.PROMPT_PLUGINS, "atdd-skill", pdir)
    return pdir


def test_scorer_reviews_a_copy_isolated_with_the_plugin_and_caches(tmp_path, plugin, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "test_app.py").write_text("def test_x(): pass\n")
    (ws / "node_modules").mkdir()
    calls = []

    def fake_run(cmd, cwd=None, **kw):
        calls.append((cmd, cwd))
        assert cwd != ws and (cwd / "test_app.py").exists()        # a copy
        assert not (cwd / "node_modules").exists()                  # minus noise
        (cwd / "test_app.py").write_text("tampered")                 # cannot reach ws
        return subprocess.CompletedProcess(cmd, 0, _stream(
            block={"acceptance_tests_found": True, "ratings": _ALL3, "disclosure": "full"}), "")

    monkeypatch.setattr(ar.subprocess, "run", fake_run)
    monkeypatch.setattr(ar.Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / ".retort").mkdir()
    scorer = ar.AtddReviewScorer(model="claude-opus-4-8")
    art = RunArtifacts(output_dir=ws)
    stack = StackConfig(language="python", agent="claude-code", framework="none")

    assert scorer.score(art, stack) == pytest.approx(0.75)
    cmd = calls[0][0]
    assert cmd[cmd.index("--plugin-dir") + 1] == str(plugin)
    assert "msec-mcp" in cmd[cmd.index("--mcp-config") + 1]
    assert cmd[cmd.index("--setting-sources") + 1] == "project,local"
    assert cmd[cmd.index("--model") + 1] == "claude-opus-4-8"
    assert (ws / "test_app.py").read_text() == "def test_x(): pass\n"
    assert (ws / "_atdd_review.md").read_text().startswith("Overall")
    assert json.loads((ws / "_atdd_review.json").read_text())["ratings"] == _ALL3

    assert scorer.score(art, stack) == pytest.approx(0.75)        # cached: no 2nd review
    assert len(calls) == 1


def test_missing_plugin_is_unmeasured_not_zero(tmp_path, monkeypatch):
    monkeypatch.setitem(pp.PROMPT_PLUGINS, "atdd-skill", tmp_path / "absent")
    ws = tmp_path / "ws"
    ws.mkdir()
    assert ar.AtddReviewScorer().score(
        RunArtifacts(output_dir=ws),
        StackConfig(language="python", agent="claude-code", framework="none")) is None


def test_registered():
    assert "atdd_review" in create_default_registry()
