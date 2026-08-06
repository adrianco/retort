#!/usr/bin/env python3
"""Why can a run that passed its tests not be STARTED by the runtime probe?

"The tests passed" and "the server starts" are different claims, and the probe
was unable to tell them apart: it launches every server with
stderr=subprocess.DEVNULL, so the one artifact that explains a failure to start
is discarded. A NoClassDefFoundError and a genuinely broken program produce the
identical note, "server did not answer".

This re-runs each unmeasured run WITH stderr captured and classifies the cause:

  HARNESS   the probe launched it wrongly (bad classpath, wrong entrypoint)
  ARCHIVE   the artifact it needs was stripped when the run was archived
  DEPS      it needs a package that is not installed here
  PROGRAM   it really does fail on its own terms
  UNKNOWN   no output to go on

Usage:  python scripts/diagnose_unrunnable.py [--json runtime-range.json]
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retort.scoring.scorers import runtime as rt  # noqa: E402

HANDSHAKE = "".join(json.dumps(c) + "\n" for c in rt.BRAZIL_CALLS)

#: (substring in stderr, verdict, explanation). First match wins.
SIGNATURES: list[tuple[str, str, str]] = [
    ("NoClassDefFoundError", "HARNESS", "launched without its dependencies on the classpath"),
    ("ClassNotFoundException", "HARNESS", "launched without its dependencies on the classpath"),
    ("ModuleNotFoundError", "DEPS", "a Python dependency is not installed"),
    ("ImportError", "DEPS", "a Python dependency is not importable"),
    ("Cannot find module", "ARCHIVE", "node_modules stripped by archiving"),
    ("MODULE_NOT_FOUND", "ARCHIVE", "node_modules stripped by archiving"),
    ("command not found", "HARNESS", "the launch command does not exist"),
    ("No such file or directory", "HARNESS", "the launch path does not exist"),
    ("undefined function", "PROGRAM", "missing export/entrypoint in the source"),
    ("init terminating", "PROGRAM", "the runtime aborted during start-up"),
    ("Segmentation fault", "PROGRAM", "crashed on start-up"),
    ("panic:", "PROGRAM", "panicked on start-up"),
    ("Traceback", "PROGRAM", "raised on start-up"),
    ("Exception in thread", "PROGRAM", "threw on start-up"),
]


def verdict(rc, out: str, err: str, note: str) -> tuple[str, str]:
    blob = f"{err}\n{out}"
    for sig, kind, why in SIGNATURES:
        if sig in blob:
            return kind, why
    if rc == "TIMEOUT" and out.strip().startswith("{"):
        return "HARNESS", "answered, but the probe stopped waiting"
    if rc == "TIMEOUT":
        return "PROGRAM", "started and then hung without answering"
    if out.strip().startswith("{"):
        return "HARNESS", "it DID answer when run directly"
    if not err.strip() and not out.strip():
        return "UNKNOWN", "no output on either stream"
    return "UNKNOWN", (err.strip().splitlines() or ["?"])[-1][:80]


def main() -> int:
    src = Path(sys.argv[sys.argv.index("--json") + 1]) if "--json" in sys.argv \
        else Path("docs/runtime-range.json")
    rows = [r for r in json.loads(src.read_text()) if not r["ok"]]
    # runtime-range.json does not record the run path, so resolve it from the
    # implementation survey, which scanned the same runs and does.
    survey = json.loads(Path("docs/implementation-survey.json").read_text())
    index: dict[tuple, list[str]] = {}
    for s in survey:
        index.setdefault((s["language"], s["model"], s.get("effort", "")), []).append(s["run"])
    used: set[str] = set()
    for r in rows:
        for cand in index.get((r["language"], r["model"], r.get("effort", "")), []):
            if cand not in used:
                r["run"] = cand
                used.add(cand)
                break
    print(f"re-running {len(rows)} unmeasured runs with stderr captured\n")

    out_rows = []
    for r in rows:
        run = Path(r["run"]) if r.get("run") else None
        if run is None or not run.is_dir():
            continue
        cmd, note = rt._build_then_entry(run, r["language"])
        if cmd is None:
            kind, why = "HARNESS", f"no launch recipe: {note}"
            rc, err = "-", ""
        else:
            try:
                p = subprocess.run(cmd, cwd=run.resolve(), input=HANDSHAKE,
                                   capture_output=True, text=True, timeout=90)
                rc, o, err = p.returncode, p.stdout, p.stderr
            except subprocess.TimeoutExpired as e:
                rc = "TIMEOUT"
                o = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
                err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            except Exception as ex:                       # noqa: BLE001
                rc, o, err = f"EXC", "", str(ex)
            kind, why = verdict(rc, o, err, r["note"])
        tag = f"{r['language']}/{r['model']}{('@'+r['effort']) if r['effort'] else ''}"
        print(f"  {kind:8s} {tag:34s} {why}")
        if err.strip():
            print(f"           | {err.strip().splitlines()[-1][:100]}")
        out_rows.append({**r, "verdict": kind, "why": why,
                         "stderr_tail": err.strip()[-600:]})

    Path("docs/unrunnable-diagnosis.json").write_text(json.dumps(out_rows, indent=1))
    from collections import Counter
    print("\n" + "\n".join(f"  {k:8s} {v}" for k, v in
                           Counter(r["verdict"] for r in out_rows).most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
