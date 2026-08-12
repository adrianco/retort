#!/usr/bin/env python3
"""Mark the fields in older provenance.json files that do NOT describe their run.

Until 2026-08-11 `provenance.capture()` recorded the LOCAL stack unconditionally,
so every cloud experiment (Claude Code or Codex) carries an `agent_config.hermes`
block and a `serving.omlx` sampling dict — `temperature 0.7, top_p 0.95,
top_k 40` — that were read off this machine's local serving stack and had nothing
to do with the hosted model that actually ran.

That matters more here than it would elsewhere: this file exists precisely
because unrecorded sampling silently halved the local numbers before exp-27, and
the repo's standing rule is that provenance reports the EFFECTIVE value. A
manifest stating the wrong sampling with confidence is worse than one stating
none.

WHY ANNOTATE RATHER THAN REWRITE. provenance.json is the audit trail — CLAUDE.md
says not to hand-edit it — and the recorded values are not fabricated: they are
real readings of this host, merely irrelevant to those runs. Deleting them would
destroy information about what the machine looked like at the time. The failure
mode is a reader believing the block describes the run, so the fix is to say
plainly that it does not, in the file, without touching what was recorded.

The hosted model's real sampling is NOT recoverable after the fact — it is set
provider-side and was never observable from the client — so this does not invent
a replacement value.

Usage:  python scripts/annotate_stale_provenance.py [--check]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MARKER = "_correction"
LOCAL_HARNESSES = {"hermes", "omp", "lcm"}

NOTE = {
    "issue": "provenance recorded the local stack for a cloud run",
    "fixed_in": "provenance.capture(agents=...) — 2026-08-11",
    "fields_that_do_not_describe_this_run": [
        "agent_config.hermes",
        "serving.omlx",
    ],
    "explanation": (
        "This experiment ran entirely on a hosted agent. The hermes and oMLX "
        "blocks above were read from the local serving stack installed on the "
        "host and were captured unconditionally by a bug; they did not affect "
        "this run. In particular the recorded sampling (temperature/top_p/"
        "top_k) was NOT applied — a hosted model's sampling is set provider-"
        "side and is not observable from the client, so it is unknown for this "
        "run rather than being the value shown."
    ),
    "still_valid": [
        "retort", "host", "harness", "models", "stack_presets",
        "tools (as an inventory of what was installed, not what ran)",
    ],
}


def affected(manifest: dict) -> bool:
    """True when a cloud-only run carries a local-stack block."""
    local_agents = (manifest.get("harness") or {}).get("local_agents") or {}
    kinds = {v.get("harness") for v in local_agents.values() if isinstance(v, dict)}
    if LOCAL_HARNESSES & kinds:
        return False                      # a local agent really did run
    has_local_block = bool((manifest.get("agent_config") or {}).get("hermes")) \
        or bool((manifest.get("serving") or {}).get("omlx"))
    return has_local_block


def main() -> int:
    check = "--check" in sys.argv
    files = sorted(Path("experiments").rglob("provenance.json"))
    todo, done = [], []
    for f in files:
        try:
            manifest = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if not affected(manifest):
            continue
        if manifest.get(MARKER):
            done.append(f)
            continue
        todo.append((f, manifest))

    if check:
        print(f"{len(done)} annotated, {len(todo)} still to annotate")
        for f, _ in todo:
            print(f"  {f}")
        return 1 if todo else 0

    for f, manifest in todo:
        manifest[MARKER] = NOTE
        f.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str))
        print(f"  annotated {f}")
    print(f"\n{len(todo)} annotated, {len(done)} already carried the note")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
