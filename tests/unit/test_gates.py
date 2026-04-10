"""Tests for promotion gate evaluation."""

from __future__ import annotations

import pytest

from retort.config.schema import PromotionConfig, PromotionGate
from retort.promotion.gates import GateResult, evaluate_gate


@pytest.fixture
def default_config() -> PromotionConfig:
    """Default promotion config (p_value=0.10, posterior=0.80, dominated=0.95)."""
    return PromotionConfig()


@pytest.fixture
def custom_config() -> PromotionConfig:
    return PromotionConfig(
        screening_to_trial=PromotionGate(p_value=0.05),
        trial_to_production=PromotionGate(posterior_confidence=0.90),
        production_to_retired=PromotionGate(dominated_confidence=0.99),
    )


class TestScreeningToTrial:
    def test_pass_below_threshold(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "screening_to_trial", {"p_value": 0.05}, default_config
        )
        assert result.passed is True
        assert "✓" in result.detail

    def test_pass_at_threshold(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "screening_to_trial", {"p_value": 0.10}, default_config
        )
        assert result.passed is True

    def test_fail_above_threshold(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "screening_to_trial", {"p_value": 0.15}, default_config
        )
        assert result.passed is False
        assert "0.1500 > threshold" in result.detail

    def test_fail_missing_evidence(self, default_config: PromotionConfig):
        result = evaluate_gate("screening_to_trial", {}, default_config)
        assert result.passed is False
        assert "missing" in result.detail

    def test_custom_threshold(self, custom_config: PromotionConfig):
        # 0.05 threshold — 0.04 passes, 0.06 fails
        r1 = evaluate_gate(
            "screening_to_trial", {"p_value": 0.04}, custom_config
        )
        assert r1.passed is True

        r2 = evaluate_gate(
            "screening_to_trial", {"p_value": 0.06}, custom_config
        )
        assert r2.passed is False


class TestTrialToProduction:
    def test_pass(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "trial_to_production",
            {"posterior_confidence": 0.85},
            default_config,
        )
        assert result.passed is True

    def test_fail(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "trial_to_production",
            {"posterior_confidence": 0.70},
            default_config,
        )
        assert result.passed is False

    def test_at_threshold(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "trial_to_production",
            {"posterior_confidence": 0.80},
            default_config,
        )
        assert result.passed is True

    def test_missing(self, default_config: PromotionConfig):
        result = evaluate_gate("trial_to_production", {}, default_config)
        assert result.passed is False


class TestProductionToRetired:
    def test_pass(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "production_to_retired",
            {"dominated_confidence": 0.98},
            default_config,
        )
        assert result.passed is True

    def test_fail(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "production_to_retired",
            {"dominated_confidence": 0.90},
            default_config,
        )
        assert result.passed is False

    def test_custom_threshold(self, custom_config: PromotionConfig):
        r1 = evaluate_gate(
            "production_to_retired",
            {"dominated_confidence": 0.99},
            custom_config,
        )
        assert r1.passed is True

        r2 = evaluate_gate(
            "production_to_retired",
            {"dominated_confidence": 0.98},
            custom_config,
        )
        assert r2.passed is False


class TestEdgeCases:
    def test_unknown_gate(self, default_config: PromotionConfig):
        result = evaluate_gate("bogus_gate", {}, default_config)
        assert result.passed is False
        assert "unknown gate" in result.detail

    def test_gate_result_is_frozen(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "screening_to_trial", {"p_value": 0.05}, default_config
        )
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]

    def test_vacuous_pass_no_thresholds(self):
        config = PromotionConfig(
            screening_to_trial=PromotionGate(),
        )
        result = evaluate_gate("screening_to_trial", {}, config)
        assert result.passed is True
        assert "vacuously" in result.detail

    def test_gate_name_on_result(self, default_config: PromotionConfig):
        result = evaluate_gate(
            "screening_to_trial", {"p_value": 0.05}, default_config
        )
        assert result.gate_name == "screening_to_trial"
