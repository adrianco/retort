"""Ask a REAL MCP client the golden questions, instead of parsing the answer.

`factual_accuracy` speaks raw JSON-RPC to the produced server, reads
`content[0].text`, and parses it. MCP deliberately leaves that text free-form, so
parsing means guessing at shape — and every false failure this project has
recorded on brazil-bench lived in the guessing, not in the servers:

  * a nested `{"record": {...}}` read as a missing W/D/L figure;
  * a competition candidate list with `Brasileirao` but not `Brasileirão`, so
    every filtered call missed and the fallback returned Série A and Série B
    merged;
  * a 40-row table graded as a wrong 20-row one.

This scorer removes the guessing by handing the server to Claude Code as a
genuine MCP client and asking it the same golden questions in a prompt. The
client discovers the tools, picks one, and synthesizes its own arguments — which
is both what a real consumer does and the exact step that produced the
`Brasileirão` bug. Observed doing it: the client tried
`{"competition": "Brasileirao Serie A"}`, got nothing, and retried
`{"competition": "Série A"}` unprompted.

THE CONFOUND, AND THE GUARD. The 2019 Série A table is famous — Flamengo's 90
points is in every frontier model's training data — so a judge can answer
correctly while the server sits broken and unused. The prompt saying "use the
server" is not evidence that it did. So the verdict is computed from the
TRANSCRIPT, not from the prose: `--output-format stream-json` reports every
`tool_use` block, and a run whose transcript contains no `mcp__<server>__*` call
scores 0.0 with that stated as the reason. Do not relax this into trusting a
self-reported tool name — a model that answered from memory will happily name a
tool it never called.

LENIENT BY CONSTRUCTION — WHICH IS WHY IT DOES NOT REPLACE ANYTHING. A capable
client compensates for a broken server. Against exp-60's rust cell, whose
`standings` tool a real client REJECTS outright (top-level array as
`structuredContent`), this returns the fully correct answer anyway by routing
around to `team_record`. That is faithful to how the server would really be
used, and it is useless as a well-formedness check. `mcp_conformance` is the
column with teeth there; this one measures whether the data is right and
reachable. Run both.

Reported alongside `factual_accuracy` rather than replacing it, so the four
experiments already scored by the parser keep their meaning and the two can be
compared on the same runs.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring import probe_status
from retort.scoring.scorers import runtime as rt

#: Judge for this column. Held fixed like every other judge here — a moving
#: judge silently redefines the response variable.
DEFAULT_JUDGE_MODEL = "claude-opus-4-8"

#: The MCP server name the config registers, hence the tool prefix to look for.
SERVER_NAME = "brazil"

#: Seconds for the whole client session. It is one prompt with a handful of tool
#: calls; longer than this means the server is not answering.
CLIENT_TIMEOUT_S = 300

PROMPT = """Use the `brazil` MCP server's tools to look up the final league table for the 2019 Brasileirao Serie A (Campeonato Brasileiro Serie A).

Report ONLY what the server returns. Do not use your own knowledge of Brazilian football — if the server's numbers disagree with what you remember, report the SERVER's numbers. If the server cannot answer, say so rather than filling in the gap.

Reply with ONLY this JSON object and nothing else:
{"played": <matches Flamengo played that season, per the server>, "points": <Flamengo's points, per the server>, "clubs": <how many distinct clubs are in that season's table, per the server>, "tool": "<the tool you got this from>"}

If the server could not give you a figure, use null for it."""

#: 2019 Série A: a 20-team double round-robin, so every club played 38, and
#: Flamengo won on 90 points. All three are stated in the task's own worked
#: example, so this tests the spec as written rather than adding a requirement.
GOLDEN = {"played": 38, "points": 90, "clubs": 20}


@dataclass
class ClientFactsResult:
    ok: bool = False
    score: float = 0.0
    note: str = ""
    #: Every MCP tool call seen in the transcript. The evidence that the server
    #: was actually used, rather than the model's memory.
    tool_calls: list[dict] = field(default_factory=list)
    answer: dict = field(default_factory=dict)
    raw: str = ""
    assertions: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "score": self.score, "note": self.note,
                "tool_calls": self.tool_calls, "answer": self.answer,
                "raw": self.raw, "assertions": self.assertions}


def _mcp_config(cmd: list[str]) -> str:
    """A Claude Code MCP config for the produced server.

    No `cwd` key: it is not honoured, and a server that cannot find its `data/`
    directory starts and then fails to connect — which reads identically to a
    broken program. The client is launched WITH cwd=run_dir instead.
    """
    return json.dumps({"mcpServers": {SERVER_NAME: {
        "type": "stdio", "command": cmd[0], "args": list(cmd[1:])}}})


def _tool_calls_of(stream: str, prefix: str) -> list[dict]:
    """Every MCP tool_use block in the transcript, with its arguments."""
    out: list[dict] = []
    for line in stream.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        for blk in (ev.get("message", {}) or {}).get("content", []) or []:
            if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                continue
            name = blk.get("name", "")
            if name.startswith(prefix):
                out.append({"tool": name, "args": blk.get("input")})
    return out


def _final_text(stream: str) -> str:
    """The last assistant text in the transcript."""
    text = ""
    for line in stream.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result" and isinstance(ev.get("result"), str):
            text = ev["result"]
            continue
        for blk in (ev.get("message", {}) or {}).get("content", []) or []:
            if isinstance(blk, dict) and blk.get("type") == "text":
                text = blk.get("text", "") or text
    return text


def _verdict_of(text: str) -> dict | None:
    """The JSON object the judge was asked for, wherever it sits in the reply."""
    for candidate in re.findall(r"\{[^{}]*\}", text or ""):
        try:
            obj = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(obj, dict) and any(k in obj for k in GOLDEN):
            return obj
    return None


def measure(run_dir: Path, language: str,
            model: str = DEFAULT_JUDGE_MODEL) -> ClientFactsResult:
    """Register the produced server with a real client and ask it the questions."""
    res = ClientFactsResult()
    cmd, why = rt._build_then_entry(run_dir, language)
    if cmd is None:
        res.note = why or "no runnable entrypoint"
        return res

    run_dir = run_dir.resolve()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write(_mcp_config(cmd))
        cfg = fh.name
    try:
        proc = subprocess.run(
            ["claude", "-p", PROMPT,
             "--mcp-config", cfg,
             # Without this the judge inherits whatever MCP servers happen to be
             # configured on the run host, and the measurement stops being a
             # property of the produced server.
             "--strict-mcp-config",
             "--model", model,
             "--output-format", "stream-json", "--verbose",
             "--dangerously-skip-permissions"],
            cwd=run_dir, capture_output=True, text=True,
            timeout=CLIENT_TIMEOUT_S, stdin=subprocess.DEVNULL, check=False)
    except FileNotFoundError:
        res.note = "claude CLI not found on PATH"
        return res
    except subprocess.TimeoutExpired:
        res.note = f"MCP client session timed out after {CLIENT_TIMEOUT_S}s"
        return res
    finally:
        try:
            os.unlink(cfg)
        except OSError:
            pass

    stream = proc.stdout or ""
    res.tool_calls = _tool_calls_of(stream, f"mcp__{SERVER_NAME}__")
    res.raw = _final_text(stream)[:4000]

    # THE GUARD. An answer produced without touching the server is the model's
    # memory of a famous league table, not a measurement of this artifact.
    if not res.tool_calls:
        res.note = ("the client answered without calling a single MCP tool — "
                    "the server never served, so this is not a measurement of it")
        return res

    answer = _verdict_of(res.raw)
    if answer is None:
        res.note = "the client returned no parseable verdict"
        return res
    res.answer = answer

    hits = 0
    for key, want in GOLDEN.items():
        got = answer.get(key)
        passed = isinstance(got, (int, float)) and int(got) == want
        hits += bool(passed)
        res.assertions.append({"name": key, "expected": want, "actual": got,
                               "passed": bool(passed)})
    res.score = hits / len(GOLDEN)
    res.ok = hits == len(GOLDEN)
    if not res.ok:
        res.note = "; ".join(
            f"{a['name']}: expected {a['expected']}, server said {a['actual']}"
            for a in res.assertions if not a["passed"])
    return res


class McpClientFactsScorer:
    """Golden answers as read by a real MCP client, not by a hand-written parser.

    Returns 0.0 rather than None for a server that will not start or will not
    serve — same reasoning as `factual_accuracy`. Does NOT gate: it is a new
    column reported beside the parser-based one so the two can be compared on
    the same runs.
    """

    @property
    def name(self) -> str:
        return "mcp_client_facts"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("MCP_CLIENT_JUDGE_MODEL",
                                             DEFAULT_JUDGE_MODEL)

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if artifacts.output_dir is None:
            return 0.0
        run_dir = Path(artifacts.output_dir)
        if rt.detect_task(run_dir) != "brazil-soccer-mcp":
            return 1.0            # N/A for other tasks
        with probe_status.announcing(f"asking an MCP client ({stack.language})",
                                     stack.language):
            result = measure(run_dir, stack.language, self.model)
        try:
            (run_dir / "_mcp_client_facts.json").write_text(
                json.dumps(result.as_dict(), indent=1))
        except OSError:
            pass
        return result.score
