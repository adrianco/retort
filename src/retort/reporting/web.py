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
) -> int:
    """Render the experiment as static HTML. Returns number of pages written."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "style.css").write_text(_STYLE)

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
    index_html = _render_index(
        page_title=page_title,
        stacks=stacks,
        runs=runs,
        results_by_run=results_by_run,
        visibility=visibility,
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
            )
            (stacks_dir / f"{slug}.html").write_text(html_str)
            n_pages += 1

    return n_pages


def _infer_title(db_path: Path) -> str:
    return f"Retort: {db_path.parent.name}"


def _slug(signature: str) -> str:
    return hashlib.sha1(signature.encode()).hexdigest()[:10]


def _fmt_optional(v: float | None) -> str:
    return f"{v:.3f}" if v is not None else "n/a"


def _render_index(
    *,
    page_title: str,
    stacks: list[StackMaturity],
    runs: list,
    results_by_run: dict[int, list],
    visibility: str,
) -> str:
    n_runs = len(runs)
    n_completed = sum(1 for r in runs if r.status == RunStatus.completed)
    n_failed = sum(1 for r in runs if r.status == RunStatus.failed)

    metric_names = sorted({
        res.metric_name for results in results_by_run.values() for res in results
    })

    summary_items = [
        ("Stacks", len(stacks)),
        ("Runs", n_runs),
        ("Completed", n_completed),
        ("Failed", n_failed),
        ("Metrics", len(metric_names)),
    ]
    if visibility == "private":
        summary_items.append(("Visibility", "private"))

    summary_html = "\n".join(
        f'<div class="summary-item"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(str(value))}</div></div>'
        for label, value in summary_items
    )

    if not stacks:
        rows_html = '<tr><td colspan="6" class="muted">No stacks yet.</td></tr>'
    else:
        rows_html = "\n".join(_render_stack_row(s, visibility) for s in stacks)

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
<table class="sortable">
  <thead><tr>
    <th class="numeric" data-dir="desc">Maturity</th>
    <th>Phase</th>
    <th>Stack</th>
    <th class="numeric">Replicates</th>
    <th class="numeric">Completion</th>
    <th class="numeric">code_quality</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>

<p class="muted">Click a column header to sort. <a href="https://github.com/adrianco/retort">retort</a> · maturity = 0.30·agreement + 0.30·completion + 0.25·score + 0.15·coverage</p>
<script>
{_SORT_SCRIPT}
</script>
"""
    return _PAGE_TEMPLATE.format(
        title=html.escape(page_title),
        css="style.css",
        body=body,
    )


def _render_stack_row(stack: StackMaturity, visibility: str) -> str:
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
    return f"""\
<tr>
  <td class="numeric" data-sort-key="{stack.maturity:.4f}">{stack.maturity:.3f}</td>
  <td><span class="phase phase-{phase}">{phase}</span></td>
  <td class="factors">{link}</td>
  <td class="numeric" data-sort-key="{stack.n_replicates}">{stack.n_completed}/{stack.n_replicates}</td>
  <td class="numeric" data-sort-key="{stack.completion_rate:.3f}">{stack.completion_rate * 100:.0f}%</td>
  <td class="numeric">{score_cell}</td>
</tr>"""


def _render_stack_page(
    *,
    page_title: str,
    stack: StackMaturity,
    runs: list,
    results_by_run: dict[int, list],
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

    # Build runs table.
    metric_names = sorted({
        res.metric_name for r in stack_runs for res in results_by_run.get(r.id, [])
    })
    headers = "".join(f'<th class="numeric">{html.escape(m)}</th>' for m in metric_names)
    rows = []
    for run in stack_runs:
        scores = {res.metric_name: res.value for res in results_by_run.get(run.id, [])}
        cells = "".join(
            f'<td class="numeric">{scores[m]:.3f}</td>' if m in scores
            else '<td class="numeric muted">—</td>'
            for m in metric_names
        )
        status_label = run.status.value if hasattr(run.status, "value") else str(run.status)
        rows.append(
            f"<tr><td>{run.id}</td><td>rep {run.replicate}</td>"
            f"<td>{html.escape(status_label)}</td>{cells}</tr>"
        )
    rows_html = "\n".join(rows) or '<tr><td colspan="99" class="muted">No runs.</td></tr>'

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

<div class="summary">
  <div class="summary-item"><div class="label">Replicates</div>
       <div class="value">{stack.n_completed}/{stack.n_replicates}</div></div>
  <div class="summary-item"><div class="label">Completion</div>
       <div class="value">{stack.completion_rate * 100:.0f}%</div></div>
  <div class="summary-item"><div class="label">Replicate agreement</div>
       <div class="value">{stack.replicate_agreement:.2f}</div></div>
  <div class="summary-item"><div class="label">{html.escape(stack.headline_metric)}</div>
       <div class="value">{_fmt_optional(stack.headline_mean)}</div></div>
</div>

<h2>Runs</h2>
<table>
  <thead><tr>
    <th>Run ID</th><th>Replicate</th><th>Status</th>{headers}
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>

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
