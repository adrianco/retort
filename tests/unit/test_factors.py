"""Tests for the factor registry."""

import pytest

from retort.design.factors import Factor, FactorRegistry, FactorType


class TestFactor:
    def test_create_categorical(self):
        f = Factor(name="lang", levels=("python", "go"))
        assert f.name == "lang"
        assert f.levels == ("python", "go")
        assert f.factor_type == FactorType.CATEGORICAL
        assert f.num_levels == 2

    def test_create_ordinal(self):
        f = Factor(name="size", levels=("small", "medium", "large"), factor_type=FactorType.ORDINAL)
        assert f.factor_type == FactorType.ORDINAL
        assert f.num_levels == 3

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            Factor(name="", levels=("a", "b"))

    def test_single_level_rejected(self):
        with pytest.raises(ValueError, match="at least 2 levels"):
            Factor(name="x", levels=("only_one",))

    def test_zero_levels_rejected(self):
        with pytest.raises(ValueError, match="at least 2 levels"):
            Factor(name="x", levels=())

    def test_duplicate_levels_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            Factor(name="x", levels=("a", "b", "a"))

    def test_level_index(self):
        f = Factor(name="lang", levels=("python", "go", "rust"))
        assert f.level_index("python") == 0
        assert f.level_index("go") == 1
        assert f.level_index("rust") == 2

    def test_level_index_invalid(self):
        f = Factor(name="lang", levels=("python", "go"))
        with pytest.raises(ValueError, match="not found"):
            f.level_index("rust")

    def test_immutable(self):
        f = Factor(name="lang", levels=("python", "go"))
        with pytest.raises(AttributeError):
            f.name = "other"


class TestFactorRegistry:
    def test_add_and_get(self):
        reg = FactorRegistry()
        f = reg.add("lang", ["python", "go"])
        assert reg.get("lang") is f
        assert len(reg) == 1

    def test_duplicate_name_rejected(self):
        reg = FactorRegistry()
        reg.add("lang", ["python", "go"])
        with pytest.raises(ValueError, match="already registered"):
            reg.add("lang", ["rust", "typescript"])

    def test_get_missing(self):
        reg = FactorRegistry()
        with pytest.raises(KeyError, match="not found"):
            reg.get("nope")

    def test_remove(self):
        reg = FactorRegistry()
        reg.add("lang", ["python", "go"])
        reg.remove("lang")
        assert len(reg) == 0
        assert "lang" not in reg

    def test_remove_missing(self):
        reg = FactorRegistry()
        with pytest.raises(KeyError):
            reg.remove("nope")

    def test_contains(self):
        reg = FactorRegistry()
        reg.add("lang", ["python", "go"])
        assert "lang" in reg
        assert "agent" not in reg

    def test_names(self):
        reg = FactorRegistry()
        reg.add("lang", ["python", "go"])
        reg.add("agent", ["claude", "copilot"])
        assert reg.names == ["lang", "agent"]

    def test_factors_list(self):
        reg = FactorRegistry()
        f1 = reg.add("lang", ["python", "go"])
        f2 = reg.add("agent", ["claude", "copilot"])
        assert reg.factors == [f1, f2]

    def test_level_counts(self):
        reg = FactorRegistry()
        reg.add("lang", ["python", "go", "rust"])
        reg.add("agent", ["claude", "copilot"])
        assert reg.level_counts() == [3, 2]

    def test_from_dict(self):
        spec = {
            "lang": ["python", "go"],
            "agent": ["claude", "copilot", "aider"],
        }
        reg = FactorRegistry.from_dict(spec)
        assert len(reg) == 2
        assert reg.get("lang").num_levels == 2
        assert reg.get("agent").num_levels == 3

    def test_add_ordinal(self):
        reg = FactorRegistry()
        f = reg.add("size", ["small", "large"], factor_type=FactorType.ORDINAL)
        assert f.factor_type == FactorType.ORDINAL
