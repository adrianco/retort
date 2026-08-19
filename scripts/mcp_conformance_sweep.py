"""Sweep every archived brazil run for MCP protocol conformance.

Answers the question the text-reading probes cannot: would a REAL client accept
these servers? Resumable — results are appended one JSON object per line, and a
re-run skips whatever is already recorded, so an interrupted sweep costs only the
run it was on.

Each run is bounded: the probe carries its own wall-clock budget, and the build
step is capped separately, because a toolchain that hangs must not hold the sweep.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from retort.scoring.scorers import mcp_conformance as mc  # noqa: E402

#: The task's corpus, staged once outside the repo. 52 of 140 archived runs no
#: longer carry their own data/kaggle, and a server that cannot load the corpus
#: never reaches the protocol — so without this the sweep would score them 0.00
#: for a reason that has nothing to do with conformance. Verified byte-identical
#: across experiments before sharing (one digest over all six CSVs).
CANON = Path.home() / ".retort" / "cache" / "brazil-corpus" / "kaggle"

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "mcp-conformance-sweep.jsonl"


def runs() -> list[Path]:
    found = [p for p in ROOT.glob("experiments/*/*/brazil/runs/*/rep*")
             if p.is_dir() and not p.name.endswith("-failed")]
    return sorted(found)


def key(p: Path) -> str:
    return str(p.relative_to(ROOT))


def language_of(p: Path) -> str:
    for part in p.parts:
        if "language=" in part:
            return part.split("language=", 1)[1].split("_", 1)[0]
    return "?"


def experiment_of(p: Path) -> str:
    for part in p.parts:
        if part.startswith("experiment-"):
            return part
    return "?"


def main() -> int:
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                done.add(json.loads(line)["run"])
            except (ValueError, KeyError):
                pass
    targets = [p for p in runs() if key(p) not in done]
    print(f"{len(done)} already done, {len(targets)} to go", flush=True)

    for i, run_dir in enumerate(targets, 1):
        lang = language_of(run_dir)
        t0 = time.perf_counter()
        # Lend the corpus if this archive lost it, and take it back afterwards.
        # A measurement must not mutate the thing it measures.
        lent = None
        kaggle = run_dir / "data" / "kaggle"
        if not kaggle.exists() and CANON.is_dir():
            try:
                kaggle.parent.mkdir(parents=True, exist_ok=True)
                kaggle.symlink_to(CANON, target_is_directory=True)
                lent = kaggle
            except OSError:
                lent = None
        try:
            res = mc.measure(run_dir, lang, budget_s=180.0)
            # MEASURED vs UNMEASURABLE. A run whose server never completed the
            # handshake tells us nothing about its conformance — it tells us the
            # archive could not be resurrected (stripped build tree, absent
            # toolchain, dependency drift). Recording 0.00 there would put
            # "we could not run it" and "a real client rejects it" in the same
            # column, which is the single mistake this project keeps making.
            # Non-results are NULL, exactly as docs/runtime-measurement.md says.
            measured = any(c.name == "completes the MCP handshake" and c.passed
                           for c in res.checks)
            rec = {
                "run": key(run_dir), "language": lang,
                "experiment": experiment_of(run_dir),
                "measured": measured,
                "score": res.score if measured else None,
                "ok": res.ok if measured else None,
                "tools": res.tools,
                "note": res.note[:400],
                "failed_checks": [c.as_dict() for c in res.checks if not c.passed][:20],
                "checks_total": len(res.checks),
                "elapsed_s": round(time.perf_counter() - t0, 1),
            }
        except Exception as exc:  # noqa: BLE001 — one bad run must not end the sweep
            rec = {"run": key(run_dir), "language": lang,
                   "experiment": experiment_of(run_dir),
                   "measured": False, "score": None, "ok": None, "tools": 0,
                   "note": f"sweep error: {type(exc).__name__}: {exc}"[:400],
                   "failed_checks": [], "checks_total": 0,
                   "elapsed_s": round(time.perf_counter() - t0, 1)}
        finally:
            if lent is not None:
                try:
                    lent.unlink()
                    if not any(lent.parent.iterdir()):
                        lent.parent.rmdir()
                except OSError:
                    pass
        with OUT.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        s = "unmeasurable" if rec["score"] is None else f"{rec['score']:.2f}"
        print(f"[{i}/{len(targets)}] {lang:11s} {s}  {rec['elapsed_s']:6.1f}s  "
              f"{rec['note'][:70]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
