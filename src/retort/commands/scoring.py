"""Score / evaluate / recover commands — extracted from cli.py.

Registered on the shared ``main`` group; ``retort.cli`` imports this module at its
very bottom (after ``main`` and every helper are defined), so it is not circular.
Shared helpers are referenced through the ``cli`` module (``cli._helper(...)``) so
that monkeypatching ``retort.cli._helper`` reaches these command bodies too.
"""
from __future__ import annotations

import json  # noqa: F401  (used inside moved bodies)
import re  # noqa: F401
from pathlib import Path  # noqa: F401

import click

from retort import cli
from retort.cli import main


@main.command("evaluate")
@click.argument("run_dirs", nargs=-1, type=click.Path(exists=True, file_okay=False))
@click.option(
    "--experiment-dir",
    "experiment_dir",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Evaluate all runs in <EXPERIMENT_DIR>/runs/.",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="workspace.yaml",
    show_default=True,
    help="Path to workspace YAML config (for model + tracker settings).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-run evaluation even if evaluation.md is up-to-date.",
)
@click.option(
    "--workers",
    default=4,
    show_default=True,
    type=int,
    help="Parallel evaluation workers.",
)
def evaluate(
    run_dirs: tuple[str, ...],
    experiment_dir: str | None,
    config: str,
    force: bool,
    workers: int,
) -> None:
    """Evaluate run archives via the evaluate-run skill.

    Pass one or more RUN_DIRS, or use --experiment-dir to bulk-evaluate
    all runs in <EXPERIMENT_DIR>/runs/.  Use --force to re-run evaluations
    whose evaluation.md is already up-to-date.

    Use this for manual or retroactive evaluation of runs that predate
    auto-evaluation, or to re-evaluate after updating the skill.
    """
    import concurrent.futures
    from retort.config.loader import load_workspace

    if experiment_dir and run_dirs:
        raise click.UsageError("Pass either RUN_DIRS or --experiment-dir, not both.")
    if not experiment_dir and not run_dirs:
        raise click.UsageError("Provide at least one RUN_DIR or use --experiment-dir.")

    workspace_config = load_workspace(config)
    eval_cfg = workspace_config.evaluation
    if not eval_cfg.enabled:
        click.echo("evaluation.enabled=false in config, but running on manual request.")

    targets: list[Path]
    if experiment_dir:
        runs_root = Path(experiment_dir) / "runs"
        if not runs_root.is_dir():
            raise click.ClickException(f"No runs/ directory found in {experiment_dir}")
        # Cell dirs nest under runs/ (deeper when a model id contains '/'), and
        # each holds rep dirs with the actual code. _iter_archive_cells finds the
        # leaf cell dirs regardless of depth; a rep dir's name starts with "rep".
        targets = sorted(
            rep
            for _cell_name, cell in cli._iter_archive_cells(runs_root)
            for rep in cell.iterdir() if rep.is_dir() and cli._is_rep_dir(rep.name)
        )
        if not targets:
            raise click.ClickException(f"No rep directories found under {runs_root}")
        click.echo(f"Evaluating {len(targets)} run(s) in {runs_root} with {workers} workers", err=True)
    else:
        targets = [Path(d) for d in run_dirs]

    visibility = workspace_config.experiment.visibility

    def _eval_one(run_dir: Path) -> None:
        cli._run_auto_evaluation(run_dir, eval_cfg, visibility, force=force)

    if workers <= 1 or len(targets) == 1:
        for t in targets:
            _eval_one(t)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_eval_one, t): t for t in targets}
            for fut in concurrent.futures.as_completed(futures):
                exc = fut.exception()
                if exc:
                    click.echo(f"  (worker error for {futures[fut].name}: {exc})", err=True)


@main.command("reevaluate")
@click.option(
    "--experiment-dir", "experiment_dir", required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Experiment dir (uses its runs/ archives and retort.db).",
)
@click.option(
    "--config", type=click.Path(exists=True), default=None,
    help="Workspace YAML (defaults to <experiment-dir>/workspace.yaml).",
)
@click.option(
    "--eval-model", default="", show_default="latest (no --model passed)",
    help="Judge model for the second-opinion spec eval. Default: unset — the "
         "claude CLI picks its most recent model, so this tracks new releases "
         "automatically. Pass an explicit id to pin one.",
)
@click.option("--workers", default=2, show_default=True, type=int)
@click.option("--languages", help="Comma-separated language filter (default: all).")
@click.option(
    "--force", is_flag=True,
    help="Re-evaluate runs that already have requirement_coverage.",
)
def reevaluate(experiment_dir, config, eval_model, workers, languages, force):
    """Re-evaluate archived runs with the second-opinion spec eval, persisting
    requirement_coverage into the experiment's retort.db.

    Non-destructive: adds/updates the requirement_coverage metric only — run
    status is left unchanged (apply the conformance gate separately if you want
    to reclassify). Resumable: skips runs that already have a coverage value
    unless --force. Use after `retort aggregate` to refresh the master DB.
    """
    import concurrent.futures
    import re
    from retort.config.loader import load_workspace

    exp = Path(experiment_dir)
    db_path = exp / "retort.db"
    if not db_path.exists():
        raise click.ClickException(f"No retort.db in {experiment_dir}")
    cfg_path = config or (exp / "workspace.yaml")
    workspace_config = load_workspace(str(cfg_path))
    eval_cfg = workspace_config.evaluation.model_copy(
        update={"enabled": True, "model": eval_model}
    )
    visibility = workspace_config.experiment.visibility

    runs_root = exp / "runs"

    # Preflight: confirm the eval tooling actually works before spending a batch,
    # so a broken judge / missing skill fails loudly instead of silently
    # persisting nothing and reporting success.
    ok, msg = cli._eval_tooling_preflight(eval_model, runs_root)
    if not ok:
        raise click.ClickException(
            f"Eval tooling preflight FAILED: {msg}. "
            "Fix the judge model/skill before re-evaluating (nothing was changed)."
        )
    click.echo(f"Eval preflight OK — {msg}")

    reps = sorted(
        rep
        for _cell_name, cell in cli._iter_archive_cells(runs_root)
        for rep in cell.iterdir()
        if rep.is_dir() and cli._is_rep_dir(rep.name)
    )
    lang_filter = {s.strip() for s in languages.split(",")} if languages else None
    work = []
    skipped = 0
    orphaned: list[str] = []   # archives whose factors match NO db row
    incomplete = 0             # real row, but not completed (legit skip)
    already = 0                # already has coverage (legit skip)
    for rep in reps:
        # The cell dir name (language=X_model=Y[_prompt=Z…]) is the
        # authoritative factor source and matches what's stored in
        # run_config_json. Use the path relative to runs_root, not just
        # rep.parent.name, so a model id with '/' (which nests the cell) is
        # reconstructed whole. Older experiments' stack.json omit `model`, so
        # deriving factors from stack.json silently fails to match the DB row.
        run_config = cli._run_config_from_cell_name(str(rep.parent.relative_to(runs_root)))
        if not run_config:
            sj = rep / "stack.json"
            if not sj.exists():
                continue
            try:
                cfg = json.loads(sj.read_text())
            except (ValueError, OSError):
                # A malformed/empty stack.json must not kill the whole batch.
                skipped += 1
                click.echo(f"  (skipping {rep.parent.name}/{rep.name}: unreadable stack.json)", err=True)
                continue
            run_config = {k: cfg.get(k) for k in ("language", "model", "tooling")
                          if cfg.get(k) is not None}
        if lang_filter and run_config.get("language") not in lang_filter:
            continue
        m = re.search(r"rep(\d+)", rep.name)
        replicate = int(m.group(1)) if m else 1
        if not cli._run_completed_exists(db_path, run_config, replicate):
            # No completed DB row to attach coverage to. Distinguish a genuinely
            # incomplete run (a failed/running row exists) from an ORPHAN whose
            # factors match nothing — the latter means cell parsing/matching is
            # broken and the eval is silently skipping real runs.
            if cli._run_row_exists(db_path, run_config, replicate):
                incomplete += 1
            else:
                orphaned.append(f"{rep.parent.name}/{rep.name}")
            continue
        if not force and cli._run_has_requirement_coverage(db_path, run_config, replicate):
            already += 1
            continue
        work.append((rep, run_config, replicate))

    click.echo(
        f"Re-evaluating {len(work)} run(s) in {experiment_dir} "
        f"(judge={eval_model}, {workers} workers, second-opinion)"
    )

    def _eval(item):
        rep, run_config, replicate = item
        passed, cov = cli._spec_conformance_passes(rep, eval_cfg, visibility)
        return (rep, run_config, replicate, passed, cov)

    # Persist each result the moment its eval finishes (in the main thread, so
    # the DB write is serial/safe), rather than batching at the end. The covered
    # count then climbs run-by-run, and a mid-pass crash keeps what was done.
    counts = {"persisted": 0, "inconclusive": 0, "done": 0}

    def _handle(result):
        rep, run_config, replicate, verdict, cov = result
        counts["done"] += 1
        label = f"{rep.parent.name}/{rep.name}"
        if verdict is None:
            # Eval couldn't run (usage limit / timeout). Don't persist — leave
            # the run uncovered so a later resume re-evaluates it cleanly.
            counts["inconclusive"] += 1
            click.echo(f"  {label}: inconclusive (eval didn't run) — retry later")
            return
        if cli._persist_requirement_coverage(db_path, run_config, replicate, cov):
            counts["persisted"] += 1
        click.echo(f"  {label}: ReqCov={cov} [{'PASS' if verdict else 'fail'}]")

    if workers <= 1:
        for w in work:
            _handle(_eval(w))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for fut in concurrent.futures.as_completed([pool.submit(_eval, w) for w in work]):
                exc = fut.exception()
                if exc:
                    click.echo(f"  (worker error: {exc})", err=True)
                else:
                    _handle(fut.result())

    persisted, inconclusive = counts["persisted"], counts["inconclusive"]
    # Fold any WAL back into the .db so readers (aggregate) + git see a clean file.
    import sqlite3
    cx = sqlite3.connect(db_path)
    cx.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    cx.close()
    msg = f"Persisted requirement_coverage for {persisted}/{counts['done']} runs."
    if inconclusive:
        msg += f" {inconclusive} inconclusive (usage limit/timeout) — re-run to finish."
    click.echo(msg)

    # Health verdict: surface when the eval tooling silently did little/nothing,
    # rather than reporting success on an empty pass.
    click.echo(
        f"Eval health: {len(reps)} archived runs | matched {len(work) + already + incomplete} "
        f"(evaluated {len(work)}, already-covered {already}, incomplete {incomplete}) "
        f"| orphaned {len(orphaned)}"
    )
    problems = []
    if orphaned:
        ex = ", ".join(orphaned[:3]) + ("…" if len(orphaned) > 3 else "")
        problems.append(
            f"{len(orphaned)} archived run(s) matched NO database row — cell-name "
            f"parsing / factor matching is broken, real runs were skipped (e.g. {ex})"
        )
    if work and persisted == 0:
        problems.append(
            f"evaluated {len(work)} run(s) but persisted 0 coverage values — the "
            f"judge tooling produced nothing usable"
        )
    elif work and inconclusive == len(work):
        problems.append(
            f"all {len(work)} evals were inconclusive (the judge never ran)"
        )
    if problems:
        for p in problems:
            click.echo(f"  ✗ EVAL TOOLING PROBLEM: {p}", err=True)
        raise click.ClickException(
            "Eval tooling did not work correctly — see the problems above. "
            "requirement_coverage is unreliable until they are fixed."
        )


@main.command("rescore")
@click.option("--experiment-dir", "experiment_dir", required=True,
              type=click.Path(exists=True, file_okay=False),
              help="Experiment directory containing retort.db and runs/.")
@click.option("--config", type=click.Path(exists=True, dir_okay=False),
              help="Workspace YAML (defaults to <experiment-dir>/workspace.yaml).")
@click.option("--languages", help="Comma-separated language filter (default: all).")
@click.option("--only-failed", is_flag=True,
              help="Only re-score runs currently marked failed.")
@click.option("--metrics", "metrics_only",
              help="Re-score ONLY these metrics (comma-separated), computed "
                   "directly without the test-coverage gate and leaving status "
                   "unchanged. Use to fix a non-gating scorer gap (e.g. "
                   "maintainability) on already-passing runs whose trimmed "
                   "archives can no longer rebuild.")
@click.option("--workers", default=4, show_default=True, type=int)
@click.option("--dry-run", is_flag=True, help="Report changes without writing.")
def rescore(experiment_dir, config, languages, only_failed, metrics_only, workers, dry_run):
    """Re-score archived runs with the current scorers (DB + scores.json).

    Use after fixing or upgrading a scorer: re-runs the mechanical metrics
    against each archived run and writes the corrected values to retort.db
    (preserving the ``_``-prefixed telemetry and requirement_coverage) AND to the
    archive's ``scores.json`` (which the spec eval reads — keeping them in sync).
    Reclassifies status via the conformance gate: a run whose tests now execute
    (test_coverage > 0) becomes ``completed``. Run ``retort reevaluate`` afterward
    to refresh requirement_coverage, then ``retort aggregate``. Idempotent.

    With ``--metrics``, only the named metrics are recomputed (directly, no gate)
    and status is left untouched — the right tool when a passing run's archive
    was trimmed and can't rebuild, but a static metric (maintainability) needs a
    corrected value.
    """
    import concurrent.futures
    import re
    import sqlite3
    from retort.config.loader import load_workspace
    from retort.playpen.runner import RunArtifacts, StackConfig
    from retort.scoring.collector import ScoreCollector
    from retort.scoring.registry import create_default_registry

    subset = [s.strip() for s in metrics_only.split(",")] if metrics_only else None
    _registry = create_default_registry() if subset else None

    exp = Path(experiment_dir)
    db_path = exp / "retort.db"
    if not db_path.exists():
        raise click.ClickException(f"No retort.db in {experiment_dir}")
    cfg_path = config or (exp / "workspace.yaml")
    workspace_config = load_workspace(str(cfg_path))
    metrics = subset if subset else [r.name for r in workspace_config.responses]
    collector = None if subset else ScoreCollector(metrics=metrics)
    lang_filter = {s.strip() for s in languages.split(",")} if languages else None

    def _telemetry(run_config, replicate):
        where, params = cli._factor_match_sql(run_config)
        con = sqlite3.connect(db_path)
        row = con.execute(
            f"SELECT id, status FROM experiment_runs WHERE replicate=? AND {where} "
            "ORDER BY finished_at DESC", (replicate, *params)).fetchone()
        tele = {}
        if row:
            tele = dict(con.execute(
                "SELECT metric_name, value FROM run_results WHERE run_id=? "
                "AND metric_name LIKE '\\_%' ESCAPE '\\'", (row[0],)).fetchall())
        con.close()
        return (row[1] if row else None), tele

    runs_root = exp / "runs"
    work = []
    for cell_name, cell in sorted(cli._iter_archive_cells(runs_root)):
        run_config = cli._run_config_from_cell_name(cell_name)
        if not run_config:
            continue
        if lang_filter and run_config.get("language") not in lang_filter:
            continue
        for rep in sorted(cell.iterdir()):
            if not rep.is_dir() or not cli._is_rep_dir(rep.name):
                continue
            m = re.search(r"rep(\d+)", rep.name)
            replicate = int(m.group(1)) if m else 1
            status, tele = _telemetry(run_config, replicate)
            if status is None:
                continue
            if only_failed and status != "failed":
                continue
            work.append((rep, run_config, replicate, tele))

    click.echo(f"Re-scoring {len(work)} run(s) in {experiment_dir} "
               f"(metrics={','.join(metrics)}, {workers} workers"
               f"{', dry-run' if dry_run else ''})")

    def _score(item):
        rep, run_config, replicate, tele = item
        stack = StackConfig(
            language=run_config["language"], agent=run_config.get("agent", "unknown"),
            framework=run_config.get("framework", "none"),
            extra={"tooling": run_config["tooling"]} if "tooling" in run_config else {})
        artifacts = RunArtifacts(
            output_dir=rep, stdout="", stderr="", exit_code=0,
            duration_seconds=tele.get("_duration_seconds", 0.0),
            token_count=int(tele.get("_tokens", 0) or 0), metadata={})
        if subset:
            # Direct per-scorer computation — no test-coverage gate, so a static
            # metric still gets a real value on an archive that can't rebuild.
            scores = {}
            for m in subset:
                if m in _registry:
                    try:
                        scores[m] = _registry.get(m).score(artifacts, stack)
                    except Exception:
                        scores[m] = 0.0
        else:
            scores = {s.metric_name: s.value for s in collector.collect(artifacts, stack).scores}
        return (rep, run_config, replicate, scores)

    counts = {"updated": 0, "recovered": 0, "done": 0}

    def _handle(result):
        rep, run_config, replicate, scores = result
        counts["done"] += 1
        tc = scores.get("test_coverage")
        label = f"{rep.parent.name}/{rep.name}"
        if dry_run:
            click.echo(f"  [dry] {label}: " + " ".join(f"{k}={v:.2f}" for k, v in scores.items()))
            return
        if subset:
            # Update only the named metrics; leave status and other metrics alone.
            cli._persist_metric_values(db_path, run_config, replicate, scores)
            try:
                sj = rep / "scores.json"
                existing = json.loads(sj.read_text()) if sj.exists() else {}
                existing.update(scores)
                sj.write_text(json.dumps(existing))
            except (OSError, ValueError):
                pass
            counts["updated"] += 1
            click.echo(f"  {label}: " + " ".join(f"{k}={v:.2f}" for k, v in scores.items())
                       + " (metrics-only)")
            return
        new_status = cli._persist_rescore(db_path, run_config, replicate, scores)
        try:
            (rep / "scores.json").write_text(json.dumps(scores))
        except OSError:
            pass
        if new_status == "completed":
            counts["updated"] += 1
        gate = "" if tc is None else (" RECOVERED" if tc > 0 else " still-fails-gate")
        click.echo(f"  {label}: " + " ".join(f"{k}={v:.2f}" for k, v in scores.items())
                   + f" -> {new_status}{gate}")

    if workers <= 1:
        for w in work:
            _handle(_score(w))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for fut in concurrent.futures.as_completed([pool.submit(_score, w) for w in work]):
                exc = fut.exception()
                if exc:
                    click.echo(f"  (worker error: {exc})", err=True)
                else:
                    _handle(fut.result())

    if not dry_run:
        cx = sqlite3.connect(db_path)
        cx.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        cx.close()
    click.echo(f"Re-scored {counts['done']} run(s); {counts['updated']} now completed. "
               f"Run `retort reevaluate` then `retort aggregate` to refresh.")


@main.command("diagnose")
@click.option("--experiment-dir", "experiment_dir", required=True,
              type=click.Path(exists=True, file_okay=False),
              help="Experiment directory containing retort.db and runs/.")
@click.option("--as-json", "as_json", is_flag=True,
              help="Emit JSON instead of the text report.")
def diagnose(experiment_dir, as_json):
    """Deep-analyse every FAILED run and classify it TOOLING vs GENUINE.

    Read-only, so you never have to hand-investigate a failure again. For each
    failed run it RE-TESTS the archived code with the current scorers and probes
    the test command:

    \b
    * TOOLING — the code actually builds and its tests pass; the gate failed it
      on a scoring artefact (e.g. coverage measured 0 on passing tests). These
      recover with `retort rescore --only-failed`.
    * GENUINE — the tests genuinely don't run / don't pass, or the spec isn't
      met (requirement_coverage < 1). The specific cause is reported.

    Note: re-testing python archives installs their deps, so a large failure set
    can take a few minutes.
    """
    import json as _json
    import sqlite3

    from retort.playpen.runner import RunArtifacts, StackConfig
    from retort.scoring.scorers.test_coverage import TestCoverageScorer

    exp = Path(experiment_dir)
    db_path = exp / "retort.db"
    if not db_path.exists():
        raise click.ClickException(f"No retort.db in {experiment_dir}")
    runs_root = exp / "runs"
    scorer = TestCoverageScorer()
    con = sqlite3.connect(db_path)
    failed = con.execute(
        "SELECT id, run_config_json, replicate, error_message FROM experiment_runs "
        "WHERE status IN ('failed','crashed') ORDER BY run_config_json, replicate").fetchall()

    def _metric(run_id, name):
        r = con.execute(
            "SELECT value FROM run_results WHERE run_id=? AND metric_name=?",
            (run_id, name)).fetchone()
        return r[0] if r else None

    findings = []
    for run_id, rc_json, rep, err in failed:
        rc = _json.loads(rc_json)
        cell = "_".join(f"{k}={v}" for k, v in sorted(rc.items()))
        label = f"{cell}/rep{rep}"
        # A failed run is archived as repN-failed when one exists; otherwise the
        # gate-failed-but-code-present runs keep the plain repN dir.
        rep_dir = runs_root / cell / f"rep{rep}-failed"
        if not rep_dir.is_dir():
            rep_dir = runs_root / cell / f"rep{rep}"
        req_cov = _metric(run_id, "requirement_coverage")
        old_tc = _metric(run_id, "test_coverage")
        cost = _metric(run_id, "_cost_usd")
        dur = _metric(run_id, "_duration_seconds")
        # A failure that burned ~$0 and finished almost instantly didn't fail on
        # the model's merits — it was interrupted (usage/rate limit, a kill, a CLI
        # error). The tell: a genuine failure spends minutes and dollars; an
        # interruption is instant and free. Re-run it, don't trust the "failure".
        if cost in (0, 0.0, None) and dur is not None and dur < 60 \
                and old_tc in (0, 0.0, None):
            findings.append((label, "INTERRUPTED",
                             "~$0 cost / near-instant — a usage-limit or killed "
                             "run, not a model failure; re-run with --resume"))
            continue
        if not rep_dir.is_dir():
            findings.append((label, "UNKNOWN", "no archived run dir to inspect"))
            continue
        # HARNESS — the agent was PREVENTED from working, so this is not a model
        # result at all. It outranks TOOLING/GENUINE because the run never really
        # happened: a blocked file tool (or an agent that wrote nothing) scores a
        # zero indistinguishable from an incapable model, which is how a harness
        # bug once masqueraded as a language "capability wall".
        _harness = cli._harness_failure(rep_dir)
        if _harness:
            findings.append((label, "HARNESS", _harness))
            continue
        stack = StackConfig(
            language=rc.get("language", ""), agent=rc.get("agent", "unknown"),
            framework=rc.get("framework", "none"),
            extra={"tooling": rc["tooling"]} if "tooling" in rc else {})
        art = RunArtifacts(output_dir=rep_dir, stdout="", stderr="", exit_code=0,
                           duration_seconds=0.0, token_count=0, metadata={})
        # Mechanical-gate failure (tests did not run) → re-test with current scorers.
        if (err or "").startswith("tests did not run") or old_tc in (0, 0.0, None):
            tc = scorer.score(art, stack)
            if tc and tc > 0:
                findings.append((label, "TOOLING",
                                 f"tests now run and measure {tc:.0%} coverage — "
                                 "scorer false-failure (rescore recovers it)"))
            else:
                rate = scorer._tests_pass_rate(rep_dir.resolve(), rc.get("language", ""))
                if rate and rate > 0:
                    findings.append((label, "TOOLING",
                                     f"tests pass ({rate:.0%}) but the coverage "
                                     "tool measured 0"))
                else:
                    findings.append((label, "GENUINE",
                                     "tests do not run / do not pass on the "
                                     "archived code"))
        elif req_cov is not None and req_cov < 1.0:
            findings.append((label, "GENUINE",
                             f"spec shortfall: requirement_coverage={req_cov}"))
        else:
            findings.append((label, "GENUINE", err or "failed (no recorded reason)"))
    con.close()

    if as_json:
        click.echo(_json.dumps(
            [{"cell": c, "class": k, "cause": v} for c, k, v in findings], indent=2))
        return
    tooling = [f for f in findings if f[1] == "TOOLING"]
    genuine = [f for f in findings if f[1] == "GENUINE"]
    interrupted = [f for f in findings if f[1] == "INTERRUPTED"]
    if not findings:
        click.echo("No failed runs to diagnose — all runs are completed.")
        return
    click.echo(f"Diagnosed {len(findings)} failed run(s): {len(tooling)} TOOLING, "
               f"{len(genuine)} GENUINE, {len(interrupted)} INTERRUPTED\n")
    for c, k, v in findings:
        click.echo(f"  [{k:11}] {c}\n             {v}")
    if tooling:
        click.echo(f"\n→ {len(tooling)} tooling false-failure(s) recover with:\n"
                   f"    retort rescore --experiment-dir {experiment_dir} --only-failed")
    if interrupted:
        click.echo(f"\n→ {len(interrupted)} interrupted run(s) just need re-running:\n"
                   f"    retort run … --config {experiment_dir}/workspace.yaml "
                   "--resume --retry-failed")


def _nonpassing_languages(exp: Path) -> list[str]:
    """Languages that have at least one non-``completed`` cell in the experiment's
    retort.db — the set `recover` refreshes requirement_coverage on. Captured BEFORE
    rescore (which flips recovered cells to completed)."""
    import json
    import sqlite3

    db = exp / "retort.db"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    try:
        rows = conn.execute(
            "SELECT run_config_json, status FROM experiment_runs"
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
    langs: set[str] = set()
    for cfg_json, status in rows:
        if status and status != "completed":
            try:
                lang = (json.loads(cfg_json or "{}") or {}).get("language")
            except (ValueError, TypeError):
                lang = None
            if lang:
                langs.add(lang)
    return sorted(langs)


@main.command()
@click.option(
    "--experiment-dir",
    type=click.Path(exists=True),
    required=True,
    help="Experiment dir (uses its retort.db + runs/ archives).",
)
@click.option(
    "--reevaluate/--no-reevaluate",
    "run_reeval",
    default=True,
    help="After rescoring, refresh requirement_coverage on the recovered cells' "
    "languages (default on). Skip it (faster, e.g. for an all-tooling recovery) "
    "with --no-reevaluate.",
)
@click.option("--eval-model", default=None, help="Judge model for the reevaluate pass.")
@click.option(
    "--workers", type=int, default=3, help="Parallel workers for rescore / reevaluate."
)
@click.pass_context
def recover(ctx, experiment_dir, run_reeval, eval_model, workers):
    """Post-run recovery in one step: diagnose → rescore --only-failed → reevaluate.

    The standard cleanup after a local run, which reliably produces a few scorer
    TOOLING false-failures (all-zeros on code that actually builds and passes —
    e.g. coverage measured 0 on passing tests). This chains the three commands you
    would otherwise run by hand: it classifies the failures, rescores the tooling
    ones back to their true metrics, then refreshes requirement_coverage on the
    languages that had failures so the spec gate is honest. Finish with
    `retort aggregate` to publish the corrected numbers to master.db.
    """
    exp = Path(experiment_dir)
    langs = _nonpassing_languages(exp)  # capture before rescore flips them

    click.echo("== diagnose ==")
    ctx.invoke(diagnose, experiment_dir=experiment_dir)

    click.echo("\n== rescore --only-failed ==")
    ctx.invoke(rescore, experiment_dir=experiment_dir, only_failed=True, workers=workers)

    if run_reeval and langs:
        click.echo(f"\n== reevaluate --force --languages {','.join(langs)} ==")
        ctx.invoke(
            reevaluate,
            experiment_dir=experiment_dir,
            languages=",".join(langs),
            force=True,
            workers=workers,
            eval_model=eval_model,
        )
    elif run_reeval:
        click.echo("\n== reevaluate: no non-passing cells to refresh ==")

    click.echo(
        "\n→ done. Run `retort aggregate --out master.db` to publish the corrected numbers."
    )


