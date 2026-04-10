"""Tests for the aliasing report rendering."""

from __future__ import annotations

import json

import pytest

from retort.design.aliasing import AliasGroup, AliasingReport
from retort.reporting.aliasing_report import _roman, render_json, render_text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def full_factorial_report() -> AliasingReport:
    """Aliasing report for a full factorial (no confounding)."""
    return AliasingReport(
        factor_names=["language", "agent"],
        factor_labels={"A": "language", "B": "agent"},
        resolution=99,
        n_runs=4,
        n_factors=2,
        alias_groups=[
            AliasGroup(effects=("language",)),
            AliasGroup(effects=("agent",)),
            AliasGroup(effects=("language:agent",)),
        ],
        generators=[],
        defining_relation=[],
    )


@pytest.fixture
def confounded_report() -> AliasingReport:
    """Aliasing report with confounded effects."""
    return AliasingReport(
        factor_names=["A", "B", "C", "D"],
        factor_labels={"A": "A", "B": "B", "C": "C", "D": "D"},
        resolution=3,
        n_runs=8,
        n_factors=4,
        alias_groups=[
            AliasGroup(effects=("A",)),
            AliasGroup(effects=("B", "C:D")),
            AliasGroup(effects=("C", "B:D")),
            AliasGroup(effects=("D", "B:C")),
        ],
        generators=["AB"],
        defining_relation=["ABD"],
    )


# ---------------------------------------------------------------------------
# Text rendering tests
# ---------------------------------------------------------------------------


class TestRenderText:
    def test_header(self, full_factorial_report: AliasingReport):
        text = render_text(full_factorial_report)
        assert "Aliasing / Confounding Report" in text

    def test_full_factorial_shows_full(self, full_factorial_report: AliasingReport):
        text = render_text(full_factorial_report)
        assert "Full" in text

    def test_shows_resolution(self, confounded_report: AliasingReport):
        text = render_text(confounded_report)
        assert "III" in text

    def test_shows_factor_labels(self, confounded_report: AliasingReport):
        text = render_text(confounded_report)
        assert "A = A" in text
        assert "B = B" in text

    def test_shows_generators(self, confounded_report: AliasingReport):
        text = render_text(confounded_report)
        assert "Generators" in text
        assert "AB" in text

    def test_no_generators_for_full(self, full_factorial_report: AliasingReport):
        text = render_text(full_factorial_report)
        assert "Generators" not in text

    def test_shows_defining_relation(self, confounded_report: AliasingReport):
        text = render_text(confounded_report)
        assert "Defining Relation" in text
        assert "ABD" in text

    def test_shows_clear_effects(self, confounded_report: AliasingReport):
        text = render_text(confounded_report)
        assert "[clear]" in text

    def test_shows_confounded_effects(self, confounded_report: AliasingReport):
        text = render_text(confounded_report)
        assert "[confounded]" in text

    def test_summary_section(self, confounded_report: AliasingReport):
        text = render_text(confounded_report)
        assert "Summary" in text
        assert "Clear effects:" in text
        assert "Confounded groups:" in text


# ---------------------------------------------------------------------------
# JSON rendering tests
# ---------------------------------------------------------------------------


class TestRenderJson:
    def test_valid_json(self, confounded_report: AliasingReport):
        output = render_json(confounded_report)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_contains_fields(self, confounded_report: AliasingReport):
        data = json.loads(render_json(confounded_report))
        assert "n_factors" in data
        assert "n_runs" in data
        assert "resolution" in data
        assert "factor_labels" in data
        assert "generators" in data
        assert "defining_relation" in data
        assert "alias_groups" in data
        assert "confounded_pairs" in data

    def test_alias_groups_structure(self, confounded_report: AliasingReport):
        data = json.loads(render_json(confounded_report))
        groups = data["alias_groups"]
        assert len(groups) == 4
        for g in groups:
            assert "effects" in g
            assert "is_clear" in g
            assert "order" in g

    def test_confounded_pairs(self, confounded_report: AliasingReport):
        data = json.loads(render_json(confounded_report))
        pairs = data["confounded_pairs"]
        assert len(pairs) > 0
        assert "effect_a" in pairs[0]
        assert "effect_b" in pairs[0]


# ---------------------------------------------------------------------------
# Roman numeral helper
# ---------------------------------------------------------------------------


class TestRoman:
    def test_common_values(self):
        assert _roman(3) == "III"
        assert _roman(4) == "IV"
        assert _roman(5) == "V"

    def test_fallback_for_large(self):
        assert _roman(99) == "99"
