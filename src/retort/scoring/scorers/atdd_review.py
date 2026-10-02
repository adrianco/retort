"""ATDD-conformance scorer — Dave Farley's own `msec:atdd-review` skill grades the tests.

exp-13's ATDD results were graded, if at all, by our reading of the method. This
scorer hands the finished workspace to the course's review skill instead, which
fetches its criteria live from the course MCP server (`msec-mcp`, paid tier) and
assesses seven categories:

    A spec quality · B 4-layer architecture · C isolation · D DSL quality ·
    E protocol drivers · F intermittency risks · G releasability truthfulness

Each is rated 0-4 by the reviewer; the score is the sum / 28. A workspace with no
acceptance tests at all scores 0.0 — a real result (the neutral arm usually has
none), not a missing one.

Honesty rules — the score is NULL (None), never a guess, when:
  * the reviewer never invoked `msec:atdd-review`, or never fetched course
    content (then it graded from its own idea of ATDD, which is what this
    scorer exists to replace);
  * the reply carries no parseable rating block, or the CLI failed/timed out.

The reviewer runs isolated exactly like the agent under test (no host MCP
servers, plugins or CLAUDE.md), with only the msec plugin + server added back,
on a COPY of the workspace so it cannot alter what later scorers measure. The
full review is kept beside the run as ``_atdd_review.md`` and the verdict cached
in ``_atdd_review.json`` (re-scoring is free; delete the file to re-review).

Opt-in via ``responses:`` — every uncached run costs one multi-turn review.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig

logger = logging.getLogger(__name__)

#: Fixed so every run in an experiment is graded by the same reviewer, and NOT
#: the model under test (exp-83 builds with Opus 5.5). Override: ATDD_REVIEW_MODEL.
DEFAULT_REVIEW_MODEL = "claude-opus-4-8"
CATEGORIES = ("A", "B", "C", "D", "E", "F", "G")
_MAX_PER_CATEGORY = 4
#: The plugin level whose plugin + MCP server the reviewer gets.
_PLUGIN_LEVEL = "atdd-skill"
_SKILL = "msec:atdd-review"
_COPY_IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "venv", "node_modules", "target", "dist", "build",
    "__pycache__", ".pytest_cache", ".mypy_cache", "*.pyc")

_PROMPT = f"""Invoke the `{_SKILL}` skill with the Skill tool, with the arguments \
"Review every acceptance and end-to-end test in the current directory against Dave \
Farley's ATDD principles". Follow its review approach in full: read the code, fetch \
the course topics it names for EVERY category A-G before assessing that category, \
then write the review. This is a non-interactive run with no user present: do not \
ask questions, do not offer follow-ups, do not modify any file.

After the review, end your reply with exactly one fenced ```json block, nothing \
after it, of this shape:
{{"acceptance_tests_found": true|false, "ratings": {{"A": n, "B": n, "C": n, "D": n, \
"E": n, "F": n, "G": n}}, "disclosure": "full"|"summary_only"}}
Each n is an integer 0-4 for that category: 0 absent or fundamentally wrong, \
1 poor, 2 partial, 3 good, 4 exemplary of Dave's principle. If there are no \
acceptance or end-to-end tests at all, set acceptance_tests_found false and every \
rating 0. "disclosure" is what the course server returned (full lessons, or \
summaries only)."""


class AtddReviewScorer:
    """Score 0-1 from `msec:atdd-review`'s A-G ratings; None when unmeasured."""

    def __init__(self, *, model: str | None = None, timeout_seconds: int = 1200) -> None:
        self.model = model or os.environ.get("ATDD_REVIEW_MODEL", DEFAULT_REVIEW_MODEL)
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "atdd_review"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float | None:
        out = artifacts.output_dir
        if out is None or not out.exists():
            return None
        cache = out / "_atdd_review.json"
        try:
            cached = json.loads(cache.read_text())
            if cached.get("score") is not None:
                return float(cached["score"])
        except (OSError, ValueError, TypeError):
            pass

        stream = self._review(out)
        if stream is None:
            return None
        verdict = parse_review(stream)
        verdict["model"] = self.model
        (out / "_atdd_review.md").write_text(verdict.pop("review_text", "") or "")
        cache.write_text(json.dumps(verdict, indent=2, sort_keys=True))
        if verdict["score"] is None:
            logger.warning("atdd_review unmeasured for %s: %s", out, verdict.get("note"))
        return verdict["score"]

    def _review(self, workspace: Path) -> str | None:
        from retort.playpen.local_runner import CLAUDE_AGENT_ISOLATION_ARGS
        from retort.playpen.prompt_plugins import claude_isolation_args

        try:
            iso = claude_isolation_args(_PLUGIN_LEVEL, CLAUDE_AGENT_ISOLATION_ARGS)
        except FileNotFoundError as exc:
            logger.warning("atdd_review: %s", exc)
            return None
        with tempfile.TemporaryDirectory(prefix="atdd-review-",
                                         dir=Path.home() / ".retort") as tmp:
            # Under ~/.retort, never /var: macOS refuses the agent's file tool
            # under the system temp dir (the false-zero playpen bug).
            copy = Path(tmp) / "workspace"
            shutil.copytree(workspace, copy, ignore=_COPY_IGNORE, symlinks=True)
            cmd = ["claude", "-p", _PROMPT, "--output-format", "stream-json", "--verbose",
                   "--max-turns", "80", "--dangerously-skip-permissions",
                   "--model", self.model, *iso]
            try:
                proc = subprocess.run(cmd, cwd=copy, capture_output=True, text=True,
                                      timeout=self.timeout_seconds)
            except (OSError, subprocess.TimeoutExpired) as exc:
                logger.warning("atdd_review: reviewer did not complete: %s", exc)
                return None
        return proc.stdout


_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_review(stream: str) -> dict:
    """Turn the reviewer's stream-json transcript into a verdict dict.

    Keys: score (float|None), ratings, acceptance_tests_found, disclosure,
    skill_invoked, course_fetches, note, review_text.
    """
    v: dict = {"score": None, "ratings": None, "acceptance_tests_found": None,
               "disclosure": None, "skill_invoked": False, "course_fetches": 0,
               "note": None, "review_text": ""}
    for line in stream.splitlines():
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            v["review_text"] = ev.get("result") or ""
        for b in (ev.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            if b.get("name") == "Skill" and (b.get("input") or {}).get("skill") == _SKILL:
                v["skill_invoked"] = True
            elif str(b.get("name", "")).startswith("mcp__msec-mcp__"):
                v["course_fetches"] += 1
    if not v["skill_invoked"]:
        v["note"] = f"reviewer never invoked {_SKILL}"
        return v
    if not v["course_fetches"]:
        v["note"] = "reviewer fetched no course content"
        return v
    blocks = _JSON_BLOCK_RE.findall(v["review_text"])
    try:
        block = json.loads(blocks[-1])
        ratings = {c: int(block["ratings"][c]) for c in CATEGORIES}
    except (IndexError, ValueError, KeyError, TypeError):
        v["note"] = "no parseable ratings block in the review"
        return v
    if any(not 0 <= r <= _MAX_PER_CATEGORY for r in ratings.values()):
        v["note"] = f"rating out of range: {ratings}"
        return v
    v["ratings"] = ratings
    v["acceptance_tests_found"] = bool(block.get("acceptance_tests_found"))
    v["disclosure"] = block.get("disclosure")
    v["score"] = round(sum(ratings.values()) / (_MAX_PER_CATEGORY * len(CATEGORIES)), 4)
    return v
