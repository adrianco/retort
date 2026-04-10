"""Export effects reports to JSON, CSV, and text formats."""

from __future__ import annotations

import csv
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
