"""Tests for design matrix generation."""

import pytest

from retort.design.factors import FactorRegistry
from retort.design.generator import (
    DesignMatrix,
    DesignPhase,
    generate_design,
    generate_fractional_design,
    generate_screening_design,
)


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

    def test_from_csv_roundtrip(self, two_level_registry, tmp_path):
        """from_csv(to_csv(...)) produces identical matrix content."""
        result = generate_screening_design(two_level_registry)
        path = str(tmp_path / "design.csv")
        result.to_csv(path)
        loaded = DesignMatrix.from_csv(path, phase="screening")
        assert list(loaded.matrix.columns) == list(result.matrix.columns)
        assert len(loaded.matrix) == result.num_runs
        assert loaded.phase == DesignPhase.SCREENING

    def test_from_csv_values_match(self, mixed_level_registry, tmp_path):
        result = generate_screening_design(mixed_level_registry)
        path = tmp_path / "design.csv"
        result.to_csv(str(path))
        loaded = DesignMatrix.from_csv(path)
        # Cell values must be identical
        for col in result.matrix.columns:
            assert list(loaded.matrix[col]) == list(result.matrix[col])

    def test_from_csv_phase_default(self, two_level_registry, tmp_path):
        result = generate_screening_design(two_level_registry)
        path = tmp_path / "d.csv"
        result.to_csv(str(path))
        loaded = DesignMatrix.from_csv(path)
        assert loaded.phase == DesignPhase.SCREENING

    def test_from_csv_characterization_phase(self, two_level_registry, tmp_path):
        result = generate_design(two_level_registry, "characterization")
        path = tmp_path / "d.csv"
        result.to_csv(str(path))
        loaded = DesignMatrix.from_csv(path, phase="characterization")
        assert loaded.phase == DesignPhase.CHARACTERIZATION

    def test_from_csv_subset(self, mixed_level_registry, tmp_path):
        """from_csv should load a manually-trimmed (subset) CSV correctly."""
        import pandas as pd
        result = generate_screening_design(mixed_level_registry)
        # Write a 3-row subset
        subset = result.matrix.head(3)
        path = tmp_path / "subset.csv"
        subset.to_csv(path, index_label="run")
        loaded = DesignMatrix.from_csv(path)
        assert loaded.num_runs == 3


class TestGenerateFractionalDesign:
    def _six_by_two_by_two_registry(self) -> FactorRegistry:
        reg = FactorRegistry()
        reg.add("language", ["python", "typescript", "go", "rust", "java", "clojure"])
        reg.add("model", ["opus-4-6", "opus-4-7"])
        reg.add("tooling", ["none", "beads"])
        return reg

    def test_quarter_fraction_run_count(self):
        """Quarter fraction of 24-cell design → 6 runs."""
        reg = self._six_by_two_by_two_registry()
        result = generate_fractional_design(reg, fraction=0.25)
        assert result.num_runs == 6

    def test_all_levels_covered(self):
        """Every factor level must appear at least once."""
        reg = self._six_by_two_by_two_registry()
        result = generate_fractional_design(reg, fraction=0.25)
        for factor in reg.factors:
            assert set(result.matrix[factor.name]) == set(factor.levels), (
                f"Factor '{factor.name}' levels not fully covered"
            )

    def test_binary_factors_balanced(self):
        """Both binary factors must be balanced (3 runs per level)."""
        reg = self._six_by_two_by_two_registry()
        result = generate_fractional_design(reg, fraction=0.25)
        for fname in ["model", "tooling"]:
            counts = result.matrix[fname].value_counts()
            assert counts.min() == counts.max(), (
                f"Factor '{fname}' not balanced: {counts.to_dict()}"
            )

    def test_fraction_metadata_set(self):
        reg = self._six_by_two_by_two_registry()
        result = generate_fractional_design(reg, fraction=0.25)
        assert result.fraction == 0.25
        assert result.full_factorial_size == 24

    def test_fraction_one_returns_full_design(self):
        reg = self._six_by_two_by_two_registry()
        full = generate_design(reg, "screening")
        frac = generate_design(reg, "screening", fraction=1.0)
        assert frac.num_runs == full.num_runs

    def test_fraction_above_one_rejected(self):
        reg = self._six_by_two_by_two_registry()
        with pytest.raises(ValueError, match="fraction"):
            generate_fractional_design(reg, fraction=1.5)

    def test_fraction_zero_rejected(self):
        reg = self._six_by_two_by_two_registry()
        with pytest.raises(ValueError, match="fraction"):
            generate_fractional_design(reg, fraction=0.0)

    def test_no_duplicate_rows(self):
        reg = self._six_by_two_by_two_registry()
        result = generate_fractional_design(reg, fraction=0.25)
        assert not result.matrix.duplicated().any()

    def test_half_fraction(self):
        """Half fraction of 24-cell design → 12 runs, all levels covered."""
        reg = self._six_by_two_by_two_registry()
        result = generate_fractional_design(reg, fraction=0.5)
        assert result.num_runs == 12
        for factor in reg.factors:
            assert set(result.matrix[factor.name]) == set(factor.levels)

    def test_two_level_only_fraction(self):
        """Fraction on a pure 2-level design still covers all levels."""
        reg = FactorRegistry()
        reg.add("A", ["a0", "a1"])
        reg.add("B", ["b0", "b1"])
        reg.add("C", ["c0", "c1"])
        # 2^3 = 8, half fraction = 4
        result = generate_fractional_design(reg, fraction=0.5)
        assert result.num_runs <= 4
        for factor in reg.factors:
            assert set(result.matrix[factor.name]) == set(factor.levels)

    def test_generate_design_fraction_kwarg(self):
        """generate_design(fraction=...) delegates to generate_fractional_design."""
        reg = self._six_by_two_by_two_registry()
        result = generate_design(reg, "screening", fraction=0.25)
        assert result.num_runs == 6
        assert result.fraction == 0.25
