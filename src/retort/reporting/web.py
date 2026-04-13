"""Static HTML report generation for retort experiments.

Outputs a self-contained directory of HTML + CSS that can be served
locally (`python -m http.server`) or pushed to GitHub Pages. No JS
framework — a small inline script makes the leaderboard table sortable.

Layout:

  <out>/
    index.html              — landing page: experiment summary + sortable
                              leaderboard ranked by maturity
    style.css               — shared stylesheet
    stacks/<sig>.html       — per-stack drill-down (public mode only)

The stacks/ pages are skipped in private mode to avoid leaking generated
code paths or finding contents.
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from retort.analysis.maturity import (
    StackMaturity,
    classify_phase,
    compute_stack_maturity,
)
from retort.reporting.code_summary import CodeSummary, summarize_archive
from retort.storage.database import get_engine, get_session_factory
from retort.storage.models import ExperimentRun, RunResult, RunStatus


_STYLE = """\
:root {
  --bg: #fafafa;
  --fg: #222;
  --muted: #666;
  --accent: #2563eb;
  --border: #e5e7eb;
  --header-bg: #f3f4f6;
  --row-alt: #fafbfc;
  --good: #16a34a;
  --warn: #ca8a04;
  --bad: #dc2626;
}
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       margin: 0 auto; max-width: 1100px; padding: 2rem 1rem;
       background: var(--bg); color: var(--fg); }
h1, h2, h3 { line-height: 1.2; }
h1 { margin: 0 0 0.25rem 0; font-size: 1.75rem; }
.subtitle { color: var(--muted); margin: 0 0 2rem 0; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
           gap: 1rem; margin: 1rem 0 2rem; }
.summary-item { background: white; border: 1px solid var(--border); border-radius: 6px;
                padding: 0.75rem 1rem; }
.summary-item .label { color: var(--muted); font-size: 0.85rem; }
.summary-item .value { font-size: 1.25rem; font-weight: 600; margin-top: 0.25rem; }
table { width: 100%; border-collapse: collapse; background: white;
        border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }
th { background: var(--header-bg); font-weight: 600; cursor: pointer; user-select: none; }
th.numeric, td.numeric { text-align: right; font-variant-numeric: tabular-nums; }
tr:nth-child(even) { background: var(--row-alt); }
tr:hover { background: #eff6ff; }
.phase { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 3px;
         font-size: 0.8rem; font-weight: 600; }
.phase-production { background: #dcfce7; color: #166534; }
.phase-trial      { background: #fef3c7; color: #92400e; }
.phase-screening  { background: #dbeafe; color: #1e40af; }
.phase-candidate  { background: #f3f4f6; color: #4b5563; }
.muted { color: var(--muted); font-size: 0.85rem; }
.factors { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 0.85rem; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.notice { background: #fef3c7; border: 1px solid #fcd34d; border-radius: 6px;
          padding: 0.75rem 1rem; margin: 1rem 0; }
details.code-summary { background: #fafbfc; border: 1px solid var(--border);
                       border-radius: 6px; padding: 0.5rem 0.75rem; margin: 0.4rem 0; }
details.code-summary > summary { cursor: pointer; user-select: none;
                                 font-family: ui-monospace, monospace; font-size: 0.9rem; }
details.code-summary > summary::marker { color: var(--muted); }
.code-files { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 0.85rem;
              margin: 0.5rem 0; }
.code-files .file { margin: 0.25rem 0 0.25rem 1rem; }
.code-files .file-name { font-weight: 600; }
.code-files .symbols { color: var(--muted); margin-left: 1.5rem; word-spacing: 0.5em; }
.code-files .test { color: #166534; }
"""

_SORT_SCRIPT = """\
document.querySelectorAll('table.sortable').forEach(t => {
  const headers = t.querySelectorAll('thead th');
  headers.forEach((h, idx) => {
    h.addEventListener('click', () => {
      const tbody = t.tBodies[0];
      const rows = Array.from(tbody.rows);
      const numeric = h.classList.contains('numeric');
      const dir = h.dataset.dir === 'asc' ? 'desc' : 'asc';
      rows.sort((a, b) => {
        let av = a.cells[idx].dataset.sortKey ?? a.cells[idx].textContent;
        let bv = b.cells[idx].dataset.sortKey ?? b.cells[idx].textContent;
        if (numeric) { av = parseFloat(av) || 0; bv = parseFloat(bv) || 0; }
        return (av < bv ? -1 : av > bv ? 1 : 0) * (dir === 'asc' ? 1 : -1);
      });
      headers.forEach(x => delete x.dataset.dir);
      h.dataset.dir = dir;
      rows.forEach(r => tbody.appendChild(r));
    });
  });
});
"""


def generate_web_report(
    *,
    db_path: Path,
    output_dir: Path,
    title: str | None = None,
    visibility: str = "public",
    experiment_dir: Path | None = None,
    anova_path: Path | None = None,
) -> int:
    """Render the experiment as static HTML. Returns number of pages written.

    experiment_dir is used to locate per-run archives at
    ``<experiment_dir>/runs/<cell>/rep<N>/summary/index.md``. Defaults to
    the database's parent directory.

    anova_path optionally points at a pre-rendered ANOVA text file (the
    output of ``retort analyze``) to inline on the index. Defaults to
    ``<experiment_dir>/reports/anova.txt`` if it exists.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "style.css").write_text(_STYLE)

    if experiment_dir is None:
        experiment_dir = db_path.parent
    if anova_path is None:
        candidate = experiment_dir / "reports" / "anova.txt"
        anova_path = candidate if candidate.exists() else None

    engine = get_engine(db_path)
    session = get_session_factory(engine)()
    try:
        stacks = compute_stack_maturity(session)
        runs = session.query(ExperimentRun).all()
        results_by_run: dict[int, list[RunResult]] = {}
        for r in session.query(RunResult).all():
            results_by_run.setdefault(r.run_id, []).append(r)
    finally:
        session.close()
        engine.dispose()

    page_title = title or _infer_title(db_path)

    # index.html
    anova_text = anova_path.read_text() if anova_path else None
    index_html = _render_index(
        page_title=page_title,
        stacks=stacks,
        runs=runs,
        results_by_run=results_by_run,
        visibility=visibility,
        anova_text=anova_text,
    )
    (output_dir / "index.html").write_text(index_html)
    n_pages = 1

    # Per-stack drill-downs (public mode only). Private mode keeps the
    # leaderboard but doesn't expose per-stack details.
    if visibility == "public":
        stacks_dir = output_dir / "stacks"
        stacks_dir.mkdir(exist_ok=True)
        for stack in stacks:
            slug = _slug(stack.stack_signature)
            html_str = _render_stack_page(
                page_title=page_title,
                stack=stack,
                runs=runs,
                results_by_run=results_by_run,
                experiment_dir=experiment_dir,
            )
            (stacks_dir / f"{slug}.html").write_text(html_str)
            n_pages += 1

    return n_pages


_RESPONSE_METRICS_LAST: tuple[str, ...] = ()  # (placeholder for future config)


def _split_metrics(metric_names: list[str]) -> tuple[list[str], list[str]]:
    """Partition into (response metrics, side-channel telemetry).

    Telemetry metrics use a leading underscore by convention (set in
    cli._store_run_result). Everything else is a configured response.
    """
    responses = sorted(m for m in metric_names if not m.startswith("_"))
    telemetry = sorted(m for m in metric_names if m.startswith("_"))
    return responses, telemetry


_TELEMETRY_LABELS: dict[str, str] = {
    "_tokens": "tokens",
    "_cost_usd": "cost ($)",
    "_duration_seconds": "duration (s)",
}


def _format_metric(name: str, value: float) -> str:
    """Render a metric value with sensible units per name."""
    if name == "_tokens":
        return f"{int(value):,}"
    if name == "_cost_usd":
        return f"${value:.4f}"
    if name == "_duration_seconds":
        return f"{value:.1f}s"
    return f"{value:.3f}"


def _cell_dir_name(factors: dict[str, str]) -> str:
    """Match cli._archive_run_workspace's directory naming."""
    return "_".join(f"{k}={v}" for k, v in sorted(factors.items()))


def _summary_link(experiment_dir: Path, factors: dict[str, str], replicate: int) -> str | None:
    """Return a relative URL to the run-summary skill output if it exists.

    Looks at <experiment_dir>/runs/<cell>/rep<N>/summary/index.md. Returns
    a path relative to the rendered stacks/<slug>.html page, or None if no
    summary exists.
    """
    cell = _cell_dir_name(factors)
    rel = f"../../runs/{cell}/rep{replicate}/summary/index.md"
    abs_target = experiment_dir / "runs" / cell / f"rep{replicate}" / "summary" / "index.md"
    if abs_target.exists():
        return rel
    return None


def _archive_dir(
    experiment_dir: Path,
    factors: dict[str, str],
    replicate: int,
    status_label: str,
) -> Path:
    """Mirror cli._archive_run_workspace's path layout."""
    cell = _cell_dir_name(factors)
    suffix = "" if status_label == "completed" else "-failed"
    return experiment_dir / "runs" / cell / f"rep{replicate}{suffix}"


def _render_code_summary_block(replicate: int, code: CodeSummary) -> str:
    """Render a <details> block listing files + symbols for one replicate."""
    items: list[str] = []
    for f in code.files:
        cls = "file test" if f.is_test else "file"
        symbols = ""
        if f.symbols:
            symbols = (
                '<div class="symbols">'
                + html.escape(", ".join(f.symbols[:30]))
                + ("…" if len(f.symbols) > 30 else "")
                + "</div>"
            )
        items.append(
            f'<div class="{cls}">'
            f'<span class="file-name">{html.escape(f.relpath)}</span>'
            f' <span class="muted">({f.loc} loc{", test" if f.is_test else ""})</span>'
            f'{symbols}</div>'
        )

    summary_line = (
        f"rep {replicate} — {code.n_files} file(s), {code.total_loc} loc"
    )
    if code.n_test_files:
        summary_line += f" ({code.n_test_files} test file(s), {code.test_loc} test loc)"

    return (
        f'<details class="code-summary">'
        f'<summary>{html.escape(summary_line)}</summary>'
        f'<div class="code-files">{"".join(items)}</div>'
        f'</details>'
    )


def _infer_title(db_path: Path) -> str:
    return f"Retort: {db_path.parent.name}"


def _slug(signature: str) -> str:
    return hashlib.sha1(signature.encode()).hexdigest()[:10]


def _fmt_optional(v: float | None) -> str:
    return f"{v:.3f}" if v is not None else "n/a"


def _stack_telemetry(
    stack: StackMaturity,
    runs: list,
    results_by_run: dict[int, list],
) -> dict[str, float | None]:
    """Per-stack mean tokens/cost/duration. None when no data."""
    sig = stack.stack_signature
    tokens: list[float] = []
    cost: list[float] = []
    duration: list[float] = []
    for run in runs:
        try:
            run_sig = json.dumps(json.loads(run.run_config_json or "{}"), sort_keys=True)
        except (TypeError, ValueError):
            continue
        if run_sig != sig:
            continue
        for res in results_by_run.get(run.id, []):
            if res.value is None:
                continue
            if res.metric_name == "_tokens":
                tokens.append(float(res.value))
            elif res.metric_name == "_cost_usd":
                cost.append(float(res.value))
            elif res.metric_name == "_duration_seconds":
                duration.append(float(res.value))
    return {
        "tokens_mean": (sum(tokens) / len(tokens)) if tokens else None,
        "cost_mean": (sum(cost) / len(cost)) if cost else None,
        "duration_mean": (sum(duration) / len(duration)) if duration else None,
    }


def _render_index(
    *,
    page_title: str,
    stacks: list[StackMaturity],
    runs: list,
    results_by_run: dict[int, list],
    visibility: str,
    anova_text: str | None = None,
) -> str:
    n_runs = len(runs)
    n_completed = sum(1 for r in runs if r.status == RunStatus.completed)
    n_failed = sum(1 for r in runs if r.status == RunStatus.failed)

    metric_names = sorted({
        res.metric_name for results in results_by_run.values() for res in results
    })

    # Roll up tokens + cost across the whole experiment.
    total_tokens = 0
    total_cost = 0.0
    for results in results_by_run.values():
        for res in results:
            if res.metric_name == "_tokens":
                total_tokens += int(res.value or 0)
            elif res.metric_name == "_cost_usd":
                total_cost += float(res.value or 0)

    summary_items = [
        ("Stacks", len(stacks)),
        ("Runs", n_runs),
        ("Completed", n_completed),
        ("Failed", n_failed),
        ("Metrics", len(metric_names)),
    ]
    if total_tokens:
        summary_items.append(("Tokens (total)", f"{total_tokens:,}"))
    if total_cost:
        summary_items.append(("Cost (total)", f"${total_cost:.2f}"))
    if visibility == "private":
        summary_items.append(("Visibility", "private"))

    summary_html = "\n".join(
        f'<div class="summary-item"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(str(value))}</div></div>'
        for label, value in summary_items
    )

    if not stacks:
        rows_html = '<tr><td colspan="9" class="muted">No stacks yet.</td></tr>'
    else:
        rows_html = "\n".join(
            _render_stack_row(s, visibility, _stack_telemetry(s, runs, results_by_run))
            for s in stacks
        )

    if anova_text:
        anova_section = (
            '<h2>ANOVA</h2>'
            '<p class="muted">From <code>retort analyze</code> on the exported CSV. '
            'Significant factors are flagged at the bottom of each response section.</p>'
            f'<pre style="background:white;border:1px solid var(--border);'
            f'border-radius:6px;padding:0.75rem 1rem;overflow:auto;font-size:0.85rem;">'
            f'{html.escape(anova_text)}</pre>'
        )
    else:
        anova_section = ""

    notice = ""
    if visibility == "private":
        notice = (
            '<div class="notice">'
            'This is a <strong>private</strong> experiment. Per-stack drill-down '
            'pages with generated code and findings are intentionally not '
            'rendered. Aggregate metrics only.'
            '</div>'
        )

    body = f"""
<h1>{html.escape(page_title)}</h1>
<p class="subtitle">Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}</p>
{notice}
<div class="summary">{summary_html}</div>

<h2>Stack maturity</h2>
<p class="muted">
  Click any column header to sort. Tokens / Cost / Duration are
  per-replicate means — sort ascending to find the most efficient stacks
  at a given quality level.
</p>
<table class="sortable">
  <thead><tr>
    <th class="numeric" data-dir="desc">Maturity</th>
    <th>Phase</th>
    <th>Stack</th>
    <th class="numeric">n</th>
    <th class="numeric">code_quality</th>
    <th class="numeric">tokens (mean)</th>
    <th class="numeric">cost (mean)</th>
    <th class="numeric">duration (mean)</th>
    <th class="numeric">$/quality</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>

<p class="muted">Click a column header to sort. <a href="https://github.com/adrianco/retort">retort</a> · maturity = 0.30·agreement + 0.30·completion + 0.25·score + 0.15·coverage</p>
{anova_section}
<script>
{_SORT_SCRIPT}
</script>
"""
    return _PAGE_TEMPLATE.format(
        title=html.escape(page_title),
        css="style.css",
        body=body,
    )


def _render_stack_row(
    stack: StackMaturity,
    visibility: str,
    telemetry: dict[str, float | None],
) -> str:
    factors_str = ", ".join(f"{k}={v}" for k, v in stack.factors.items())
    phase = classify_phase(stack.maturity)
    if visibility == "public":
        link = f'<a href="stacks/{_slug(stack.stack_signature)}.html">{html.escape(factors_str)}</a>'
    else:
        link = html.escape(factors_str)
    score_cell = (
        f'<span data-sort-key="{stack.headline_mean:.3f}">{stack.headline_mean:.3f}</span>'
        if stack.headline_mean is not None
        else '<span class="muted" data-sort-key="0">n/a</span>'
    )

    def _num_cell(value: float | None, fmt: str, sort_key: float | None = None) -> str:
        if value is None:
            return '<td class="numeric muted" data-sort-key="999999999">—</td>'
        key = sort_key if sort_key is not None else value
        return f'<td class="numeric" data-sort-key="{key}">{fmt.format(value)}</td>'

    tokens_cell = _num_cell(telemetry["tokens_mean"], "{:,.0f}")
    cost_cell = _num_cell(telemetry["cost_mean"], "${:.4f}")
    duration_cell = _num_cell(telemetry["duration_mean"], "{:.1f}s")

    # $/quality — lower is better (more quality per dollar).
    if telemetry["cost_mean"] and stack.headline_mean and stack.headline_mean > 0:
        cost_per_quality = telemetry["cost_mean"] / stack.headline_mean
        cpq_cell = (
            f'<td class="numeric" data-sort-key="{cost_per_quality:.4f}">'
            f'${cost_per_quality:.4f}</td>'
        )
    else:
        cpq_cell = '<td class="numeric muted" data-sort-key="999999999">—</td>'

    return f"""\
<tr>
  <td class="numeric" data-sort-key="{stack.maturity:.4f}">{stack.maturity:.3f}</td>
  <td><span class="phase phase-{phase}">{phase}</span></td>
  <td class="factors">{link}</td>
  <td class="numeric" data-sort-key="{stack.n_replicates}">{stack.n_completed}/{stack.n_replicates}</td>
  <td class="numeric">{score_cell}</td>
  {tokens_cell}
  {cost_cell}
  {duration_cell}
  {cpq_cell}
</tr>"""


def _render_stack_page(
    *,
    page_title: str,
    stack: StackMaturity,
    runs: list,
    results_by_run: dict[int, list],
    experiment_dir: Path,
) -> str:
    factors_str = ", ".join(f"{k}={v}" for k, v in stack.factors.items())
    phase = classify_phase(stack.maturity)

    # Find runs belonging to this stack (matching signature).
    stack_runs = []
    for run in runs:
        try:
            sig = json.dumps(json.loads(run.run_config_json or "{}"), sort_keys=True)
        except (TypeError, ValueError):
            continue
        if sig == stack.stack_signature:
            stack_runs.append(run)
    stack_runs.sort(key=lambda r: r.replicate)

    metric_names = sorted({
        res.metric_name for r in stack_runs for res in results_by_run.get(r.id, [])
    })
    response_metrics, telemetry_metrics = _split_metrics(metric_names)

    def _column_label(name: str) -> str:
        return _TELEMETRY_LABELS.get(name, name)

    headers = "".join(
        f'<th class="numeric">{html.escape(_column_label(m))}</th>'
        for m in response_metrics + telemetry_metrics
    )
    headers = (
        '<th class="numeric">Run</th><th>Rep</th><th>Status</th>'
        + headers
        + '<th class="numeric">Files</th><th class="numeric">LOC</th>'
    )

    language = stack.factors.get("language", "")
    rows = []
    code_blocks: list[str] = []
    total_cost = 0.0
    total_tokens = 0
    for run in stack_runs:
        scores = {res.metric_name: res.value for res in results_by_run.get(run.id, [])}
        if "_tokens" in scores:
            total_tokens += int(scores["_tokens"])
        if "_cost_usd" in scores:
            total_cost += scores["_cost_usd"]
        cells = "".join(
            f'<td class="numeric">{_format_metric(m, scores[m])}</td>' if m in scores
            else '<td class="numeric muted">—</td>'
            for m in response_metrics + telemetry_metrics
        )
        status_label = run.status.value if hasattr(run.status, "value") else str(run.status)

        archive_dir = _archive_dir(experiment_dir, stack.factors, run.replicate, status_label)
        code = summarize_archive(archive_dir, language)
        if code is not None:
            files_cell = f'<td class="numeric">{code.n_files}</td>'
            loc_cell = f'<td class="numeric">{code.total_loc}</td>'
            code_blocks.append(_render_code_summary_block(run.replicate, code))
        else:
            files_cell = '<td class="numeric muted">—</td>'
            loc_cell = '<td class="numeric muted">—</td>'

        rows.append(
            f"<tr><td>{run.id}</td><td>rep {run.replicate}</td>"
            f"<td>{html.escape(status_label)}</td>{cells}{files_cell}{loc_cell}</tr>"
        )
    rows_html = "\n".join(rows) or '<tr><td colspan="99" class="muted">No runs.</td></tr>'
    code_html = "\n".join(code_blocks) if code_blocks else (
        '<p class="muted">No archived workspaces found for this stack — '
        'either the runs predate the archival fix or the runs/ directory '
        'is gitignored in this view.</p>'
    )

    # Aggregate summary cards.
    cards = [
        ("Replicates", f"{stack.n_completed}/{stack.n_replicates}"),
        ("Completion", f"{stack.completion_rate * 100:.0f}%"),
        ("Replicate agreement", f"{stack.replicate_agreement:.2f}"),
        (stack.headline_metric, _fmt_optional(stack.headline_mean)),
    ]
    if total_tokens:
        cards.append(("Tokens (total)", f"{total_tokens:,}"))
    if total_cost:
        cards.append(("Cost (total)", f"${total_cost:.4f}"))
    summary_html = "\n".join(
        f'<div class="summary-item"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(str(value))}</div></div>'
        for label, value in cards
    )

    return _PAGE_TEMPLATE.format(
        title=html.escape(f"{page_title} · {factors_str}"),
        css="../style.css",
        body=f"""
<p class="muted"><a href="../index.html">&larr; index</a></p>
<h1>{html.escape(factors_str)}</h1>
<p class="subtitle">
  <span class="phase phase-{phase}">{phase}</span>
  &nbsp;maturity {stack.maturity:.3f}
</p>

<div class="summary">{summary_html}</div>

<h2>Runs</h2>
<table>
  <thead><tr>{headers}</tr></thead>
  <tbody>{rows_html}</tbody>
</table>

<h2>Code review</h2>
<p class="muted">
  Per-replicate file listing extracted from the archived workspace.
  For semantic analysis (architecture, interfaces, control flow), invoke
  the <code>run-summary</code> skill via <code>retort evaluate &lt;run_dir&gt;</code>.
</p>
{code_html}

<p class="muted">
  Stack signature (sorted JSON): <code>{html.escape(stack.stack_signature)}</code>
</p>
""",
    )


_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="{css}">
</head>
<body>{body}</body>
</html>
"""
