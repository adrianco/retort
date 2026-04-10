"""Tests for design matrix generation."""

import pytest

from retort.design.factors import FactorRegistry
from retort.design.generator import DesignMatrix, DesignPhase, generate_design, generate_screening_design


class TestGenerateScreeningDesign:
    def test_two_level_factors(self, two_level_registry):
        result = generate_screening_design(two_level_registry)
        assert isinstance(result, DesignMatrix)
        assert result.phase == DesignPhase.SCREENING
        assert list(result.matrix.columns) == ["language", "agent", "framework"]
        # All values must be valid levels
        for col in result.matrix.columns:
            factor = two_level_registry.get(col)
            assert set(result.matrix[col]).issubset(set(factor.levels))

    def test_all_levels_appear(self, two_level_registry):
        """Every level of every factor should appear at least once."""
        result = generate_screening_design(two_level_registry)
        for factor in two_level_registry.factors:
            appearing = set(result.matrix[factor.name])
            assert appearing == set(factor.levels), (
                f"Factor '{factor.name}': expected {set(factor.levels)}, got {appearing}"
            )

    def test_mixed_levels(self, mixed_level_registry):
        result = generate_screening_design(mixed_level_registry)
        assert result.num_runs > 0
        # All levels should appear
        for factor in mixed_level_registry.factors:
            appearing = set(result.matrix[factor.name])
            assert appearing == set(factor.levels)

    def test_large_design(self, large_registry):
        """6-factor design should work and cover all levels."""
        result = generate_screening_design(large_registry)
        assert result.num_runs > 0
        for factor in large_registry.factors:
            appearing = set(result.matrix[factor.name])
            assert appearing == set(factor.levels)

    def test_no_exact_duplicate_rows(self, mixed_level_registry):
        result = generate_screening_design(mixed_level_registry)
        dupes = result.matrix.duplicated()
        assert not dupes.any(), f"Found duplicate rows: {result.matrix[dupes]}"

    def test_fewer_than_two_factors_rejected(self):
        reg = FactorRegistry()
        reg.add("only", ["a", "b"])
        with pytest.raises(ValueError, match="at least 2 factors"):
            generate_screening_design(reg)

    def test_screening_run_count_reasonable(self, two_level_registry):
        """Screening design should have far fewer runs than full factorial."""
        result = generate_screening_design(two_level_registry)
        full_factorial_size = 2 * 2 * 2  # 8
        # Screening should be <= full factorial (for 2-level, it may equal it for 3 factors)
        assert result.num_runs <= full_factorial_size

    def test_run_configs(self, two_level_registry):
        result = generate_screening_design(two_level_registry)
        configs = result.run_configs()
        assert len(configs) == result.num_runs
        assert all(isinstance(c, dict) for c in configs)
        assert all("language" in c for c in configs)


class TestGenerateDesign:
    def test_screening_phase_string(self, two_level_registry):
        result = generate_design(two_level_registry, "screening")
        assert result.phase == DesignPhase.SCREENING

    def test_screening_phase_enum(self, two_level_registry):
        result = generate_design(two_level_registry, DesignPhase.SCREENING)
        assert result.phase == DesignPhase.SCREENING

    def test_characterization_phase(self, two_level_registry):
        result = generate_design(two_level_registry, "characterization")
        assert result.phase == DesignPhase.CHARACTERIZATION
        assert result.num_runs > 0

    def test_characterization_has_more_runs(self, large_registry):
        """Resolution IV should generally need more runs than Resolution III."""
        screening = generate_design(large_registry, "screening")
        characterization = generate_design(large_registry, "characterization")
        # Characterization should have at least as many runs
        assert characterization.num_runs >= screening.num_runs

    def test_invalid_phase(self, two_level_registry):
        with pytest.raises(ValueError):
            generate_design(two_level_registry, "optimization")


class TestDesignMatrix:
    def test_to_csv(self, two_level_registry, tmp_path):
        result = generate_screening_design(two_level_registry)
        path = str(tmp_path / "design.csv")
        result.to_csv(path)
        import pandas as pd
        loaded = pd.read_csv(path, index_col="run")
        assert list(loaded.columns) == ["language", "agent", "framework"]
        assert len(loaded) == result.num_runs
