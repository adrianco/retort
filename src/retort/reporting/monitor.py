"""Live progress monitor for in-flight and completed experiment runs.

Reads a retort SQLite database and summarizes run status, per-cell coverage,
resource totals (cost / tokens / duration), throughput, and an ETA. It is safe
to point at a database that is actively being written by one or more
``retort run`` shards: it only reads, and the runner commits one row per run, so
each snapshot reflects every run that has finished so far.

The runner persists a row in ``experiment_runs`` only when a run reaches a
terminal state (``completed`` / ``failed``), so the number of in-flight runs is
inferred as ``expected_total - completed - failed`` rather than read directly.
``expected_total`` comes from the design (``design_matrix_rows`` × replicates).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from retort.storage.models import (
    DesignMatrixRow,
    ExperimentRun,
    RunResult,
    RunStatus,
)

# Underscore-prefixed metrics carry resource data rather than quality scores.
COST_METRIC = "_cost_usd"
TOKENS_METRIC = "_tokens"
DURATION_METRIC = "_duration_seconds"
# Peak CONTEXT (largest prompt fed to the model), distinct from total token spend.
CONTEXT_METRIC = "_max_context_tokens"
_RESOURCE_METRICS = frozenset(
    {COST_METRIC, TOKENS_METRIC, DURATION_METRIC, CONTEXT_METRIC, "_turns"}
)

# An idle gap longer than this between consecutive run starts marks a new run
# session (e.g. a --resume after a usage-limit pause), so throughput/ETA are
# measured over the current session rather than since the first-ever run.
_SESSION_GAP_S = 3600.0

# Cap the failures list in the text report so a run with dozens of pending
# retries doesn't flood a --watch screen; the full list is still in --json.
_MAX_FAILURES_SHOWN = 5


def _as_utc(dt: datetime | None) -> datetime | None:
    """Coerce a (possibly naive, SQLite-sourced) datetime to UTC-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _label(factors: dict, run_id: int) -> str:
    """Stable ``value/value/...`` cell label ordered by factor name."""
    return "/".join(str(factors[k]) for k in sorted(factors)) or f"run-{run_id}"


def resolve_target(
    target: str | None,
    db: str | None = None,
    config: str | None = None,
) -> tuple[Path, Path | None]:
    """Resolve a positional experiment target to ``(db_path, config_path)``.

    Convention: ``retort monitor experiment-5`` finds ``experiment-5/retort.db``
    and ``experiment-5/workspace.yaml``. ``target`` may be an experiment
    directory, a path to a ``.db`` file, or omitted (falling back to the
    explicit ``--db`` / ``--config`` options). Explicit ``db`` / ``config``
    always win over inferred paths.

    Raises:
        ValueError: if no database path can be determined.
    """
    db_path: Path | None = Path(db) if db else None
    config_path: Path | None = Path(config) if config else None

    if target is not None:
        p = Path(target)
        # A direct .db file, else treat the target as an experiment directory.
        if p.suffix == ".db" or (p.is_file() and p.suffix != ""):
            base = p.parent
            db_path = db_path or p
        else:
            base = p
            db_path = db_path or p / "retort.db"
        if config_path is None and (base / "workspace.yaml").is_file():
            config_path = base / "workspace.yaml"

    if db_path is None:
        raise ValueError(
            "No database to monitor. Pass an experiment directory "
            "(e.g. `retort monitor experiment-5`) or `--db <path>`."
        )
    return db_path, config_path


@dataclass
class CellProgress:
    """Aggregated progress for one design cell (one factor combination)."""

    factors: dict[str, str]
    completed: int = 0
    failed: int = 0
    crashed: int = 0
    cost_usd: float = 0.0
    tokens: float = 0.0
    duration_total_s: float = 0.0
    max_context: float = 0.0   # high-water context across this cell's runs
    metric_means: dict[str, float] = field(default_factory=dict)

    @property
    def mean_duration_s(self) -> float | None:
        """Mean wall-clock duration per completed run in this cell."""
        return self.duration_total_s / self.completed if self.completed else None

    @property
    def label(self) -> str:
        """Stable ``value/value/...`` label, ordered by factor name."""
        return "/".join(v for _, v in sorted(self.factors.items()))

    def display_label(self, keys: list[str]) -> str:
        """Label built from ``keys`` only, with separator-safe values.

        A factor value can itself contain ``/`` (e.g. a model id like
        ``mlxlocal/Qwen3.6-35B-A3B``), which would masquerade as extra factors in
        the joined label — so slashes inside a value become ``-``.
        """
        return "/".join(
            str(self.factors.get(k, "")).replace("/", "-") for k in keys
        ) or "(single cell)"


def informative_factors(cells: list[CellProgress]) -> list[str]:
    """The factors worth putting in a cell label.

    Drops the two kinds of noise that make the table unreadable:

    * **constant** factors — every cell shares the value (e.g. ``agent`` and
      ``prompt`` in a single-agent sweep), so they distinguish nothing;
    * **redundant** factors — a factor that partitions the cells exactly like an
      earlier one (e.g. ``model`` and ``stack``, which are 1:1 by construction in
      a stack-preset sweep). Of a redundant pair we keep whichever has the
      shorter values, so ``m35`` wins over ``mlxlocal/Qwen3.6-35B-A3B``.

    Falls back to every factor if that would leave nothing to show.
    """
    if not cells:
        return []
    keys = sorted({k for c in cells for k in c.factors})
    varying = [k for k in keys if len({c.factors.get(k) for c in cells}) > 1]

    kept: list[str] = []
    seen_partitions: list[tuple[tuple[str, ...], str]] = []
    for k in varying:
        # A factor's "partition" is how it groups the cells; identical partitions
        # carry identical information.
        partition = tuple(str(c.factors.get(k)) for c in cells)
        groups = tuple(sorted({p for p in partition}))
        width = max((len(v) for v in groups), default=0)
        dup = next(
            (i for i, (g, _) in enumerate(seen_partitions)
             if _same_partition(partition, cells, seen_partitions[i][1])),
            None,
        )
        if dup is not None:
            prev_key = seen_partitions[dup][1]
            prev_width = max(
                (len(str(c.factors.get(prev_key))) for c in cells), default=0
            )
            if width < prev_width:  # keep the more readable of the two
                kept[kept.index(prev_key)] = k
                seen_partitions[dup] = (groups, k)
            continue
        seen_partitions.append((groups, k))
        kept.append(k)
    return kept or varying or keys


def _same_partition(
    partition: tuple[str, ...], cells: list[CellProgress], other_key: str
) -> bool:
    """True when ``partition`` groups the cells exactly as ``other_key`` does."""
    other = tuple(str(c.factors.get(other_key)) for c in cells)
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}
    for a, b in zip(partition, other):
        if mapping.setdefault(a, b) != b or reverse.setdefault(b, a) != a:
            return False
    return True


@dataclass
class MonitorSnapshot:
    """A point-in-time summary of an experiment's run database."""

    completed: int
    failed: int
    crashed: int
    expected_total: int | None
    design_cells: int
    replicates: int | None
    total_cost_usd: float
    total_tokens: float
    mean_duration_s: float | None
    wall_elapsed_s: float | None
    throughput_per_hour: float | None
    eta_seconds: float | None
    cells: list[CellProgress]
    recent: list[dict]
    failures: list[dict]
    generated_at: datetime

    @property
    def terminal(self) -> int:
        """Runs that hold a DATA POINT — ``completed`` (passed) or ``failed``
        (ran to completion but fell short of a gate). Both are real measurements
        and count as progress. ``crashed`` rows are excluded: the agent never
        completed, so the cell is retried and still needs a real attempt."""
        return self.completed + self.failed

    @property
    def remaining(self) -> int | None:
        """Slots still needing a real attempt: expected minus the cells that
        already hold a DATA POINT (``completed`` + ``failed``).

        A ``failed`` row IS progress — a completed run that the eval judged short
        of spec is a genuine measurement, not stale work awaiting retry. Only
        ``crashed`` cells (agent never completed) and never-run slots remain, so
        the ETA converges even when most cells fail their eval.
        """
        if self.expected_total is None:
            return None
        return max(self.expected_total - self.terminal, 0)

    @property
    def pct_complete(self) -> float | None:
        """Percent of expected runs that hold a data point (completed or failed)."""
        if not self.expected_total:
            return None
        return 100.0 * self.terminal / self.expected_total

    @property
    def all_terminal(self) -> bool:
        """True once every expected slot holds a data point (completed or
        failed) — i.e. no crashed or un-run cells remain."""
        if self.expected_total is None:
            return False
        return self.terminal >= self.expected_total

    @property
    def is_done(self) -> bool:
        """True when every expected cell holds a DATA POINT (completed or failed).

        A ``failed`` (completed-but-gate-short) run is a valid result, so it
        counts toward done — the experiment is finished once every cell has been
        measured, even if many measurements are failures. Only ``crashed`` cells
        (retried) keep a run un-done. ``--watch`` loops until this is true.
        """
        if self.expected_total is None:
            return False
        return self.terminal >= self.expected_total

    @property
    def eta_finish(self) -> datetime | None:
        if self.eta_seconds is None:
            return None
        return self.generated_at + _timedelta(self.eta_seconds)


def _timedelta(seconds: float):
    from datetime import timedelta

    return timedelta(seconds=seconds)


def build_snapshot(
    session: Session,
    *,
    replicates: int | None = None,
    expected_total: int | None = None,
    recent_n: int = 6,
    now: datetime | None = None,
) -> MonitorSnapshot:
    """Build a :class:`MonitorSnapshot` from the current database state.

    Args:
        session: Open SQLAlchemy session bound to a retort database.
        replicates: Replicates per cell. Used (with the design cell count) to
            compute ``expected_total`` when that is not given directly.
        expected_total: Total runs expected. Overrides the replicates-derived
            value when provided.
        recent_n: How many most-recently-finished completions to surface.
        now: Reference time for elapsed/ETA (defaults to ``datetime.now(utc)``;
            injectable for deterministic tests).

    Returns:
        A populated snapshot. Quality-metric means exclude failed runs.
    """
    now = now or datetime.now(timezone.utc)

    design_cells = session.query(DesignMatrixRow).count()

    runs = session.query(ExperimentRun).all()
    # Pre-load results once to avoid an N+1 query per run.
    results_by_run: dict[int, dict[str, float]] = {}
    for r in session.query(RunResult).all():
        results_by_run.setdefault(r.run_id, {})[r.metric_name] = r.value

    cells: dict[str, CellProgress] = {}
    metric_sums: dict[str, dict[str, list[float]]] = {}
    total_cost = 0.0
    total_tokens = 0.0
    durations: list[float] = []
    started_times: list[datetime] = []
    finished: list[tuple[datetime, ExperimentRun]] = []
    failures: list[dict] = []
    completed = failed = crashed = 0

    for run in runs:
        try:
            factors = json.loads(run.run_config_json or "{}")
        except (TypeError, ValueError):
            factors = {}
        if not isinstance(factors, dict):
            factors = {}
        label = _label(factors, run.id)
        str_factors = {k: str(v) for k, v in factors.items()}
        cell = cells.setdefault(label, CellProgress(factors=str_factors))
        res = results_by_run.get(run.id, {})

        status = run.status.value if hasattr(run.status, "value") else str(run.status)
        if status == RunStatus.crashed.value:
            # Agent never completed → no data point. Retried on --resume, so it
            # is NOT progress: don't count it toward the pace/ETA, list it as a
            # (retryable) failure for visibility.
            crashed += 1
            cell.crashed += 1
            failures.append(
                {
                    "label": label,
                    "factors": str_factors,
                    "replicate": run.replicate,
                    "error": (run.error_message or "") + "  [crashed — will retry]",
                    "duration_s": res.get(DURATION_METRIC),
                }
            )
            continue
        if status == RunStatus.failed.value:
            failed += 1
            cell.failed += 1
            failures.append(
                {
                    "label": label,
                    "factors": str_factors,
                    "replicate": run.replicate,
                    "error": run.error_message or "",
                    "duration_s": res.get(DURATION_METRIC),
                }
            )
            # A failed run IS a data point that took wall-clock time — count its
            # start toward the session pace so the ETA reflects the real rate at
            # which cells are being measured, not just the successful ones.
            if run.started_at is not None:
                started_times.append(_as_utc(run.started_at))
            continue
        if status != RunStatus.completed.value:
            # pending / running rows are not normally persisted; skip if present.
            continue

        completed += 1
        cell.completed += 1
        cost = res.get(COST_METRIC, 0.0) or 0.0
        toks = res.get(TOKENS_METRIC, 0.0) or 0.0
        total_cost += cost
        total_tokens += toks
        cell.cost_usd += cost
        cell.tokens += toks
        cell.max_context = max(cell.max_context, res.get(CONTEXT_METRIC) or 0)
        if DURATION_METRIC in res and res[DURATION_METRIC] is not None:
            durations.append(res[DURATION_METRIC])
            cell.duration_total_s += res[DURATION_METRIC]
        if run.started_at is not None:
            started_times.append(_as_utc(run.started_at))
        if run.finished_at is not None:
            finished.append((_as_utc(run.finished_at), run))

        # Accumulate quality-metric means (skip resource metrics).
        sums = metric_sums.setdefault(label, {})
        for name, val in res.items():
            if name in _RESOURCE_METRICS or val is None:
                continue
            sums.setdefault(name, []).append(val)

    for label, sums in metric_sums.items():
        cells[label].metric_means = {n: sum(v) / len(v) for n, v in sums.items() if v}

    if expected_total is None and replicates is not None and design_cells:
        expected_total = design_cells * replicates

    mean_duration = sum(durations) / len(durations) if durations else None

    wall_elapsed = None
    throughput = None
    eta = None
    if started_times:
        # Measure pace over the most recent contiguous run *session* only: a
        # --resume run carries old completed rows whose start times are hours or
        # days back, and dividing by that idle gap yields a uselessly low rate.
        # Split sessions on an idle gap between consecutive run starts.
        starts = sorted(started_times)
        session_start = starts[0]
        session_count = len(starts)
        for i in range(len(starts) - 1, 0, -1):
            if (starts[i] - starts[i - 1]).total_seconds() > _SESSION_GAP_S:
                session_start = starts[i]
                session_count = len(starts) - i
                break
        wall_elapsed = (now - session_start).total_seconds()
        if wall_elapsed > 0 and session_count > 0:
            throughput = session_count / (wall_elapsed / 3600.0)
            # Remaining = cells without a DATA POINT yet (completed + failed).
            # A failed run is a finished measurement, not outstanding work, so it
            # does not inflate the ETA; only crashed/un-run cells count as left.
            remaining = (
                max(expected_total - (completed + failed), 0)
                if expected_total is not None
                else None
            )
            if remaining:
                eta = remaining / throughput * 3600.0
            elif remaining == 0:
                eta = 0.0

    finished.sort(key=lambda t: t[0], reverse=True)
    recent = []
    for fin_dt, run in finished[:recent_n]:
        res = results_by_run.get(run.id, {})
        try:
            factors = json.loads(run.run_config_json or "{}")
        except (TypeError, ValueError):
            factors = {}
        recent.append(
            {
                "label": _label(factors, run.id),
                "factors": {k: str(v) for k, v in factors.items()},
                "replicate": run.replicate,
                "finished_at": fin_dt,
                "code_quality": res.get("code_quality"),
                "test_coverage": res.get("test_coverage"),
                "cost_usd": res.get(COST_METRIC),
                "duration_s": res.get(DURATION_METRIC),
            }
        )

    ordered_cells = sorted(cells.values(), key=lambda c: c.label)

    return MonitorSnapshot(
        completed=completed,
        failed=failed,
        crashed=crashed,
        expected_total=expected_total,
        design_cells=design_cells,
        replicates=replicates,
        total_cost_usd=total_cost,
        total_tokens=total_tokens,
        mean_duration_s=mean_duration,
        wall_elapsed_s=wall_elapsed,
        throughput_per_hour=throughput,
        eta_seconds=eta,
        cells=ordered_cells,
        recent=recent,
        failures=failures,
        generated_at=now,
    )


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def _fmt_tokens(tokens: float) -> str:
    if tokens >= 1e9:
        return f"{tokens / 1e9:.2f}B"
    if tokens >= 1e6:
        return f"{tokens / 1e6:.1f}M"
    if tokens >= 1e3:
        return f"{tokens / 1e3:.0f}K"
    return f"{tokens:.0f}"



def _short(entry: dict, keys: list[str]) -> str:
    """Cell label for a recent/failure entry, using only informative factors."""
    f = entry.get("factors")
    if not f or not keys:
        return str(entry.get("label", "?"))
    return "/".join(str(f.get(k, "")).replace("/", "-") for k in keys)


def render_active(active: list[dict]) -> list[str]:
    """Render the 'Active now' block from live in-flight run descriptors.

    Each descriptor: ``{"label": str, "replicate": int|None, "elapsed_s":
    float|None, "evaluating": bool, "context_tokens": int|None}``. Returns [] when
    there are no active runs.

    ``ctx`` is the context the run is carrying *right now* — watching it climb is
    how you catch a run ballooning toward non-termination while you can still act.
    """
    if not active:
        return []
    lines = [f"Active now ({len(active)}):"]
    for a in sorted(active, key=lambda x: x.get("label", "")):
        rep = f" rep{a['replicate']}" if a.get("replicate") is not None else ""
        elapsed = _fmt_duration(a.get("elapsed_s")) if a.get("elapsed_s") else "—"
        state = "evaluating" if a.get("evaluating") else "running"
        ctx = a.get("context_tokens")
        pk = a.get("context_peak")
        # Show the peak too: a context-managing agent (hermes-lcm) COMPACTS when it
        # crosses its budget, so a run that just churned 113K reads as a placid 6K.
        # "ctx 6K (pk 114K)" exposes the grow/compact cycle that current alone hides.
        if ctx and pk and pk > ctx * 1.2:
            ctx_s = f"  ctx {ctx/1000:.0f}K (pk {pk/1000:.0f}K)"
        elif ctx:
            ctx_s = f"  ctx {ctx/1000:.0f}K"
        else:
            ctx_s = ""
        lines.append(f"  ▶ {a.get('label', '?')}{rep}  {state} {elapsed}{ctx_s}")
    return lines


def render_text(
    snap: MonitorSnapshot,
    db_path: str | None = None,
    active: list[dict] | None = None,
) -> str:
    """Render a snapshot as a compact human-readable report."""
    lines: list[str] = []
    # All timestamps shown in the viewer's local timezone (%Z labels it).
    ts = snap.generated_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    header = "Retort run monitor"
    if db_path:
        header += f" — {db_path}"
    lines.append(f"{header}")
    lines.append(ts)
    lines.append("─" * 64)

    if snap.expected_total is not None:
        pct = snap.pct_complete or 0.0
        bar_w = 30
        # A cell is "measured" once it holds a data point (completed OR failed).
        frac = snap.terminal / snap.expected_total if snap.expected_total else 0
        filled = int(bar_w * frac)
        bar = "█" * filled + "·" * (bar_w - filled)
        lines.append(
            f"Progress   : {snap.terminal:>3} / {snap.expected_total:<3} measured "
            f"({pct:4.1f}%)  [{bar}]"
        )
        # Only crashed cells (agent never completed) are outstanding — they retry
        # on --resume. Passed and failed are both real, finished measurements.
        crash_note = (
            f"  ({snap.crashed} crashed — retry on --resume)" if snap.crashed else ""
        )
        lines.append(
            f"             {snap.completed} completed · {snap.failed} failed · "
            f"remaining={snap.remaining}{crash_note}"
        )
    else:
        lines.append(
            f"Progress   : {snap.completed} completed, {snap.failed} failed, "
            f"{snap.crashed} crashed (total unknown — pass --config or --total)"
        )

    lines.append(
        f"Resources  : ${snap.total_cost_usd:,.2f}   "
        f"{_fmt_tokens(snap.total_tokens)} tokens   "
        f"mean {_fmt_duration(snap.mean_duration_s)}/run"
    )
    tp = f"{snap.throughput_per_hour:.1f} runs/hr" if snap.throughput_per_hour else "—"
    eta = _fmt_duration(snap.eta_seconds) if snap.eta_seconds else "—"
    finish = ""
    if snap.eta_finish and snap.eta_seconds:
        finish = f"  (≈ {snap.eta_finish.astimezone().strftime('%H:%M %Z')})"
    lines.append(f"Throughput : {tp}   ·   ETA {eta}{finish}")
    if snap.design_cells:
        reps = f" × {snap.replicates} reps" if snap.replicates else ""
        lines.append(f"Design     : {snap.design_cells} cells{reps}")
    lines.append("")

    active_lines = render_active(active or [])
    if active_lines:
        lines.extend(active_lines)
        lines.append("")

    # Per-cell table. Label shows only the factors that actually distinguish
    # cells (constants and redundant duplicates are elided into a legend), and
    # the column is sized to the content so nothing overflows the header.
    reps = snap.replicates
    lines.append("Cells:")
    keys = informative_factors(snap.cells)
    labels = {id(c): c.display_label(keys) for c in snap.cells}
    width = min(max((len(v) for v in labels.values()), default=4), 44)

    # Legend: the factors held constant across every cell (dropped from labels).
    all_keys = sorted({k for c in snap.cells for k in c.factors})
    const = {
        k: str(snap.cells[0].factors.get(k))
        for k in all_keys
        if k not in keys and len({c.factors.get(k) for c in snap.cells}) == 1
    }
    if const:
        lines.append(
            "  (all cells: " + ", ".join(f"{k}={v}" for k, v in const.items()) + ")"
        )
    if keys:
        lines.append("  cell = " + "/".join(keys))

    lines.append(
        f"  {'cell':<{width}}  {'done':>5}  {'fail':>4}  {'crash':>5}  "
        f"{'cq':>4}  {'cov':>4}  {'~dur':>6}  {'pk ctx':>7}  {'$tot':>6}"
    )
    for c in snap.cells:
        lab = labels[id(c)]
        if len(lab) > width:
            lab = lab[: width - 1] + "…"
        done = f"{c.completed}/{reps}" if reps else str(c.completed)
        fail_s = f"✗{c.failed}" if c.failed else "·"
        crash_s = f"⚠{c.crashed}" if c.crashed else "·"
        cq = c.metric_means.get("code_quality")
        cov = c.metric_means.get("test_coverage")
        cq_s = f"{cq:.2f}" if cq is not None else "—"
        cov_s = f"{cov:.2f}" if cov is not None else "—"
        dur_s = _fmt_duration(c.mean_duration_s)  # mean wall-clock per run
        ctx_s = f"{c.max_context/1000:.0f}K" if c.max_context else "—"
        lines.append(
            f"  {lab:<{width}}  {done:>5}  {fail_s:>4}  {crash_s:>5}  "
            f"{cq_s:>4}  {cov_s:>4}  {dur_s:>6}  {ctx_s:>7}  ${c.cost_usd:>5.1f}"
        )
    lines.append("")

    if snap.recent:
        lines.append("Recent completions:")
        for r in snap.recent:
            qual = r["code_quality"]
            covg = r["test_coverage"]
            cst = r["cost_usd"]
            cq = f"cq={qual:.2f}" if qual is not None else "cq=—"
            cov = f"cov={covg:.2f}" if covg is not None else "cov=—"
            cost = f"${cst:.2f}" if cst is not None else "$—"
            dur = _fmt_duration(r["duration_s"])
            fin = r["finished_at"]
            ts = fin.astimezone().strftime("%m-%d %H:%M %Z") if fin else "   —   "
            lines.append(
                f"  ✓ {ts}  {_short(r, keys)} rep{r['replicate']}  {cq} {cov}  {cost}  {dur}"
            )
        lines.append("")

    if snap.failures:
        n = len(snap.failures)
        shown = snap.failures[-_MAX_FAILURES_SHOWN:]
        hidden = n - len(shown)
        suffix = f" — showing last {len(shown)} of {n}" if hidden else ""
        lines.append(f"Failures ({n}){suffix}:")
        for f in shown:
            err = (f["error"] or "").splitlines()[0][:80] if f["error"] else ""
            dur = f" ({_fmt_duration(f.get('duration_s'))})" if f.get("duration_s") else ""
            lines.append(f"  ✗ {_short(f, keys)} rep{f['replicate']}{dur}  {err}")
    else:
        lines.append("Failures   : none")

    return "\n".join(lines)


def render_json(snap: MonitorSnapshot, active: list[dict] | None = None) -> str:
    """Render a snapshot as JSON (machine-readable)."""

    def _iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    data = {
        "generated_at": _iso(snap.generated_at),
        "active": active or [],
        "completed": snap.completed,
        "failed": snap.failed,
        "crashed": snap.crashed,
        "measured": snap.terminal,
        "remaining": snap.remaining,
        "expected_total": snap.expected_total,
        "pct_complete": snap.pct_complete,
        "design_cells": snap.design_cells,
        "replicates": snap.replicates,
        "is_done": snap.is_done,
        "total_cost_usd": round(snap.total_cost_usd, 4),
        "total_tokens": snap.total_tokens,
        "mean_duration_s": snap.mean_duration_s,
        "throughput_per_hour": snap.throughput_per_hour,
        "eta_seconds": snap.eta_seconds,
        "eta_finish": _iso(snap.eta_finish),
        "cells": [
            {
                "label": c.label,
                "factors": c.factors,
                "completed": c.completed,
                "failed": c.failed,
                "cost_usd": round(c.cost_usd, 4),
                "tokens": c.tokens,
                "mean_duration_s": c.mean_duration_s,
                "metric_means": {k: round(v, 4) for k, v in c.metric_means.items()},
            }
            for c in snap.cells
        ],
        "recent": [
            {**r, "finished_at": _iso(r["finished_at"])} for r in snap.recent
        ],
        "failures": snap.failures,
    }
    return json.dumps(data, indent=2)
