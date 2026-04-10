"""Render aliasing reports in text, JSON, and HTML formats."""

from __future__ import annotations

import json

from retort.design.aliasing import AliasingReport


def render_text(report: AliasingReport) -> str:
    """Render aliasing report as human-readable text."""
    lines: list[str] = []
    lines.append("Aliasing / Confounding Report")
    lines.append("=" * 60)
    lines.append(f"Factors:    {report.n_factors}")
    lines.append(f"Runs:       {report.n_runs}")
    lines.append(f"Resolution: {'Full' if not report.defining_relation else _roman(report.resolution)}")
    lines.append("")

    # Factor labels
    lines.append("Factor Labels")
    lines.append("-" * 40)
    for label, name in sorted(report.factor_labels.items()):
        lines.append(f"  {label} = {name}")
    lines.append("")

    # Generators
    if report.generators:
        lines.append("Generators")
        lines.append("-" * 40)
        n_base = report.n_factors - len(report.generators)
        base_labels = [chr(ord("A") + i) for i in range(n_base)]
        for i, gen in enumerate(report.generators):
            gen_label = chr(ord("A") + n_base + i)
            lines.append(f"  {gen_label} = {gen}")
        lines.append("")

    # Defining relation
    if report.defining_relation:
        lines.append("Defining Relation")
        lines.append("-" * 40)
        lines.append(f"  I = {' = '.join(report.defining_relation)}")
        lines.append("")

    # Alias groups
    lines.append("Alias Structure")
    lines.append("-" * 40)
    for group in report.alias_groups:
        if group.is_clear:
            lines.append(f"  {group.effects[0]}  [clear]")
        else:
            lines.append(f"  {' = '.join(group.effects)}  [confounded]")
    lines.append("")

    # Summary
    n_clear = sum(1 for g in report.alias_groups if g.is_clear)
    n_confounded = sum(1 for g in report.alias_groups if not g.is_clear)
    lines.append("Summary")
    lines.append("-" * 40)
    lines.append(f"  Clear effects:      {n_clear}")
    lines.append(f"  Confounded groups:  {n_confounded}")
    if report.confounded_pairs:
        lines.append(f"  Confounded pairs:   {len(report.confounded_pairs)}")
    lines.append("")

    return "\n".join(lines)


def render_json(report: AliasingReport) -> str:
    """Serialize aliasing report to JSON."""
    data = {
        "n_factors": report.n_factors,
        "n_runs": report.n_runs,
        "resolution": report.resolution,
        "factor_labels": report.factor_labels,
        "generators": report.generators,
        "defining_relation": report.defining_relation,
        "alias_groups": [
            {
                "effects": list(group.effects),
                "is_clear": group.is_clear,
                "order": group.order,
            }
            for group in report.alias_groups
        ],
        "confounded_pairs": [
            {"effect_a": a, "effect_b": b}
            for a, b in report.confounded_pairs
        ],
    }
    return json.dumps(data, indent=2)


def _roman(n: int) -> str:
    """Convert small integer to Roman numeral for resolution display."""
    romans = {
        1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
        6: "VI", 7: "VII", 8: "VIII",
    }
    return romans.get(n, str(n))
