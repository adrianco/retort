"""Export effects reports to JSON, CSV, text, and HTML formats."""

from __future__ import annotations

import csv
import html as html_mod
import io
import json
from typing import TextIO

from retort.reporting.effects import EffectsReport


def to_text(report: EffectsReport, out: TextIO | None = None) -> str:
    """Render an effects report as human-readable text.

    Args:
        report: The effects report to render.
        out: Optional file-like object to write to. If None, returns string.

    Returns:
        The rendered text.
    """
    lines: list[str] = []
    lines.append(f"Effects Report: {report.design_name}")
    lines.append(f"Metric: {report.metric}")
    lines.append(f"Runs analyzed: {report.n_runs}")
    lines.append(f"Grand mean: {report.grand_mean:.4f}")
    lines.append("")

    # Main effects
    lines.append("Main Effects")
    lines.append("-" * 60)
    for me in report.main_effects:
        lines.append(f"  {me.factor} (range: {me.effect_range:.4f})")
        for level, mean in sorted(me.level_means.items()):
            delta = mean - me.grand_mean
            sign = "+" if delta >= 0 else ""
            lines.append(f"    {level:20s}  mean={mean:.4f}  ({sign}{delta:.4f})")
        lines.append("")

    # Interactions
    if report.interactions:
        lines.append("Interaction Effects")
        lines.append("-" * 60)
        for ie in report.interactions:
            lines.append(f"  {ie.factor_a} x {ie.factor_b}")
            for (la, lb), mean in sorted(ie.cell_means.items()):
                delta = mean - ie.grand_mean
                sign = "+" if delta >= 0 else ""
                lines.append(
                    f"    {la:15s} x {lb:15s}  mean={mean:.4f}  ({sign}{delta:.4f})"
                )
            lines.append("")

    text = "\n".join(lines)
    if out is not None:
        out.write(text)
    return text


def to_json(report: EffectsReport) -> str:
    """Serialize an effects report to JSON."""
    data = {
        "design_name": report.design_name,
        "metric": report.metric,
        "n_runs": report.n_runs,
        "grand_mean": report.grand_mean,
        "main_effects": [
            {
                "factor": me.factor,
                "effect_range": me.effect_range,
                "level_means": me.level_means,
            }
            for me in report.main_effects
        ],
        "interactions": [
            {
                "factor_a": ie.factor_a,
                "factor_b": ie.factor_b,
                "cell_means": {
                    f"{la}|{lb}": v for (la, lb), v in ie.cell_means.items()
                },
            }
            for ie in report.interactions
        ],
    }
    return json.dumps(data, indent=2)


def to_csv(report: EffectsReport) -> str:
    """Export main effects as CSV rows.

    Columns: factor, level, mean, delta_from_grand_mean, effect_range
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["factor", "level", "mean", "delta", "effect_range"])
    for me in report.main_effects:
        for level, mean in sorted(me.level_means.items()):
            writer.writerow([
                me.factor,
                level,
                f"{mean:.6f}",
                f"{mean - me.grand_mean:.6f}",
                f"{me.effect_range:.6f}",
            ])
    return buf.getvalue()


def to_html(report: EffectsReport) -> str:
    """Render an effects report as a self-contained HTML page.

    The output is a complete HTML document suitable for sharing via
    email, browser, or embedding in dashboards.

    Args:
        report: The effects report to render.

    Returns:
        A complete HTML document as a string.
    """
    esc = html_mod.escape

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8">')
    parts.append(f"<title>Effects Report: {esc(report.design_name)}</title>")
    parts.append("<style>")
    parts.append(_HTML_STYLE)
    parts.append("</style>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append(f"<h1>Effects Report: {esc(report.design_name)}</h1>")
    parts.append('<div class="meta">')
    parts.append(f"<p>Metric: <strong>{esc(report.metric)}</strong></p>")
    parts.append(f"<p>Runs analyzed: {report.n_runs}</p>")
    parts.append(f"<p>Grand mean: {report.grand_mean:.4f}</p>")
    parts.append("</div>")

    # Main effects table
    parts.append("<h2>Main Effects</h2>")
    parts.append("<table>")
    parts.append("<thead><tr>")
    parts.append("<th>Factor</th><th>Level</th><th>Mean</th>")
    parts.append("<th>Delta</th><th>Effect Range</th>")
    parts.append("</tr></thead>")
    parts.append("<tbody>")
    for me in report.main_effects:
        first = True
        sorted_levels = sorted(me.level_means.items())
        for level, mean in sorted_levels:
            delta = mean - me.grand_mean
            sign = "+" if delta >= 0 else ""
            parts.append("<tr>")
            if first:
                rowspan = len(sorted_levels)
                parts.append(
                    f'<td rowspan="{rowspan}">{esc(me.factor)}</td>'
                )
            parts.append(f"<td>{esc(level)}</td>")
            parts.append(f"<td>{mean:.4f}</td>")
            cls = "positive" if delta >= 0 else "negative"
            parts.append(f'<td class="{cls}">{sign}{delta:.4f}</td>')
            if first:
                parts.append(
                    f'<td rowspan="{rowspan}">{me.effect_range:.4f}</td>'
                )
                first = False
            parts.append("</tr>")
    parts.append("</tbody></table>")

    # Interaction effects table
    if report.interactions:
        parts.append("<h2>Interaction Effects</h2>")
        parts.append("<table>")
        parts.append("<thead><tr>")
        parts.append("<th>Factor A</th><th>Factor B</th>")
        parts.append("<th>Level A</th><th>Level B</th>")
        parts.append("<th>Mean</th><th>Delta</th>")
        parts.append("</tr></thead>")
        parts.append("<tbody>")
        for ie in report.interactions:
            first = True
            sorted_cells = sorted(ie.cell_means.items())
            for (la, lb), mean in sorted_cells:
                delta = mean - ie.grand_mean
                sign = "+" if delta >= 0 else ""
                parts.append("<tr>")
                if first:
                    rowspan = len(sorted_cells)
                    parts.append(
                        f'<td rowspan="{rowspan}">{esc(ie.factor_a)}</td>'
                    )
                    parts.append(
                        f'<td rowspan="{rowspan}">{esc(ie.factor_b)}</td>'
                    )
                parts.append(f"<td>{esc(la)}</td>")
                parts.append(f"<td>{esc(lb)}</td>")
                parts.append(f"<td>{mean:.4f}</td>")
                cls = "positive" if delta >= 0 else "negative"
                parts.append(f'<td class="{cls}">{sign}{delta:.4f}</td>')
                if first:
                    first = False
                parts.append("</tr>")
        parts.append("</tbody></table>")

    parts.append('<p class="footer">Generated by Retort</p>')
    parts.append("</body></html>")

    return "\n".join(parts)


_HTML_STYLE = """\
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1rem;
  color: #1a1a1a;
}
h1 { border-bottom: 2px solid #2563eb; padding-bottom: 0.5rem; }
h2 { color: #2563eb; margin-top: 2rem; }
.meta { background: #f1f5f9; padding: 1rem; border-radius: 6px; }
.meta p { margin: 0.25rem 0; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 1rem 0;
}
th, td {
  border: 1px solid #cbd5e1;
  padding: 0.5rem 0.75rem;
  text-align: left;
}
th { background: #2563eb; color: white; }
tr:nth-child(even) { background: #f8fafc; }
.positive { color: #16a34a; }
.negative { color: #dc2626; }
.footer {
  margin-top: 2rem;
  color: #94a3b8;
  font-size: 0.85rem;
  text-align: center;
}"""
