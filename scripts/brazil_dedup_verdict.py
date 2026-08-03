#!/usr/bin/env python3
"""Did each brazil implementation deduplicate the overlapping datasets?

WHY THIS IS A FAIR TEST, NOT AN EXTRA REQUIREMENT. The five match files overlap
on purpose — the same fixture appears in 2-3 of them — so "compute the 2019
standings" cannot be answered correctly without merging them. Dedup is an
implicit part of the task, and the pinned checklist never asks for it: a run that
double-counts every fixture still scores 12/12 because the capability exists.

THE PROBE. Every implementation must expose season standings (spec capability
R9). A Brasileirão Série A season is a 20-team double round-robin, so **every
club plays exactly 38 matches**, and 2019 has a widely-known result: Flamengo
champions on 90 points. So:

    played == 38   -> merged the overlap correctly
    played  > 38   -> double-counted (usually ~76 = exactly twice)
    played  < 38   -> dropped data

That is an externally verifiable fact, not a re-implementation of the task, which
is what makes it usable as a golden answer.

Scores are NOT adjusted by this. It records how often implementations got it
right, which is the input to deciding whether the checklist should test
correctness at all (docs/future-experiments.md §0).

Usage:  python scripts/brazil_dedup_verdict.py <experiment-dir> [more dirs...]
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retort.scoring.scorers import runtime as rt  # noqa: E402

SEASON = 2019
EXPECTED_PLAYED = 38          # 20-team double round-robin
EXPECTED_TOP = "flamengo"
EXPECTED_POINTS = 90

#: Arg names implementations pick for "which season". Tried in order.
SEASON_ARGS = ("season", "year", "season_year", "temporada")


def _talk(cmd: list[str], cwd: Path, calls: list[dict], timeout: int = 40) -> list[dict]:
    """Send JSON-RPC lines, collect replies. Non-JSON banner lines are skipped."""
    try:
        p = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, bufsize=1)
    except (FileNotFoundError, OSError):
        return []
    out: list[dict] = []
    try:
        for c in calls:
            p.stdin.write(json.dumps(c) + "\n")
        p.stdin.flush()
        want = sum(1 for c in calls if "id" in c)
        deadline = time.perf_counter() + timeout
        while len(out) < want and time.perf_counter() < deadline:
            line = p.stdout.readline()
            if not line:
                break
            s = line.strip()
            if not s.startswith("{"):
                continue
            try:
                out.append(json.loads(s))
            except ValueError:
                continue
    except (BrokenPipeError, OSError):
        pass
    finally:
        p.kill()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    return out


def _standings_tool(tools: list[dict]) -> str | None:
    for t in tools:
        n = (t.get("name") or "").lower()
        if "standing" in n or "table" in n or "classifica" in n:
            return t.get("name")
    return None


def _find_played(obj, depth: int = 0):
    """Pull Flamengo's played-count out of whatever shape the server returned."""
    if depth > 6:
        return None
    if isinstance(obj, dict):
        blob = json.dumps(obj).lower()
        if EXPECTED_TOP in blob:
            for k, v in obj.items():
                if isinstance(v, (int, float)) and any(
                    s in k.lower() for s in ("played", "matches", "games", "jogos", "pj")
                ):
                    return int(v)
        for v in obj.values():
            got = _find_played(v, depth + 1)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = _find_played(v, depth + 1)
            if got is not None:
                return got
    return None


def verdict_for(run_dir: Path, language: str) -> dict:
    res = {"language": language, "run": str(run_dir), "verdict": "unknown",
           "played": None, "detail": ""}
    cmd, why = rt._build_then_entry(run_dir, language)
    if cmd is None:
        res["detail"] = why or "no runnable entrypoint"
        return res

    replies = _talk(cmd, run_dir, rt.BRAZIL_CALLS)
    tools = next((r["result"]["tools"] for r in replies
                  if r.get("id") == 2 and "result" in r
                  and isinstance(r["result"].get("tools"), list)), None)
    if not tools:
        res["detail"] = "no tools/list reply"
        return res
    name = _standings_tool(tools)
    if not name:
        res["detail"] = f"no standings-like tool among {[t.get('name') for t in tools]}"
        return res

    for arg in SEASON_ARGS:
        calls = rt.BRAZIL_CALLS + [{
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": name, "arguments": {arg: SEASON}},
        }]
        replies = _talk(cmd, run_dir, calls)
        r3 = next((r for r in replies if r.get("id") == 3), None)
        if not r3 or "result" not in r3:
            continue
        played = _find_played(r3["result"])
        if played is None:
            res["detail"] = f"{name}({arg}={SEASON}) gave no played-count for Flamengo"
            continue
        res["played"] = played
        if played == EXPECTED_PLAYED:
            res["verdict"] = "deduplicated"
        elif played > EXPECTED_PLAYED:
            res["verdict"] = "double-counted"
        else:
            res["verdict"] = "under-loaded"
        res["detail"] = f"{name}({arg}={SEASON}) -> Flamengo played={played}"
        return res
    return res


def main() -> int:
    rows = []
    for exp in sys.argv[1:]:
        for rd in sorted(p for p in (Path(exp) / "runs").glob("*/rep*")
                         if p.is_dir() and not p.name.endswith("-failed")):
            lang = next((x.split("=")[1] for x in rd.parent.name.split("_")
                         if x.startswith("language=")), "?")
            v = verdict_for(rd, lang)
            rows.append(v)
            print(f"  {lang:11s} {v['verdict']:15s} {v['detail'][:80]}", file=sys.stderr)

    print(f"\n| language | dedup verdict | Flamengo 2019 played | evidence |")
    print("|---|---|---:|---|")
    for r in rows:
        p = r["played"] if r["played"] is not None else "—"
        print(f"| {r['language']} | **{r['verdict']}** | {p} | {r['detail'][:60] or '—'} |")
    good = sum(1 for r in rows if r["verdict"] == "deduplicated")
    known = sum(1 for r in rows if r["verdict"] in ("deduplicated", "double-counted",
                                                    "under-loaded"))
    print(f"\n**{good}/{known}** implementations that could be probed handled the "
          f"overlap correctly (expected played=38; 20-team double round-robin).")
    Path("docs/brazil-dedup-verdicts.json").write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
