"""Tests for the design aliasing inspector."""

from __future__ import annotations

import json

import pytest

from retort.design.aliasing import (
    AliasGroup,
    AliasingReport,
    _all_defining_words,
    _letters,
    _word_product,
    compute_aliasing,
)
from retort.design.factors import FactorRegistry
from retort.design.generator import DesignPhase


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestWordProduct:
    def test_disjoint(self):
        assert _word_product("AB", "CD") == "ABCD"

    def test_overlap_cancels(self):
        assert _word_product("AB", "BC") == "AC"

    def test_identical_gives_identity(self):
        assert _word_product("AB", "AB") == "I"

    def test_single_letters(self):
        assert _word_product("A", "B") == "AB"

    def test_result_sorted(self):
        assert _word_product("C", "A") == "AC"


class TestLetters:
    def test_basic(self):
        assert _letters(3) == ["A", "B", "C"]

    def test_six(self):
        assert _letters(6) == ["A", "B", "C", "D", "E", "F"]


class TestDefiningWords:
    def test_single_generator(self):
        # 2^(3-1) design: 3 factors A, B, C with C=AB
        # Generator word: ABC (C * AB = ABC because C*C=I → C*AB=ABC)
        labels = ["A", "B", "C"]
        generators = ["AB"]  # C = AB
        words = _all_defining_words(generators, labels)
        assert "ABC" in words

    def test_two_generators(self):
        # 4 factors, 2 generators
        labels = ["A", "B", "C", "D"]
        generators = ["AB", "AC"]  # C=AB, D=AC
        words = _all_defining_words(generators, labels)
        assert len(words) >= 2  # at least the two generator words + their product


# ---------------------------------------------------------------------------
# AliasGroup tests
# ---------------------------------------------------------------------------


class TestAliasGroup:
    def test_clear(self):
        g = AliasGroup(effects=("language",))
        assert g.is_clear
        assert g.order == 1

    def test_confounded(self):
        g = AliasGroup(effects=("language", "agent:framework"))
        assert not g.is_clear
        assert g.order == 1  # "language" is order 1

    def test_interaction_order(self):
        g = AliasGroup(effects=("language:agent",))
        assert g.order == 2


# ---------------------------------------------------------------------------
# Full aliasing computation tests
# ---------------------------------------------------------------------------


class TestComputeAliasing:
    def test_two_factors_full_factorial(self):
        """With only 2 factors, we get a full factorial — no aliasing."""
        reg = FactorRegistry()
        reg.add("language", ["python", "go"])
        reg.add("agent", ["claude", "copilot"])

        report = compute_aliasing(reg, "screening")

        assert report.n_factors == 2
        assert report.n_runs == 4  # 2^2 full factorial
        assert report.defining_relation == []
        assert all(g.is_clear for g in report.alias_groups)

    def test_three_factors_full_factorial(self):
        """3 factors at resolution III still gives full factorial (2^3=8)."""
        reg = FactorRegistry()
        reg.add("language", ["python", "go"])
        reg.add("agent", ["claude", "copilot"])
        reg.add("framework", ["fastapi", "stdlib"])

        report = compute_aliasing(reg, "screening")

        # 3 factors: _min_base_factors(3, 3) might give 3 → full factorial
        assert report.n_factors == 3
        assert report.n_runs >= 4

    def test_four_factors_screening(self):
        """4 factors at resolution III produces aliased effects."""
        reg = FactorRegistry()
        reg.add("language", ["python", "go"])
        reg.add("agent", ["claude", "copilot"])
        reg.add("framework", ["fastapi", "stdlib"])
        reg.add("app_type", ["rest-api", "cli"])

        report = compute_aliasing(reg, "screening")

        assert report.n_factors == 4
        assert len(report.factor_labels) == 4
        # Should have some alias groups
        assert len(report.alias_groups) > 0
        # All main effects should appear
        main_effects = set()
        for g in report.alias_groups:
            for e in g.effects:
                if ":" not in e:
                    main_effects.add(e)
        assert main_effects == {"language", "agent", "framework", "app_type"}

    def test_six_factors_screening_has_aliasing(self):
        """6 factors at resolution III must have non-trivial aliasing."""
        reg = FactorRegistry()
        reg.add("A", ["a1", "a2"])
        reg.add("B", ["b1", "b2"])
        reg.add("C", ["c1", "c2"])
        reg.add("D", ["d1", "d2"])
        reg.add("E", ["e1", "e2"])
        reg.add("F", ["f1", "f2"])

        report = compute_aliasing(reg, "screening")

        assert report.n_factors == 6
        assert report.generators  # must have generators
        assert report.defining_relation  # must have defining relation
        # Some effects must be confounded
        assert any(not g.is_clear for g in report.alias_groups)

    def test_characterization_higher_resolution(self):
        """Characterization (Res IV) should have fewer confounded main effects."""
        reg = FactorRegistry()
        reg.add("A", ["a1", "a2"])
        reg.add("B", ["b1", "b2"])
        reg.add("C", ["c1", "c2"])
        reg.add("D", ["d1", "d2"])
        reg.add("E", ["e1", "e2"])

        report_screening = compute_aliasing(reg, "screening")
        report_charac = compute_aliasing(reg, "characterization")

        # Characterization should have higher or equal resolution
        assert report_charac.resolution >= report_screening.resolution

    def test_max_order_1_only_main(self):
        """max_order=1 should only include main effects."""
        reg = FactorRegistry()
        reg.add("language", ["python", "go"])
        reg.add("agent", ["claude", "copilot"])
        reg.add("framework", ["fastapi", "stdlib"])

        report = compute_aliasing(reg, "screening", max_order=1)

        for g in report.alias_groups:
            for e in g.effects:
                assert ":" not in e, f"Interaction {e} found with max_order=1"

    def test_too_few_factors_raises(self):
        reg = FactorRegistry()
        reg.add("language", ["python", "go"])

        with pytest.raises(ValueError, match="at least 2"):
            compute_aliasing(reg, "screening")

    def test_invalid_phase_raises(self):
        reg = FactorRegistry()
        reg.add("language", ["python", "go"])
        reg.add("agent", ["claude", "copilot"])

        with pytest.raises(ValueError):
            compute_aliasing(reg, "invalid_phase")

    def test_confounded_pairs_property(self):
        """Verify confounded_pairs returns correct pairs."""
        report = AliasingReport(
            factor_names=["A", "B"],
            factor_labels={"A": "A", "B": "B"},
            resolution=3,
            n_runs=4,
            n_factors=2,
            alias_groups=[
                AliasGroup(effects=("A", "B:C")),
                AliasGroup(effects=("B",)),
            ],
        )
        pairs = report.confounded_pairs
        assert ("A", "B:C") in pairs
        assert len(pairs) == 1

    def test_clear_main_effects_property(self):
        report = AliasingReport(
            factor_names=["A", "B", "C"],
            factor_labels={"A": "A", "B": "B", "C": "C"},
            resolution=3,
            n_runs=4,
            n_factors=3,
            alias_groups=[
                AliasGroup(effects=("A",)),
                AliasGroup(effects=("B", "A:C")),
                AliasGroup(effects=("C",)),
            ],
        )
        clear = report.clear_main_effects
        assert "A" in clear
        assert "B" in clear  # aliased with interaction but still the only main effect
        assert "C" in clear
