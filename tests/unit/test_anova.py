"""Tests for ANOVA analysis and residual diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from retort.analysis.anova import (
    AnovaResult,
    build_formula,
    run_all_responses,
    run_anova,
)
from retort.analysis.residuals import ResidualDiagnostics, check_residuals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_experiment_data(
    n_per_group: int = 10,
    seed: int = 42,
    effect_size: float = 5.0,
) -> pd.DataFrame:
    """Create synthetic experiment data with a known factor effect.

    Factor A (language) has a strong effect on score.
    Factor B (agent) has no effect.
    """
    rng = np.random.default_rng(seed)
    languages = ["python", "go", "rust"]
    agents = ["claude-code", "copilot"]

    rows: list[dict[str, object]] = []
    for lang in languages:
        for agent in agents:
            for _ in range(n_per_group):
                # Language has a real effect, agent does not
                base = languages.index(lang) * effect_size
                noise = rng.normal(0, 1)
                rows.append(
                    {
                        "language": lang,
                        "agent": agent,
                        "score": base + noise,
                    }
                )
    return pd.DataFrame(rows)


def _make_no_effect_data(n_per_group: int = 10, seed: int = 99) -> pd.DataFrame:
    """Data where no factor has any effect."""
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for lang in ["python", "go"]:
        for agent in ["claude-code", "copilot"]:
            for _ in range(n_per_group):
                rows.append(
                    {
                        "language": lang,
                        "agent": agent,
                        "score": rng.normal(10, 1),
                    }
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# build_formula tests
# ---------------------------------------------------------------------------


class TestBuildFormula:
    def test_main_effects_only(self):
        f = build_formula("score", ["language", "agent"])
        assert f == "score ~ C(language) + C(agent)"

    def test_with_interactions(self):
        f = build_formula("score", ["language", "agent"], include_interactions=True)
        assert "C(language):C(agent)" in f
        assert "C(language) + C(agent)" in f

    def test_single_factor(self):
        f = build_formula("y", ["x"])
        assert f == "y ~ C(x)"

    def test_three_factors_interactions(self):
        f = build_formula("y", ["a", "b", "c"], include_interactions=True)
        assert "C(a):C(b)" in f
        assert "C(a):C(c)" in f
        assert "C(b):C(c)" in f


# ---------------------------------------------------------------------------
# run_anova tests
# ---------------------------------------------------------------------------


class TestRunAnova:
    def test_detects_significant_factor(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score", significance=0.05)

        assert isinstance(result, AnovaResult)
        assert result.response == "score"
        assert "language" in result.significant_factors
        assert "agent" not in result.significant_factors

    def test_r_squared_reasonable(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")

        assert result.r_squared > 0.5
        assert result.adj_r_squared > 0.4

    def test_no_significant_factors(self):
        data = _make_no_effect_data()
        result = run_anova(data, response="score", significance=0.05)

        assert result.significant_factors == []

    def test_missing_response_raises(self):
        data = _make_experiment_data()
        with pytest.raises(ValueError, match="not found"):
            run_anova(data, response="nonexistent")

    def test_no_factors_raises(self):
        data = pd.DataFrame({"score": [1, 2, 3]})
        with pytest.raises(ValueError, match="No factor"):
            run_anova(data, response="score", factors=[])

    def test_explicit_factors(self):
        data = _make_experiment_data()
        result = run_anova(
            data, response="score", factors=["language"], significance=0.05
        )
        assert "language" in result.significant_factors

    def test_with_interactions(self):
        data = _make_experiment_data()
        result = run_anova(
            data, response="score", include_interactions=True, significance=0.05
        )
        assert isinstance(result.anova_table, pd.DataFrame)
        # Interaction term should appear in the table
        has_interaction = any(":" in str(idx) for idx in result.anova_table.index)
        assert has_interaction

    def test_factors_inferred_when_none(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")
        # Both language and agent should appear in the ANOVA table
        table_terms = [str(idx) for idx in result.anova_table.index]
        assert any("language" in t for t in table_terms)
        assert any("agent" in t for t in table_terms)

    def test_hyphenated_factor_names(self):
        """Factor names with hyphens (e.g. 'claude-code') should work."""
        data = pd.DataFrame(
            {
                "app-type": ["rest-api"] * 5 + ["cli-tool"] * 5,
                "score": list(range(10)),
            }
        )
        result = run_anova(data, response="score")
        assert isinstance(result, AnovaResult)


# ---------------------------------------------------------------------------
# run_all_responses tests
# ---------------------------------------------------------------------------


class TestRunAllResponses:
    def test_multiple_responses(self):
        data = _make_experiment_data()
        # Add a second response
        data["latency"] = np.random.default_rng(7).normal(100, 10, len(data))

        results = run_all_responses(
            data, responses=["score", "latency"], significance=0.10
        )

        assert "score" in results
        assert "latency" in results
        assert isinstance(results["score"], AnovaResult)
        assert isinstance(results["latency"], AnovaResult)

    def test_factors_shared(self):
        data = _make_experiment_data()
        data["latency"] = np.random.default_rng(7).normal(100, 10, len(data))

        results = run_all_responses(
            data,
            responses=["score", "latency"],
            factors=["language"],
        )
        for result in results.values():
            table_terms = [str(idx) for idx in result.anova_table.index]
            # Only language should be in the model
            assert any("language" in t for t in table_terms)
            assert not any("agent" in t for t in table_terms)


# ---------------------------------------------------------------------------
# Residual diagnostics tests
# ---------------------------------------------------------------------------


class TestResidualDiagnostics:
    def test_basic_diagnostics(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")
        diag = check_residuals(result.model, "score")

        assert isinstance(diag, ResidualDiagnostics)
        assert diag.response == "score"
        assert diag.n_obs == len(data)
        assert len(diag.residuals) == len(data)
        assert len(diag.standardized_residuals) == len(data)

    def test_normality_check(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")
        diag = check_residuals(result.model, "score")

        # With normal noise, Shapiro-Wilk should pass
        assert diag.normality_ok is True
        assert 0 < diag.shapiro_stat <= 1
        assert 0 < diag.shapiro_p <= 1

    def test_durbin_watson_range(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")
        diag = check_residuals(result.model, "score")

        # DW should be roughly 2 for independent errors
        assert 0 < diag.durbin_watson < 4
        assert diag.independence_ok is True

    def test_levene_with_groups(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")
        diag = check_residuals(
            result.model, "score", group_column="language", data=data
        )

        assert diag.levene_stat is not None
        assert diag.levene_p is not None
        assert diag.homoscedasticity_ok is not None

    def test_levene_without_groups(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")
        diag = check_residuals(result.model, "score")

        assert diag.levene_stat is None
        assert diag.levene_p is None
        assert diag.homoscedasticity_ok is None

    def test_all_ok_property(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")
        diag = check_residuals(result.model, "score")

        # With well-behaved normal data, all checks should pass
        assert diag.all_ok is True

    def test_summary_string(self):
        data = _make_experiment_data()
        result = run_anova(data, response="score")
        diag = check_residuals(result.model, "score")
        summary = diag.summary()

        assert "score" in summary
        assert "Shapiro-Wilk" in summary
        assert "Durbin-Watson" in summary
        assert "PASS" in summary or "FAIL" in summary

    def test_outlier_detection(self):
        """Injecting an extreme value should flag it as an outlier."""
        data = _make_experiment_data()
        # Inject an extreme outlier
        data.loc[0, "score"] = 1000.0
        result = run_anova(data, response="score")
        diag = check_residuals(result.model, "score")

        assert len(diag.outlier_indices) >= 1
