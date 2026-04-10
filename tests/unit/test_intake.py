"""Tests for candidate intake module."""

import pytest

from retort.design.factors import FactorRegistry
from retort.design.generator import generate_screening_design
from retort.promotion.lifecycle import LifecycleState, StackLifecycle
from retort.scheduler.intake import IntakeResult, intake_candidate


@pytest.fixture
def base_registry() -> FactorRegistry:
    """Registry with 3 factors, each having 3 levels."""
    reg = FactorRegistry()
    reg.add("language", ["python", "go", "rust"])
    reg.add("agent", ["claude-code", "copilot", "cursor"])
    reg.add("framework", ["fastapi", "stdlib", "axum"])
    return reg


class TestIntakeCandidate:
    def test_basic_intake(self, base_registry):
        design = generate_screening_design(base_registry)
        result = intake_candidate(
            factor_name="agent",
            new_level="aider",
            registry=base_registry,
            existing_design=design,
            nrestarts=10,
        )

        assert isinstance(result, IntakeResult)
        assert result.factor_name == "agent"
        assert result.new_level == "aider"
        assert result.stack_id == "agent:aider"
        assert result.num_new_runs > 0

    def test_lifecycle_state_without_lifecycle(self, base_registry):
        design = generate_screening_design(base_registry)
        result = intake_candidate(
            factor_name="agent",
            new_level="aider",
            registry=base_registry,
            existing_design=design,
            nrestarts=10,
        )

        assert result.lifecycle_state == "candidate"

    def test_lifecycle_auto_promote_to_screening(self, base_registry):
        design = generate_screening_design(base_registry)
        lifecycle = StackLifecycle()

        result = intake_candidate(
            factor_name="agent",
            new_level="aider",
            registry=base_registry,
            existing_design=design,
            lifecycle=lifecycle,
            nrestarts=10,
        )

        assert result.lifecycle_state == "screening"
        assert lifecycle.state("agent:aider") == LifecycleState.screening

    def test_lifecycle_changelog_records_transitions(self, base_registry):
        design = generate_screening_design(base_registry)
        lifecycle = StackLifecycle()

        intake_candidate(
            factor_name="agent",
            new_level="aider",
            registry=base_registry,
            existing_design=design,
            lifecycle=lifecycle,
            nrestarts=10,
        )

        # Should have 2 entries: register (→candidate) + promote (→screening)
        assert len(lifecycle.changelog) == 2

    def test_new_rows_are_dataframe(self, base_registry):
        design = generate_screening_design(base_registry)
        result = intake_candidate(
            factor_name="agent",
            new_level="aider",
            registry=base_registry,
            existing_design=design,
            nrestarts=10,
        )

        import pandas as pd
        assert isinstance(result.new_rows, pd.DataFrame)
        assert list(result.new_rows.columns) == list(design.matrix.columns)

    def test_invalid_factor_raises(self, base_registry):
        design = generate_screening_design(base_registry)
        with pytest.raises(ValueError, match="not found"):
            intake_candidate(
                factor_name="nonexistent",
                new_level="value",
                registry=base_registry,
                existing_design=design,
            )

    def test_existing_level_raises(self, base_registry):
        design = generate_screening_design(base_registry)
        with pytest.raises(ValueError, match="already exists"):
            intake_candidate(
                factor_name="agent",
                new_level="copilot",
                registry=base_registry,
                existing_design=design,
            )

    def test_multiple_intakes(self, base_registry):
        """Multiple candidates can be ingested sequentially."""
        design = generate_screening_design(base_registry)
        lifecycle = StackLifecycle()

        result1 = intake_candidate(
            factor_name="agent",
            new_level="aider",
            registry=base_registry,
            existing_design=design,
            lifecycle=lifecycle,
            nrestarts=10,
        )

        # Second intake for a different factor
        result2 = intake_candidate(
            factor_name="language",
            new_level="typescript",
            registry=base_registry,
            existing_design=design,
            lifecycle=lifecycle,
            nrestarts=10,
        )

        assert result1.stack_id != result2.stack_id
        assert lifecycle.state("agent:aider") == LifecycleState.screening
        assert lifecycle.state("language:typescript") == LifecycleState.screening
