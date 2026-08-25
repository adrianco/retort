"""Did `agent.verify_on_stop` actually take effect in exp-62's two arms?

The criterion was fixed BEFORE the results existed (docs/future-experiments.md):
Hermes' enabled path injects a synthetic follow-up turn via
`build_verify_on_stop_nudge()`, whose text contains

    Run the relevant verification command now (

PASS = that string appears in the verify-ON arm's agent log and NOT in the
verify-OFF arm's. A turn-count delta is reported for interest but is explicitly
NOT the criterion: turns move for unrelated reasons and exp-61 showed
within-cell spread dominating on this exact stack.

This exists because "I set it" is not "it took effect" — the first principle in
CLAUDE.md, and a capability toggle is precisely the kind of parameter that has
silently no-op'd here before.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FINGERPRINT = "Run the relevant verification command now ("


def arm_of(run_dir: Path) -> str | None:
    """Which arm a run belongs to, read from what it RECORDED, not its path.

    stack.json carries the effective agent config, so this reports what the run
    actually executed with rather than what its directory name claims.
    """
    try:
        stack = json.loads((run_dir / "stack.json").read_text())
    except (OSError, ValueError):
        return None
    hermes = stack.get("hermes") or {}
    if "verify_on_stop" in hermes:
        return f"verify_on_stop={hermes['verify_on_stop']!r}"
    return f"stack={stack.get('stack') or stack.get('preset') or '?'}"


def agent_log_text(run_dir: Path) -> str:
    out = []
    for name in ("_agent_stdout.log", "_agent_stderr.log"):
        p = run_dir / name
        if p.exists():
            out.append(p.read_text(errors="replace"))
    return "\n".join(out)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "experiments/adrianco/experiment-62-verify-on-stop/local")
    runs = sorted(p for p in root.glob("runs/*/rep*") if p.is_dir())
    if not runs:
        print(f"no runs under {root}/runs — has the smoke finished?")
        return 2

    rows = []
    for run in runs:
        text = agent_log_text(run)
        rows.append({
            "run": run.parent.name[:58],
            "arm": arm_of(run) or "?",
            "nudged": FINGERPRINT in text,
            "hits": text.count(FINGERPRINT),
            "log_kb": len(text) // 1024,
        })

    print(f"{'arm':26s} {'nudged':>7s} {'hits':>5s} {'log':>7s}  run")
    for r in rows:
        print(f"{r['arm']:26s} {str(r['nudged']):>7s} {r['hits']:>5d} "
              f"{r['log_kb']:>5d}KB  {r['run']}")
    print()

    on = [r for r in rows if r["arm"] == "verify_on_stop=True"]
    off = [r for r in rows if r["arm"] == "verify_on_stop=False"]
    if not on or not off:
        print("INCONCLUSIVE: both arms must be present and must have recorded")
        print("their effective verify_on_stop in stack.json.")
        return 2
    if any(r["log_kb"] == 0 for r in rows):
        print("INCONCLUSIVE: an arm produced no agent log to search.")
        return 2

    on_ok = all(r["nudged"] for r in on)
    off_ok = not any(r["nudged"] for r in off)
    if on_ok and off_ok:
        print("PASS — the toggle takes effect: the ON arm was nudged, the OFF arm was not.")
        return 0
    print("FAIL — the toggle did NOT take effect as configured:")
    if not on_ok:
        print("  the verify-ON arm was never nudged; the setting is a no-op there.")
    if not off_ok:
        print("  the verify-OFF arm WAS nudged; something is forcing it on.")
    print("  Do NOT run the grid until this is explained — both arms would be")
    print("  measuring the same thing and the result would be a confident null.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
