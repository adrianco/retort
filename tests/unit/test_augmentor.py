"""Tests for D-optimal design augmentation."""

import pytest

from retort.design.augmentor import (
    AugmentationResult,
    _compute_n_runs,
    augment_design,
)
from retort.design.factors import FactorRegistry
from retort.design.generator import DesignPhase, generate_screening_design


@pytest.fixture
def base_registry() -> FactorRegistry:
    """Registry with 3 factors, each having 3 levels."""
    reg = FactorRegistry()
    reg.add("language", ["python", "go", "rust"])
    reg.add("agent", ["claude-code", "copilot", "cursor"])
    reg.add("framework", ["fastapi", "stdlib", "axum"])
    return reg


@pytest.fixture
def two_level_registry() -> FactorRegistry:
    """Registry with 3 factors, each having 2 levels."""
    reg = FactorRegistry()
    reg.add("language", ["python", "go"])
    reg.add("agent", ["claude-code", "copilot"])
    reg.add("framework", ["fastapi", "stdlib"])
    return reg


class TestComputeNRuns:
    def test_minimum_exceeds_saturated(self, base_registry):
        n = _compute_n_runs(base_registry)
        # Saturated = 1 + sum(levels-1) = 1 + 2+2+2 = 7
        assert n > 7

    def test_scales_with_levels(self):
        small = FactorRegistry()
        small.add("a", ["x", "y"])
        small.add("b", ["x", "y"])

        large = FactorRegistry()
        large.add("a", ["x", "y", "z", "w"])
        large.add("b", ["x", "y", "z", "w"])

        assert _compute_n_runs(large) >= _compute_n_runs(small)


class TestAugmentDesign:
    def test_basic_augmentation(self, base_registry):
        existing = generate_screening_design(base_registry)
        result = augment_design(
            existing=existing,
            registry=base_registry,
            factor_name="agent",
            new_level="aider",
            nrestarts=10,
        )

        assert isinstance(result, AugmentationResult)
        assert result.added_factor == "agent"
        assert result.added_level == "aider"
        assert result.num_new_runs > 0

    def test_new_level_appears_in_augmentation_rows(self, base_registry):
        existing = generate_screening_design(base_registry)
        result = augment_design(
            existing=existing,
            registry=base_registry,
            factor_name="agent",
            new_level="aider",
            nrestarts=10,
        )

        # The new level should appear in at least one augmentation row
        agent_values = set(result.new_rows["agent"].tolist())
        assert "aider" in agent_values

    def test_full_design_covers_all_levels(self, base_registry):
        existing = generate_screening_design(base_registry)
        result = augment_design(
            existing=existing,
            registry=base_registry,
            factor_name="language",
            new_level="typescript",
            nrestarts=10,
        )

        full = result.full_design.matrix
        # All original levels + new level should appear in full design
        lang_levels = set(full["language"].tolist())
        assert "typescript" in lang_levels

    def test_augmentation_preserves_columns(self, base_registry):
        existing = generate_screening_design(base_registry)
        result = augment_design(
            existing=existing,
            registry=base_registry,
            factor_name="agent",
            new_level="aider",
            nrestarts=10,
        )

        assert list(result.new_rows.columns) == list(existing.matrix.columns)

    def test_full_design_has_reasonable_runs(self, base_registry):
        existing = generate_screening_design(base_registry)
        result = augment_design(
            existing=existing,
            registry=base_registry,
            factor_name="agent",
            new_level="aider",
            nrestarts=10,
        )

        # D-optimal design should have enough runs to estimate main effects
        # (intercept + sum(levels-1) contrasts)
        min_runs = 1 + sum(
            (f.num_levels - 1) for f in base_registry.factors
        ) + 1  # +1 for the new level
        assert result.full_design.num_runs >= min_runs

    def test_d_efficiency_is_numeric(self, base_registry):
        existing = generate_screening_design(base_registry)
        result = augment_design(
            existing=existing,
            registry=base_registry,
            factor_name="agent",
            new_level="aider",
            nrestarts=10,
        )

        assert isinstance(result.d_efficiency, float)

    def test_invalid_factor_raises(self, base_registry):
        existing = generate_screening_design(base_registry)
        with pytest.raises(ValueError, match="not found"):
            augment_design(
                existing=existing,
                registry=base_registry,
                factor_name="nonexistent",
                new_level="value",
            )

    def test_existing_level_raises(self, base_registry):
        existing = generate_screening_design(base_registry)
        with pytest.raises(ValueError, match="already exists"):
            augment_design(
                existing=existing,
                registry=base_registry,
                factor_name="agent",
                new_level="copilot",  # already exists
            )

    def test_custom_n_runs(self, two_level_registry):
        existing = generate_screening_design(two_level_registry)
        result = augment_design(
            existing=existing,
            registry=two_level_registry,
            factor_name="language",
            new_level="rust",
            nrestarts=10,
            n_runs=16,
        )

        assert result.full_design.num_runs <= 16

    def test_no_duplicate_rows_in_full_design(self, base_registry):
        existing = generate_screening_design(base_registry)
        result = augment_design(
            existing=existing,
            registry=base_registry,
            factor_name="agent",
            new_level="aider",
            nrestarts=10,
        )

        dupes = result.full_design.matrix.duplicated()
        assert not dupes.any()
