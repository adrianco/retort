"""Persisting run results: the experiment database side of `retort run`.

Second cut of the cli.py split. Everything here reads or writes the
experiment's retort.db -- design matrices, run rows, metric values,
requirement coverage, judge attempts, rescoring -- plus the archive-walking
helpers (`_iter_archive_cells`, `_is_rep_dir`, `_run_config_from_cell_name`)
that map an archived run directory back onto its row. `_factual_gate_failed`
lives here rather than with the other gate predicates because its only
callers are `run_experiments` and `_persist_rescore`, and it is a pure
function of its arguments; keeping it beside its persist caller avoids a
persist -> evaluate import, which is the wrong direction.

Graphify chose the boundary: every external caller is either
`run_experiments` (which stays in cli.py) or a `commands/` module reaching in
via `cli.<name>`. `cli.py` re-exports every function below, so both keep
resolving unchanged. Not moved: `_read_requirement_coverage`, whose only
caller is `_spec_conformance_passes` and which tests monkeypatch on `cli` --
it goes to run/evaluate.py with that caller.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import click

_REP_DIR_RE = re.compile(r"rep\d+$")


def _factor_match_sql(run_config: dict, col: str = "run_config_json") -> tuple[str, list]:
    """Build a WHERE fragment matching EVERY factor in a run_config.

    Matches on every factor present in run_config — language/model/tooling AND
    any others a design adds (e.g. ``prompt``). Hardcoding only language/model/
    tooling meant a prompt-factor design (exp-13) matched all prompt variants of
    a cell and persisted to whichever row sorted first — so reevaluate/rescore
    silently mis-targeted. ``tooling`` is always included and matched as JSON
    ``null`` (``IS NULL``) when absent, since designs without a tooling factor
    (exp-7/8) store no tooling key and ``= NULL`` is never true in SQL.
    """
    clauses, params = [], []
    for factor in sorted(set(run_config) | {"tooling"}):
        val = run_config.get(factor)
        if val is None:
            clauses.append(f"json_extract({col},'$.{factor}') IS NULL")
        else:
            clauses.append(f"json_extract({col},'$.{factor}')=?")
            params.append(val)
    return " AND ".join(clauses), params


def _is_rep_dir(name: str) -> bool:
    """True only for a *live* replicate archive dir — exactly ``rep<N>``.

    Guards evaluate/reevaluate/rescore against sibling dirs that merely *start*
    with ``rep`` (issue #44): a preserved dead attempt (``rep3-failed-attempt1``),
    a backup (``rep2-old``, ``rep1.bak``), etc. The old ``startswith("rep") and not
    endswith("-failed")`` test let those through, so a sibling got judged and its
    score raced onto the real replicate's DB row (last writer wins), silently
    overwriting a genuine pass with a preserved failure. ``diagnose`` keeps its own
    broader match because it *wants* the ``-failed`` dirs.
    """
    return _REP_DIR_RE.fullmatch(name) is not None


def _run_config_from_cell_name(name: str) -> dict | None:
    """Parse an archive cell-dir name into a run_config of factor values.

    Cell dirs are named ``<factor>=<value>_<factor>=<value>…`` (sorted keys,
    e.g. ``language=go_model=opus-4.8-fast_prompt=ATDD``). Generalised over ALL
    factors — not just language/model/tooling — so designs with extra factors
    (prompt, …) re-score and re-evaluate correctly. The value pattern is
    non-greedy up to the next ``_<word>=`` boundary, so values containing ``-``
    or ``.`` (``opus-4.8-fast``) parse intact. Returns None if no pairs match.
    """
    # Keys start with a letter so findall skips the ``_`` pair separators
    # (``\w`` would otherwise swallow them into the next key as ``_model``).
    pairs = re.findall(r"([A-Za-z]\w*)=(.+?)(?=_[A-Za-z]\w*=|$)", name)
    return dict(pairs) if pairs else None


def _iter_archive_cells(runs_root: Path) -> list[tuple[str, Path]]:
    """Return ``(cell_name, cell_dir)`` for every archived cell under ``runs_root``.

    A cell dir is any directory that *directly* contains a ``rep<N>`` (or
    ``rep<N>-failed``) subdir; its ``cell_name`` is the path *relative to*
    ``runs_root``. Using the relative path is what makes model ids containing
    ``/`` work: ``openrouter/anthropic/claude-opus-4.8`` nests the cell several
    directories deep (``…model=openrouter/anthropic/claude-opus-4.8_tooling=none``),
    and a plain ``runs_root.iterdir()`` stops at the first segment
    (``…model=openrouter``) — so rescore/reevaluate/evaluate found nothing and
    silently processed zero runs. For a single-segment cell name (no ``/`` in any
    factor value) this yields exactly what the old two-level walk did, so existing
    experiments are unaffected. Feed each ``cell_name`` to
    ``_run_config_from_cell_name`` (its value pattern already spans ``/``).
    """
    cells: list[tuple[str, Path]] = []
    for dirpath, dirnames, _files in os.walk(runs_root):
        d = Path(dirpath)
        # A cell dir is one with a "rep…" child — same loose test the callers use
        # to pick rep dirs (rep0, rep1, rep1-failed, and fixtures like rep-0).
        rep_children = [n for n in dirnames if n.startswith("rep")]
        if rep_children:
            cells.append((str(d.relative_to(runs_root)), d))
            # A rep dir holds source, not further cells — don't descend into it.
            dirnames[:] = [n for n in dirnames if n not in rep_children]
    return cells


def _run_row_exists(db_path, run_config: dict, replicate: int) -> bool:
    """True if ANY experiment_runs row matches these factors+replicate.

    Distinguishes an archive that maps to a real DB row (regardless of status)
    from an ORPHAN whose factors match nothing — the signature of broken
    cell-name parsing / factor matching (which silently dropped 33/36 cells of a
    prompt-factor experiment before the parser was generalised).
    """
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            f"SELECT 1 FROM experiment_runs WHERE replicate=? AND {where} LIMIT 1",
            (replicate, *params)).fetchone()
    finally:
        con.close()
    return row is not None


def _run_has_requirement_coverage(db_path, run_config: dict, replicate: int) -> bool:
    """True if the matching completed run already has a requirement_coverage row."""
    import sqlite3
    where, params = _factor_match_sql(run_config, "er.run_config_json")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT 1 FROM run_results rr JOIN experiment_runs er ON er.id=rr.run_id "
            "WHERE rr.metric_name='requirement_coverage' AND er.replicate=? "
            f"AND {where} LIMIT 1",
            (replicate, *params),
        ).fetchone()
    except sqlite3.OperationalError:
        row = None
    con.close()
    return row is not None


def _run_completed_exists(db_path, run_config: dict, replicate: int) -> bool:
    """True if a *completed* run matches these factors+replicate. A clean rep
    dir whose DB run is `failed` (or absent) can never receive coverage, so the
    re-evaluator skips it instead of burning evals on it every pass."""
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT 1 FROM experiment_runs WHERE replicate=? AND status='completed' "
            f"AND {where} LIMIT 1",
            (replicate, *params),
        ).fetchone()
    except sqlite3.OperationalError:
        row = None
    con.close()
    return row is not None


def _factual_gate_failed(scores) -> bool:
    """True when a golden-answer assertion failed.

    Absent (a task with no golden answers, or the scorer not requested) is NOT a
    failure — only a recorded score below 1.0 is. The scorer itself returns 1.0
    for tasks it does not cover, so this stays a no-op outside brazil-bench.
    """
    if scores is None:
        return False
    try:
        value = scores.get("factual_accuracy")
    except AttributeError:
        return False
    return value is not None and value < 1.0


def _init_database(db_path: Path) -> None:
    """Create and initialize the SQLite database with all tables."""
    from retort.storage.database import create_tables, get_engine

    engine = get_engine(db_path)
    create_tables(engine)
    engine.dispose()


def _persist_design_matrix(
    session,
    registry,
    design,
    phase: str,
    workspace_config,
) -> tuple[int, dict[str, int]]:
    """Persist the generated design matrix + factor levels to the database.

    Returns (matrix_id, mapping from sorted-json-config-key to row_id).

    Idempotent: a matrix with a matching (name, phase) is reused, with its
    rows looked up rather than re-created. This keeps repeated `retort run`
    invocations from accumulating duplicate matrices.
    """
    from retort.storage.models import (
        DesignMatrix,
        DesignMatrixCell,
        DesignMatrixRow,
        FactorLevel,
        LifecyclePhase,
    )

    name = workspace_config.experiment.name or "experiment"
    matrix_name = f"{name}-{phase}"
    phase_enum = LifecyclePhase(phase) if not isinstance(phase, LifecyclePhase) else phase

    # Look up an existing matrix with the same (name, phase). On resume this
    # avoids spawning a new matrix per run.
    matrix = (
        session.query(DesignMatrix)
        .filter(DesignMatrix.name == matrix_name, DesignMatrix.phase == phase_enum)
        .one_or_none()
    )
    if matrix is None:
        matrix = DesignMatrix(name=matrix_name, phase=phase_enum)
        session.add(matrix)
        session.flush()

    # Ensure all (factor_name, level_name) pairs exist as FactorLevel rows.
    level_lookup: dict[tuple[str, str], int] = {}
    for factor in registry.factors:
        for level in factor.levels:
            existing = (
                session.query(FactorLevel)
                .filter(
                    FactorLevel.factor_name == factor.name,
                    FactorLevel.level_name == level,
                )
                .one_or_none()
            )
            if existing is None:
                existing = FactorLevel(factor_name=factor.name, level_name=level)
                session.add(existing)
                session.flush()
            level_lookup[(factor.name, level)] = existing.id

    # Build the row index → row_id map. Skip rows that already exist (resume).
    config_to_row_id: dict[str, int] = {}
    for row_idx, run_config in enumerate(design.run_configs()):
        existing_row = (
            session.query(DesignMatrixRow)
            .filter(
                DesignMatrixRow.matrix_id == matrix.id,
                DesignMatrixRow.row_index == row_idx,
            )
            .one_or_none()
        )
        if existing_row is None:
            existing_row = DesignMatrixRow(matrix_id=matrix.id, row_index=row_idx)
            session.add(existing_row)
            session.flush()
            for factor_name, level_name in run_config.items():
                level_id = level_lookup.get((factor_name, level_name))
                if level_id is None:
                    # Factor or level not in registry — skip silently.
                    continue
                session.add(DesignMatrixCell(
                    row_id=existing_row.id, factor_level_id=level_id,
                ))
        else:
            # Reusing a row from a prior run (resume). Verify its persisted
            # factors match this config. Rows are keyed by POSITION, so if the
            # supplied --design's row order has drifted from the matrix, mapping
            # this config onto the existing row would silently overwrite a
            # DIFFERENT cell's runs via the uq_run_replicate constraint — the
            # row-index collision that clobbered 30 runs in exp-15 when a new
            # --design reused run indices 0-9 that already held other models.
            existing_factors = dict(
                session.query(FactorLevel.factor_name, FactorLevel.level_name)
                .join(
                    DesignMatrixCell,
                    DesignMatrixCell.factor_level_id == FactorLevel.id,
                )
                .filter(DesignMatrixCell.row_id == existing_row.id)
                .all()
            )
            mismatch = {
                fn: (lv, run_config.get(fn))
                for fn, lv in existing_factors.items()
                if run_config.get(fn) != lv
            }
            if mismatch:
                raise click.ClickException(
                    f"--design row {row_idx} already exists in matrix "
                    f"'{matrix_name}' with factors {existing_factors}, but the "
                    f"supplied design maps a different cell onto it (differs on "
                    f"{mismatch}). Refusing to overwrite: a --design CSV's row "
                    f"order must match the persisted matrix. Give new cells "
                    f"non-overlapping run indices, or use a fresh experiment."
                )

        config_to_row_id[json.dumps(run_config, sort_keys=True)] = existing_row.id

    return matrix.id, config_to_row_id


def _persist_metric_values(db_path, run_config: dict, replicate: int,
                           scores: dict[str, float]) -> bool:
    """Update only the named metrics on the latest matching run; no status change.

    For fixing a non-gating scorer gap (e.g. maintainability) on a passing run
    without re-running its (possibly un-rebuildable) tests. Returns True if a
    matching run was found.
    """
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    row = cur.execute(
        f"SELECT id FROM experiment_runs WHERE replicate=? AND {where} "
        "ORDER BY finished_at DESC", (replicate, *params)).fetchone()
    if not row:
        con.close()
        return False
    run_id = row[0]
    for name, value in scores.items():
        cur.execute("UPDATE run_results SET value=? WHERE run_id=? AND metric_name=?",
                    (float(value), run_id, name))
        if cur.rowcount == 0:
            cur.execute("INSERT INTO run_results (run_id, metric_name, value) VALUES (?,?,?)",
                        (run_id, name, float(value)))
    con.commit()
    con.close()
    return True


def _persist_requirement_coverage(db_path, run_config: dict, replicate: int,
                                  coverage: float | None) -> bool:
    """Upsert requirement_coverage onto the matching latest completed run.

    Non-destructive: only adds/replaces the requirement_coverage metric; never
    touches the run's status. Matches by factors + replicate (robust to JSON key
    order). Returns True if a run was found and updated.
    """
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id FROM experiment_runs WHERE replicate=? AND status='completed' "
        f"AND {where} ORDER BY finished_at DESC", (replicate, *params),
    ).fetchall()
    if not rows:
        con.close()
        return False
    run_id = rows[0][0]
    cur.execute("DELETE FROM run_results WHERE run_id=? AND metric_name='requirement_coverage'",
                (run_id,))
    if coverage is not None:
        cur.execute("INSERT INTO run_results (run_id, metric_name, value) VALUES (?,?,?)",
                    (run_id, "requirement_coverage", float(coverage)))
    con.commit()
    con.close()
    return True


def _persist_judge_attempt(
    run_dir: Path,
    judge,
    *,
    exit_code: int,
    stdout: str,
    stderr: str,
    duration_seconds: float,
) -> None:
    """Persist one judge attempt without overwriting prior spec opinions."""
    try:
        log_dir = run_dir / "_judge"
        log_dir.mkdir(exist_ok=True)
        attempt = len(list(log_dir.glob("attempt-*.json"))) + 1
        stem = log_dir / f"attempt-{attempt:03d}"
        stem.with_suffix(".stdout.log").write_text(stdout)
        stem.with_suffix(".stderr.log").write_text(stderr)
        stem.with_suffix(".json").write_text(json.dumps({
            "harness": judge.harness,
            "model": judge.model,
            "exit_code": exit_code,
            "duration_seconds": duration_seconds,
            "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, indent=2))
    except OSError:
        pass


def _persist_rescore(db_path, run_config: dict, replicate: int,
                     scores: dict[str, float]) -> str | None:
    """Write re-scored mechanical metrics onto the latest matching run.

    Updates the scorer metrics in-place (preserving the ``_``-prefixed telemetry
    and requirement_coverage), then reclassifies status via the conformance gate
    — a run whose tests now execute (``test_coverage`` > 0) becomes ``completed``;
    one that doesn't becomes ``failed``. Matches by factors + replicate across
    *any* status (so a false-failed run can be recovered). Returns the new status
    string, or None if no matching run was found.
    """
    import sqlite3
    where, params = _factor_match_sql(run_config)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        f"SELECT id FROM experiment_runs WHERE replicate=? AND {where} "
        "ORDER BY finished_at DESC", (replicate, *params),
    ).fetchall()
    if not rows:
        con.close()
        return None
    run_id = rows[0][0]
    for name, value in scores.items():
        cur.execute("UPDATE run_results SET value=? WHERE run_id=? AND metric_name=?",
                    (float(value), run_id, name))
        if cur.rowcount == 0:
            cur.execute("INSERT INTO run_results (run_id, metric_name, value) VALUES (?,?,?)",
                        (run_id, name, float(value)))
    # Reclassify against EVERY mechanical gate, not just test_coverage.
    # Consulting test_coverage alone silently UNDID the factual gate: rescoring
    # exp-57 flipped six runs to "completed RECOVERED", including cells scoring
    # factual_accuracy 0.00 whose 2019 table was demonstrably wrong. A recovery
    # path that resurrects runs a gate rejected is worse than no recovery path.
    # requirement_coverage is NOT consulted here — it is preserved untouched and
    # refreshed by `retort reevaluate`, which owns that gate.
    tests_ran = scores.get("test_coverage", 0.0) > 0.0
    facts_ok = not _factual_gate_failed(scores)
    new_status = "completed" if (tests_ran and facts_ok) else "failed"
    reason = (None if new_status == "completed"
              else "tests did not run (test_coverage=0)" if not tests_ran
              else f"answers wrong (factual_accuracy={scores.get('factual_accuracy')})")
    cur.execute(
        "UPDATE experiment_runs SET status=?, error_message=? WHERE id=?",
        (new_status, reason, run_id),
    )
    con.commit()
    con.close()
    return new_status


def _store_run_result(
    session,
    run_config: dict[str, str],
    phase: str,
    run_idx: int,
    replicate: int,
    artifacts,
    scores,
    design_row_id: int | None = None,
    conformance_failed: bool = False,
    #: WHICH gate failed, in the run's own words. Without it the DB labels every
    #: conformance failure "tests did not run", including spec and factual ones.
    conformance_reason: str | None = None,
    requirement_coverage: float | None = None,
    second_try: bool = False,
) -> None:
    """Store a run and its scores in the database.

    Status is three-way: a run whose agent never completed (``artifacts.succeeded``
    is False — CLI error, timeout kill, server unreachable) is ``crashed`` and is
    retried on ``--resume``. A run whose agent completed but that ``conformance_failed``
    (tests did not run, or the spec gate judged it short) is ``failed`` — a VALID
    data point that counts as progress and is not retried by default. Otherwise it
    is ``completed``. ``requirement_coverage``, when the spec eval produced one, is
    persisted as a metric so the eval's verdict feeds the scored data.
    """
    from retort.storage.models import (
        ExperimentRun,
        RunResult,
        RunStatus,
    )
    from datetime import datetime, timezone

    # Three-way outcome:
    #   crashed   — the agent did not complete (CLI error / timeout kill / server
    #               unreachable): no scoreable result → retried on --resume.
    #   failed    — the agent completed but the run fell short of a gate (tests
    #               did not run, or spec eval judged it incomplete): a VALID data
    #               point → counts as progress, not retried by default.
    #   completed — the agent completed and passed every gate.
    if not artifacts.succeeded:
        status = RunStatus.crashed
    elif conformance_failed:
        status = RunStatus.failed
    else:
        status = RunStatus.completed

    # Resume + retry-failed: a failed ExperimentRun for this same
    # (design_row_id, replicate) already exists. The unique constraint on
    # (design_row_id, replicate) blocks a fresh insert, so delete the
    # superseded row + its results first. design_row_id is None for runs
    # that predate matrix persistence; in that case match by run_config.
    if design_row_id is not None:
        existing = (session.query(ExperimentRun)
                    .filter_by(design_row_id=design_row_id, replicate=replicate)
                    .all())
    else:
        existing = (session.query(ExperimentRun)
                    .filter(
                        ExperimentRun.replicate == replicate,
                        ExperimentRun.run_config_json == json.dumps(run_config),
                    )
                    .all())
    for old in existing:
        session.query(RunResult).filter_by(run_id=old.id).delete()
        session.delete(old)
    if existing:
        session.flush()

    run = ExperimentRun(
        design_row_id=design_row_id,
        replicate=replicate,
        status=status,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        # WHICH gate fired, not a hardcoded guess. `conformance_failed` folds
        # three different gates into one boolean, and this line used to label
        # every one of them "tests did not run (test_coverage=0)". A run that
        # failed the SPEC gate was therefore recorded as having no tests — flatly
        # false, and exactly the wrong thing to tell whoever reads the archive
        # later. exp-62's arm A: test_coverage=1.0, requirement_coverage=0.917,
        # error_message="tests did not run". The console had it right all along;
        # only the DB lied.
        error_message=(
            artifacts.stderr if not artifacts.succeeded
            else (conformance_reason or "conformance gate failed")
            if conformance_failed else None
        ),
        run_config_json=json.dumps(run_config),
    )

    session.add(run)
    session.flush()  # Get the run ID

    for score in scores.scores:
        result = RunResult(
            run_id=run.id,
            metric_name=score.metric_name,
            value=score.value,
        )
        session.add(result)

    # The spec eval's verdict, when one was produced, is a first-class metric.
    if requirement_coverage is not None:
        session.add(RunResult(
            run_id=run.id,
            metric_name="requirement_coverage",
            value=float(requirement_coverage),
        ))

    # Persist non-scorer telemetry as RunResult rows too. Underscore prefix
    # marks them as side-channel data (vs. configured response metrics) so
    # downstream tools (analyze, web report) can choose to surface or hide
    # them. Without this, token/cost/duration are visible only at run-time
    # and lost forever. Stored for EVERY run — including `failed` and `crashed`
    # — even when zero, so a failure always records how long it took and how
    # many tokens it burned (a $0/0-token crash is itself a diagnostic signal).
    if artifacts.duration_seconds is not None:
        session.add(RunResult(
            run_id=run.id,
            metric_name="_duration_seconds",
            value=float(artifacts.duration_seconds),
        ))
    if artifacts.token_count is not None:
        session.add(RunResult(
            run_id=run.id,
            metric_name="_tokens",
            value=float(artifacts.token_count),
        ))
    # Peak context: the largest prompt the model was fed during this run. `_tokens`
    # is the run's TOTAL spend; this is its high-water CONTEXT mark — a different
    # question, and the one that says whether the context window is sized right.
    _peak = (artifacts.metadata or {}).get("max_context_tokens")
    if _peak:
        try:
            session.add(RunResult(
                run_id=run.id,
                metric_name="_max_context_tokens",
                value=float(_peak),
            ))
        except (TypeError, ValueError):
            pass
    # Flag a run that only reached its outcome on the self-repair SECOND attempt.
    # A second-try PASS counts at HALF credit toward pass-proportion in analysis;
    # the raw scores stay at their true final values.
    if second_try:
        session.add(RunResult(
            run_id=run.id,
            metric_name="_second_try",
            value=1.0,
        ))
    cost_str = artifacts.metadata.get("total_cost_usd") if artifacts.metadata else None
    if cost_str:
        try:
            # Attach OpenRouter reconcile provenance so validate_openrouter_spend.py
            # can cross-check this run's omp-reported cost against the billing API
            # (/api/v1/generation per id). Present only on OpenRouter-routed runs;
            # None otherwise so non-OpenRouter rows stay clean.
            reconcile = {
                k: artifacts.metadata[k]
                for k in (
                    "openrouter_generation_ids",
                    "upstream_provider",
                    "omp_cost_sum_all_turns",
                    "omp_assistant_turns",
                )
                if artifacts.metadata and k in artifacts.metadata
            }
            session.add(RunResult(
                run_id=run.id,
                metric_name="_cost_usd",
                value=float(cost_str),
                metadata_json=json.dumps(reconcile) if reconcile else None,
            ))
        except (TypeError, ValueError):
            pass
    turns_str = artifacts.metadata.get("num_turns") if artifacts.metadata else None
    if turns_str:
        try:
            turns_val = float(turns_str)
            if turns_val > 0:
                session.add(RunResult(
                    run_id=run.id,
                    metric_name="_turns",
                    value=turns_val,
                ))
        except (TypeError, ValueError):
            pass
    # AGENT STEPS — a turn-like measure for harnesses that do not report turns.
    #
    # Codex has no comparable turn count: it fires ONE `turn.completed` per exec
    # invocation regardless of how much work happened, so `_turns` is deliberately
    # left absent for it (recording 1 would put it at the bottom of the turn axis
    # and make it look absurdly efficient). But its `item.completed` events —
    # command_execution / agent_message / file_change — DO count model-initiated
    # actions, and land at 12–27 per run against Claude's 10–30, so they carry the
    # same information under a name that does not claim to be identical.
    #
    # Kept as a SEPARATE metric from `_turns` on purpose: anyone comparing across
    # harnesses has to notice they are reaching for a different column and decide
    # whether the two are commensurable, rather than being handed a false one.
    steps_str = (artifacts.metadata or {}).get("codex_items")
    if steps_str:
        try:
            steps_val = float(steps_str)
            if steps_val > 0:
                session.add(RunResult(
                    run_id=run.id,
                    metric_name="_agent_steps",
                    value=steps_val,
                ))
        except (TypeError, ValueError):
            pass
