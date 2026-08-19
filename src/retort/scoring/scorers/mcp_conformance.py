"""Would a REAL MCP client accept this server's responses?

The other probes here speak JSON-RPC to the produced server and then read
`content[0].text` — which is exactly what a hand-written integration test does,
and exactly what a real client does not. MCP leaves the *text* of a tool result
free-form, so reading it means guessing at shape, and every false failure this
project has recorded on brazil-bench came from that guessing: a nested `record`
object read as a missing figure, an unaccented competition name, a 40-row table
graded as a wrong 20-row one.

The protocol itself is not free-form, and that part can be checked exactly.
`structuredContent`, `outputSchema`, the content-block envelope and the tool
descriptors all have shapes the spec pins down, and a client enforces them. This
scorer asks the question the text-reading probes cannot: **would a real client
accept this?**

WHAT IT FOUND IMMEDIATELY. exp-60's rust cell scores 1.00 on `factual_accuracy`
— correct 2019 table, all 20 clubs, Flamengo 38 played and 90 points. Registered
with Claude Code as a genuine MCP client, two of its six tools are *rejected*:
`standings` and `search_matches` return a top-level JSON array as
`structuredContent`, where the spec requires an object. Confirmed on the wire.
They also emit `structuredContent` while declaring no `outputSchema` at all.
125 archived runs emit that field, so this is a real dimension of the corpus
that nothing has ever measured.

WHY THIS IS SEPARATE FROM ASKING AN LLM. Pointing a capable client at the same
server and asking it the golden questions gets the RIGHT ANSWER anyway: it
silently routes around the two broken tools to `team_record` and reports 38
played, 90 points, 20 clubs. A competent client compensates for a broken server,
so a prompt-driven check is *more lenient* than this one, not stricter. The
teeth are in the conformance validation, not in the prompt. Keep both.

SCORED, NOT GATED — for now. `factual_accuracy` gates because a wrong answer is
unambiguously a failed deliverable. Conformance is a new measurement over a
corpus whose base rate is unknown, and turning it into a gate before the sweep
would retroactively fail runs on a dimension they were never measured against.
Measure first, then decide with the numbers — the same order in which the
factual gate itself was introduced.

SEVERITY IS EVIDENCE, NOT TASTE. The first version scored every check as one
flat proportion, and the archive sweep immediately showed why that is wrong: 16
runs trip "emits structuredContent without declaring an outputSchema" while only
2 return a non-object `structuredContent`. Flat scoring buries the two failures
that break clients under sixteen that do not. The score is now computed from HARD
checks only — a real client rejecting the tool, or a server breaking a contract
it declared itself — and advisories are reported and counted separately. The
evidence for the split is direct: when Claude Code refused rust's tools it named
the non-object `structuredContent` specifically and said nothing about the
missing schema.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring import probe_status
from retort.scoring.scorers import runtime as rt

#: Content-block types the spec defines for a tool result.
_CONTENT_TYPES = {"text", "image", "audio", "resource", "resource_link"}


#: Checks are not equally severe, and scoring them as one flat proportion buries
#: the ones that actually break a client. Measured across the archive sweep: 16
#: runs trip "emits structuredContent without declaring an outputSchema" while
#: only 2 return a non-object structuredContent — and when Claude Code refused
#: rust's tools it named the NON-OBJECT problem specifically and said nothing
#: about the missing schema. Severity is evidence, not taste.
#:
#:   "hard"     a real client rejects the tool, or the server breaks a contract
#:              it declared itself. This is what may ever be allowed to gate.
#:   "advisory" unusual or unhelpful, but no client observed refusing it.
HARD, ADVISORY = "hard", "advisory"


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""
    tool: str = ""
    severity: str = HARD

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed,
                "detail": self.detail, "tool": self.tool,
                "severity": self.severity}


@dataclass
class ConformanceResult:
    ok: bool = False
    score: float = 0.0
    note: str = ""
    tools: int = 0
    #: Counted separately so the two never blur: a hard failure is a client
    #: rejecting the tool; an advisory is a style finding worth reporting.
    hard_failures: int = 0
    advisories: int = 0
    checks: list[Check] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "score": self.score, "note": self.note,
                "tools": self.tools, "hard_failures": self.hard_failures,
                "advisories": self.advisories,
                "checks": [c.as_dict() for c in self.checks]}

    def add(self, name: str, passed: bool, detail: str = "", tool: str = "",
            severity: str = HARD) -> None:
        self.checks.append(Check(name, passed, detail, tool, severity))


def _is_schema_object(schema: object) -> tuple[bool, str]:
    """Is this a usable JSON Schema for tool arguments?

    A client builds the tool's argument form from this. It does not have to
    declare properties — a no-argument tool legitimately has none — but it must
    be an object, and `required`/`properties` must have the right shapes or a
    client cannot render or validate a call.
    """
    if not isinstance(schema, dict):
        return False, f"inputSchema is {type(schema).__name__}, not an object"
    props = schema.get("properties")
    if props is not None and not isinstance(props, dict):
        return False, f"properties is {type(props).__name__}, not an object"
    req = schema.get("required")
    if req is not None:
        if not isinstance(req, list) or not all(isinstance(r, str) for r in req):
            return False, "required is not a list of strings"
        if isinstance(props, dict):
            missing = [r for r in req if r not in props]
            if missing:
                return False, f"required names absent from properties: {missing}"
    return True, ""


def _check_result_envelope(res: ConformanceResult, tool: dict, msg: dict) -> None:
    """The `tools/call` reply, judged the way a client judges it."""
    name = tool.get("name", "")
    result = msg.get("result")
    if not isinstance(result, dict):
        res.add("result is an object", False,
                f"result is {type(result).__name__}", name)
        return
    res.add("result is an object", True, tool=name)

    content = result.get("content")
    if not isinstance(content, list):
        res.add("content is a list", False,
                f"content is {type(content).__name__}", name)
    else:
        res.add("content is a list", True, tool=name)
        bad = [b for b in content
               if not isinstance(b, dict) or b.get("type") not in _CONTENT_TYPES]
        res.add("content blocks are well typed", not bad,
                f"{len(bad)} block(s) with a missing or unknown type" if bad else "",
                name)

    # structuredContent is a RECORD. This is the check that fails a server every
    # other probe here calls perfect: a top-level array is the natural thing to
    # return for a league table, and a real client refuses it.
    if "structuredContent" in result:
        sc = result["structuredContent"]
        ok = isinstance(sc, dict)
        res.add("structuredContent is an object", ok,
                "" if ok else
                f"structuredContent is a {type(sc).__name__}; the spec requires "
                "an object, so a real client rejects this tool outright",
                name)
        # Emitting it without declaring an outputSchema leaves a client no way
        # to know what it is looking at. Not fatal, but it is not conformant use.
        res.add("structuredContent has a declared outputSchema",
                "outputSchema" in tool,
                "" if "outputSchema" in tool else
                "returns structuredContent but declares no outputSchema",
                name, ADVISORY)
    elif "outputSchema" in tool:
        res.add("declared outputSchema is honoured", False,
                "declares an outputSchema but returned no structuredContent",
                name)


def measure(run_dir: Path, language: str,
            budget_s: float = 120.0) -> ConformanceResult:
    """Drive the server and judge its replies against the protocol."""
    budget = rt._Budget(budget_s)
    res = ConformanceResult()
    cmd, why = rt._build_then_entry(run_dir, language)
    if cmd is None:
        res.note = why or "no runnable entrypoint"
        return res

    errf = rt._stderr_file()
    try:
        proc = rt._spawn(cmd, run_dir.resolve(), errf)
    except (FileNotFoundError, OSError) as exc:
        res.note = f"could not start: {exc}"
        errf.close()
        return res

    try:
        listed = rt._mcp_handshake(proc, budget.slice(rt.ITER_TIMEOUT_S))
        if listed is None:
            res.note = rt._stderr_tail(errf) or "did not complete the MCP handshake"
            return res
        res.add("completes the MCP handshake", True)

        tools = (listed.get("result") or {}).get("tools") or []
        res.tools = len(tools)
        if not tools:
            res.note = "server advertises no tools"
            res.add("advertises at least one tool", False)
            return res
        res.add("advertises at least one tool", True)

        rid = 100
        for tool in tools:
            name = tool.get("name", "")
            res.add("tool has a name", bool(name), tool=name)
            good, detail = _is_schema_object(tool.get("inputSchema"))
            res.add("inputSchema is a usable JSON Schema", good, detail, name)
            if budget.spent():
                break
            # Call it the way a client would: arguments synthesized from the
            # tool's OWN schema, so a server is never judged on a call it did
            # not advertise.
            rid += 1
            args = rt._synthesize_args(tool.get("inputSchema", {}) or {})
            if not rt.mcp_send(proc, {"jsonrpc": "2.0", "id": rid,
                                      "method": "tools/call",
                                      "params": {"name": name, "arguments": args}}):
                res.add("answers tools/call", False, "server closed the pipe", name)
                break
            msg = rt.mcp_await_id(proc, rid, budget.slice(rt.QUERY_TIMEOUT_S))
            if msg is None:
                res.add("answers tools/call", False, "no reply", name)
                continue
            res.add("answers tools/call", True, tool=name)
            if "error" in msg:
                # A JSON-RPC error to synthesized arguments is legitimate — the
                # arguments may simply be wrong. It is not a conformance defect.
                continue
            _check_result_envelope(res, tool, msg)
    finally:
        errf.close()
        rt._reap(proc)

    if res.checks:
        hard = [c for c in res.checks if c.severity == HARD]
        # The SCORE is the hard checks only. An advisory finding is reported and
        # counted, never priced into the number a experiment reads — otherwise a
        # server that no client would refuse scores lower than one that three
        # clients reject, purely on volume.
        res.score = (sum(1 for c in hard if c.passed) / len(hard)) if hard else 1.0
        res.hard_failures = sum(1 for c in hard if not c.passed)
        res.advisories = sum(1 for c in res.checks
                             if c.severity == ADVISORY and not c.passed)
        res.ok = res.hard_failures == 0
        failed = [c for c in res.checks if not c.passed]
        if failed:
            res.note = "; ".join(
                f"{c.tool + ': ' if c.tool else ''}[{c.severity}] {c.name} — {c.detail}"
                for c in failed[:4])
    return res


class McpConformanceScorer:
    """Fraction of protocol checks a real client would accept.

    Returns 0.0 rather than None for a server that will not start — same
    reasoning as `factual_accuracy`: an artifact that does not run is a failed
    deliverable, not an unmeasurable one. Does NOT participate in the gate; see
    the module docstring.
    """

    @property
    def name(self) -> str:
        return "mcp_conformance"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if artifacts.output_dir is None:
            return 0.0
        run_dir = Path(artifacts.output_dir)
        if rt.detect_task(run_dir) != "brazil-soccer-mcp":
            return 1.0            # N/A for other tasks
        with probe_status.announcing(f"checking MCP conformance ({stack.language})",
                                     stack.language):
            result = measure(run_dir, stack.language)
        try:
            (run_dir / "_mcp_conformance.json").write_text(
                json.dumps(result.as_dict(), indent=1))
        except OSError:
            pass
        return result.score
