"""Aggregate every experiment's ``retort.db`` into one master results table.

As the program accumulates experiments, per-DB analysis stops being enough —
you want to ask cross-experiment questions ("every opus-4.8 brazil run across
exp-3/4/5", "rest-api-crud vs brazil duration by model"). This builds a single
wide, tidy table (one row per run) from all ``experiment-*/retort.db`` files,
tagged with the experiment and task, so pandas/SQL can slice across the whole
program. It is rebuilt from scratch each run, so it always reflects current data
(re-run it after a re-evaluation pass to pick up new metrics).
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

# Scored response metrics, in canonical column order.
METRICS = [
    "code_quality", "test_coverage", "defect_rate", "maintainability",
    "idiomatic", "token_efficiency", "requirement_coverage",
]
# Side-channel telemetry (underscore-prefixed in run_results) -> clean column.
TELEMETRY = {
    "_duration_seconds": "duration_seconds",
    "_tokens": "tokens",
    "_cost_usd": "cost_usd",
    "_turns": "turns",
    # Peak CONTEXT (largest prompt fed to the model in the run) — distinct from
    # `tokens`, which is the run's total spend. Answers "is the context window
    # sized right?", and a ballooning context predicts a non-terminating run.
    "_max_context_tokens": "max_context_tokens",
    # 1.0 when the run only reached its outcome on the self-repair SECOND attempt.
    # A `second_try` pass counts at HALF credit toward pass-proportion.
    "_second_try": "second_try",
    # Turn-like measure for harnesses that report no turn count. Codex fires one
    # `turn.completed` per exec regardless of work done, so `turns` stays NULL for
    # it while `agent_steps` carries its item.completed count (12-27/run vs
    # Claude's 10-30 turns). Separate columns on purpose — they are not the same
    # quantity, and a shared column would hide that.
    "_agent_steps": "agent_steps",
}
# Design factors promoted to their own column in the master table.
#
# THIS LIST MUST BE EXTENDED WHEN A NEW FACTOR SHIPS. It was
# ["language", "model", "tooling", "prompt"] when exp-49 introduced `effort`
# (thinking level), so all 63 of its runs aggregated with the factor SILENTLY
# DROPPED — the experiment's own retort.db had it, master.db did not, and no
# error was raised. `unknown_factors()` below exists so that cannot recur
# quietly: it reports any factor key present in the data but missing here.
FACTORS = ["language", "model", "tooling", "prompt", "effort", "agent", "stack"]
# `owner` = the experiments/<owner>/ segment: who ran the experiment. Carried into
# the master table so contributed studies are attributable and can be filtered
# (e.g. compare only your own runs, or audit a contributor's before merging).
TEXT_COLS = [
    "experiment", "owner", "task", "judge", "status", "started_at", "finished_at",
] + FACTORS


# Keys that appear in a run_config but are NOT design factors, so their absence
# from FACTORS is expected and must not be reported as a dropped factor.
_NON_FACTOR_KEYS = {"framework", "replicate", "task", "prompt_injection"}

# Populated during collection; read by unknown_factors() afterwards.
_SEEN_FACTOR_KEYS: set[str] = set()


def unknown_factors() -> set[str]:
    """Factor keys seen in the data but with no column in the master table.

    A non-empty result means aggregation is SILENTLY DISCARDING a factor: the
    per-experiment retort.db records it, master.db does not, and every
    cross-experiment analysis of that factor is impossible without anyone being
    told. That is exactly what happened to `effort` across all 63 runs of
    exp-49. Callers surface this as a warning.
    """
    return _SEEN_FACTOR_KEYS - set(FACTORS) - _NON_FACTOR_KEYS


def model_from_archives(exp_dir: Path) -> str:
    """The model an experiment ran, recovered from its archived ``stack.json``.

    Some designs name the model only in the agent PROFILE
    (``playpen.local_agents.<name>.model``) rather than as a design column, so
    the run_config carries no `model` and the row aggregates with a blank id —
    260 rows in master.db, which is why the reporting layer has to guess a stack
    from the experiment slug. The runner does record the effective model in each
    run's ``stack.json``, so it is recoverable.

    CONSERVATIVE ON PURPOSE: returns a model only when every archive in the
    experiment agrees. A multi-model experiment returns "" and its rows stay
    blank rather than being assigned a wrong id — mis-attributing runs to a
    model is exactly how gpt-oss runs once got counted as the 35B's.
    """
    models = set()
    for sj in exp_dir.glob("runs/**/stack.json"):
        # Skip "<cell>-failed" / "rep1-failed" snapshots: those are SUPERSEDED
        # attempts kept for diagnosis (a pre-repair copy, or a run that was
        # relaunched under a different config). exp-53 retained a first launch
        # under gpt-5.3-codex before the model was switched to gpt-5.6-luna, so
        # counting them made a single-model experiment look multi-model and the
        # conservative check refused to backfill anything.
        if any(part.endswith("-failed") for part in sj.parts):
            continue
        try:
            m = json.loads(sj.read_text()).get("model")
        except Exception:  # noqa: BLE001 — a damaged archive must not break aggregation
            continue
        if m:
            models.add(m)
        if len(models) > 1:
            return ""
    return models.pop() if len(models) == 1 else ""


def judge_for(exp_dir: Path) -> str:
    """Which judge graded this experiment, as ``harness:model`` (or "" if unknown).

    `requirement_coverage` — the number every headline in this repo rests on — is
    an LLM's opinion. It is only comparable across experiments if the SAME judge
    produced it. Since PR #45 the judge is configurable (`evaluation.judge`, with
    Claude and Codex runners), so an unrecorded judge would let two experiments
    graded by different models be averaged into one pass-proportion with nothing
    to indicate it. That is the same silent-variable failure as `effort` being
    dropped from FACTORS, and Hermes running at a turn cap nobody recorded.

    Read from the experiment's own workspace.yaml because the judge is configured
    per experiment, not per run.
    """
    wf = exp_dir / "workspace.yaml"
    if not wf.exists():
        wf = exp_dir.parent / "workspace.yaml"   # task sub-workspace layout
    if not wf.exists():
        return ""
    try:
        import yaml as _yaml

        cfg = _yaml.safe_load(wf.read_text()) or {}
    except Exception:  # noqa: BLE001 — a malformed config must not break aggregation
        return ""
    ev = cfg.get("evaluation") or {}
    if not isinstance(ev, dict):
        return ""
    judge = ev.get("judge")
    if isinstance(judge, dict):
        harness = judge.get("harness") or judge.get("profile") or "?"
        return f"{harness}:{judge.get('model') or '?'}"
    # Legacy: evaluation.model is a Claude model driven by claude-code.
    if ev.get("model"):
        return f"claude-code:{ev['model']}"
    return ""


def task_for(exp_dir: Path) -> str:
    """Best-effort task name for an experiment, from its workspace.yaml source."""
    wf = exp_dir / "workspace.yaml"
    if wf.exists():
        m = re.search(r"source:\s*(\S+)", wf.read_text())
        if m:
            src = m.group(1).lower()
            if "rest-api-crud" in src or "bookshop" in src:
                return "rest-api-crud"
            if "brazil" in src or "soccer" in src:
                return "brazil-soccer-mcp"
            return m.group(1)
    return "unknown"


def _owner_of(db: Path, root: Path) -> str:
    """Who ran this experiment — the ``experiments/<owner>/`` path segment.

    Experiments live under ``experiments/<owner>/experiment-*/`` so contributors
    can land their own studies by pull request without colliding, and so every run
    carries an attribution. Returns "" for the legacy flat layout
    (``experiment-*/`` at the repo root).
    """
    try:
        parts = db.relative_to(root).parts
    except ValueError:
        parts = db.parts
    if "experiments" in parts:
        i = parts.index("experiments")
        if i + 1 < len(parts) and not parts[i + 1].startswith("experiment-"):
            return parts[i + 1]
    # The caller may have pointed the root AT an owner dir
    # (--experiments-dir experiments/adrianco), in which case the relative path
    # holds no "experiments" segment and the owner is the root's own name. Fall
    # back to the ABSOLUTE path so attribution survives either invocation —
    # without this, aggregating that way silently produced unqualified labels.
    abs_parts = db.resolve().parts
    if "experiments" in abs_parts:
        i = abs_parts.index("experiments")
        if i + 1 < len(abs_parts) and not abs_parts[i + 1].startswith("experiment-"):
            return abs_parts[i + 1]
    return ""


def collect_runs(experiments_dir: Path) -> list[dict]:
    """One dict per run across all experiment DBs, wide (a column per metric)."""
    rows: list[dict] = []
    # Find experiment DBs in BOTH layouts, so a repo mid-migration still aggregates:
    #   experiments/<owner>/experiment-*/           (current — per-contributor)
    #   experiment-*/                               (legacy flat)
    # and in each, the DB may sit at the experiment root or one task sub-workspace
    # down (experiment-7/brazil/retort.db).
    patterns = (
        "experiment-*/retort.db", "experiment-*/*/retort.db",
        "*/*/experiment-*/retort.db", "*/*/experiment-*/*/retort.db",
    )
    db_paths: set[Path] = set()
    for pat in patterns:
        db_paths |= set(experiments_dir.glob(pat))
    for db in sorted(db_paths):
        parent = db.parent
        # Nested DBs (parent is the task sub-dir) get a compound label so each
        # row's `experiment` is unique, e.g. experiment-7-brazil. The label is
        # derived from the experiment dir name only, so it is stable across the
        # move to experiments/<owner>/.
        exp = parent.name if parent.name.startswith("experiment-") \
            else f"{parent.parent.name}-{parent.name}"
        owner = _owner_of(db, experiments_dir)
        # QUALIFY THE LABEL BY OWNER: "<githubid>/experiment-NN-slug".
        #
        # Experiment NUMBERS are only unique within a contributor's namespace —
        # experiments/<owner>/ prevents path collisions but not numbering ones.
        # PR #45 landed schoch/experiment-50/51/52 while adrianco/experiment-50
        # already existed, so a bare "experiment-50" in master.db would silently
        # merge two unrelated experiments into one group and average across them.
        # The owner is already known here; putting it in the label makes every
        # cross-experiment query and every blog table unambiguous.
        if owner and not exp.startswith(f"{owner}/"):
            exp = f"{owner}/{exp}"
        task = task_for(parent)
        judge = judge_for(parent)
        # Recover a model the design didn't name as a column (see docstring).
        fallback_model = model_from_archives(parent)
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            runs = con.execute(
                "SELECT id, replicate, status, started_at, finished_at, "
                "run_config_json FROM experiment_runs"
            ).fetchall()
        except sqlite3.OperationalError:
            con.close()
            continue
        for r in runs:
            cfg = json.loads(r["run_config_json"] or "{}")
            row: dict = {
                "experiment": exp, "owner": owner, "task": task, "judge": judge,
                "status": r["status"],
                "replicate": r["replicate"], "started_at": r["started_at"],
                "finished_at": r["finished_at"],
            }
            _SEEN_FACTOR_KEYS.update(k for k in cfg if k not in _NON_FACTOR_KEYS)
            for f in FACTORS:
                row[f] = cfg.get(f)
            if not row.get("model") and fallback_model:
                row["model"] = fallback_model
            for m in METRICS:
                row[m] = None
            for c in TELEMETRY.values():
                row[c] = None
            for mr in con.execute(
                "SELECT metric_name, value FROM run_results WHERE run_id=?", (r["id"],)
            ):
                name = mr["metric_name"]
                if name in METRICS:
                    row[name] = mr["value"]
                elif name in TELEMETRY:
                    row[TELEMETRY[name]] = mr["value"]
            rows.append(row)
        con.close()
    return rows


def build_master_db(experiments_dir: Path, out_path: Path) -> int:
    """(Re)build the master DB from all experiment DBs. Returns the run count."""
    rows = collect_runs(experiments_dir)
    cols = TEXT_COLS + ["replicate"] + METRICS + list(TELEMETRY.values())

    def coltype(c: str) -> str:
        if c == "replicate":
            return "INTEGER"
        if c in TEXT_COLS:
            return "TEXT"
        return "REAL"

    if out_path.exists():
        out_path.unlink()
    con = sqlite3.connect(out_path)
    con.execute(f"CREATE TABLE runs ({', '.join(f'{c} {coltype(c)}' for c in cols)})")
    placeholders = ", ".join("?" for _ in cols)
    con.executemany(
        f"INSERT INTO runs ({', '.join(cols)}) VALUES ({placeholders})",
        [tuple(r.get(c) for c in cols) for r in rows],
    )
    con.commit()
    con.close()
    return len(rows)


def write_csv(experiments_dir: Path, out_path: Path) -> int:
    """Also emit a CSV of the same wide table (handy for pandas/sharing)."""
    import csv
    rows = collect_runs(experiments_dir)
    cols = TEXT_COLS + ["replicate"] + METRICS + list(TELEMETRY.values())
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c) for c in cols})
    return len(rows)
