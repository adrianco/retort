"""Tests for Bayesian updating with conjugate priors."""

from __future__ import annotations

import math

import numpy as np
import pytest

from retort.analysis.bayesian import EffectPosteriors, NormalInverseGamma


class TestNormalInverseGamma:
    def test_default_prior(self):
        nig = NormalInverseGamma()
        assert nig.mu_0 == 0.0
        assert nig.kappa == 1.0
        assert nig.alpha == 1.0
        assert nig.beta == 1.0

    def test_invalid_kappa(self):
        with pytest.raises(ValueError, match="kappa"):
            NormalInverseGamma(kappa=0)

    def test_invalid_alpha(self):
        with pytest.raises(ValueError, match="alpha"):
            NormalInverseGamma(alpha=-1)

    def test_invalid_beta(self):
        with pytest.raises(ValueError, match="beta"):
            NormalInverseGamma(beta=0)

    def test_update_empty_is_identity(self):
        prior = NormalInverseGamma(mu_0=1.0, kappa=2.0, alpha=3.0, beta=4.0)
        post = prior.update([])
        assert post.mu_0 == prior.mu_0
        assert post.kappa == prior.kappa
        assert post.alpha == prior.alpha
        assert post.beta == prior.beta

    def test_update_single_observation(self):
        prior = NormalInverseGamma()
        post = prior.update([5.0])
        # kappa_n = 1 + 1 = 2
        assert post.kappa == 2.0
        # mu_n = (1*0 + 1*5) / 2 = 2.5
        assert post.mu_0 == pytest.approx(2.5)
        # alpha_n = 1 + 0.5 = 1.5
        assert post.alpha == pytest.approx(1.5)

    def test_update_multiple_observations(self):
        prior = NormalInverseGamma()
        obs = [2.0, 4.0, 6.0]
        post = prior.update(obs)
        n = 3
        x_bar = 4.0
        assert post.kappa == pytest.approx(1.0 + n)
        assert post.mu_0 == pytest.approx((1.0 * 0.0 + n * x_bar) / (1.0 + n))
        assert post.alpha == pytest.approx(1.0 + n / 2.0)

    def test_posterior_mean_shifts_toward_data(self):
        prior = NormalInverseGamma(mu_0=0.0, kappa=1.0)
        post = prior.update([10.0, 10.0, 10.0, 10.0, 10.0])
        assert post.posterior_mean > 5.0  # Shifted well toward 10

    def test_posterior_variance_decreases_with_data(self):
        prior = NormalInverseGamma(mu_0=0.0, kappa=1.0, alpha=2.0, beta=1.0)
        post = prior.update(np.random.default_rng(42).normal(0, 1, size=50))
        assert post.posterior_variance < prior.posterior_variance

    def test_posterior_variance_infinite_when_alpha_leq_1(self):
        nig = NormalInverseGamma(mu_0=0.0, kappa=1.0, alpha=0.5, beta=1.0)
        assert math.isinf(nig.posterior_variance)

    def test_credible_interval_contains_mean(self):
        prior = NormalInverseGamma()
        post = prior.update([3.0, 3.5, 2.5, 3.0])
        lo, hi = post.credible_interval(0.95)
        assert lo < post.posterior_mean < hi

    def test_credible_interval_widens_with_level(self):
        prior = NormalInverseGamma()
        post = prior.update([1.0, 2.0, 3.0])
        lo80, hi80 = post.credible_interval(0.80)
        lo99, hi99 = post.credible_interval(0.99)
        assert (hi99 - lo99) > (hi80 - lo80)

    def test_credible_interval_invalid_level(self):
        nig = NormalInverseGamma()
        with pytest.raises(ValueError, match="level"):
            nig.credible_interval(1.5)
        with pytest.raises(ValueError, match="level"):
            nig.credible_interval(0.0)

    def test_prob_greater_than_symmetry(self):
        """For a symmetric prior centred at 0, P(mu > 0) ≈ 0.5."""
        nig = NormalInverseGamma(mu_0=0.0)
        assert nig.prob_greater_than(0.0) == pytest.approx(0.5, abs=1e-10)

    def test_prob_greater_than_after_positive_data(self):
        prior = NormalInverseGamma()
        post = prior.update([5.0, 6.0, 7.0, 5.5, 6.5])
        assert post.prob_greater_than(0.0) > 0.95

    def test_prob_less_than_complement(self):
        nig = NormalInverseGamma(mu_0=2.0, kappa=5.0, alpha=3.0, beta=1.0)
        threshold = 1.0
        p_gt = nig.prob_greater_than(threshold)
        p_lt = nig.prob_less_than(threshold)
        assert p_gt + p_lt == pytest.approx(1.0)

    def test_sequential_update_equals_batch(self):
        """Updating one-at-a-time should equal updating all at once."""
        prior = NormalInverseGamma(mu_0=1.0, kappa=2.0, alpha=3.0, beta=4.0)
        obs = [1.5, 2.5, 3.5]
        batch = prior.update(obs)
        sequential = prior
        for x in obs:
            sequential = sequential.update([x])
        assert sequential.mu_0 == pytest.approx(batch.mu_0, rel=1e-10)
        assert sequential.kappa == pytest.approx(batch.kappa, rel=1e-10)
        assert sequential.alpha == pytest.approx(batch.alpha, rel=1e-10)
        assert sequential.beta == pytest.approx(batch.beta, rel=1e-10)

    def test_immutability(self):
        """update() must not mutate the original."""
        prior = NormalInverseGamma()
        _ = prior.update([10.0])
        assert prior.mu_0 == 0.0
        assert prior.kappa == 1.0


class TestEffectPosteriors:
    def test_update_creates_entry(self):
        ep = EffectPosteriors(posteriors={})
        ep.update_effect("quality", "language", [3.0, 4.0])
        assert ("quality", "language") in ep.posteriors

    def test_update_accumulates(self):
        ep = EffectPosteriors(posteriors={})
        ep.update_effect("quality", "language", [3.0])
        ep.update_effect("quality", "language", [4.0])
        post = ep.posteriors[("quality", "language")]
        # After two updates the kappa should reflect 2 observations
        assert post.kappa == pytest.approx(3.0)  # 1 + 1 + 1 (prior + 2 updates)

    def test_credible_intervals(self):
        ep = EffectPosteriors(posteriors={})
        ep.update_effect("speed", "framework", [10.0, 11.0, 9.5])
        intervals = ep.credible_intervals(0.90)
        assert ("speed", "framework") in intervals
        lo, hi = intervals[("speed", "framework")]
        assert lo < hi

    def test_prob_positive(self):
        ep = EffectPosteriors(posteriors={})
        ep.update_effect("quality", "agent", [5.0, 6.0, 7.0])
        probs = ep.prob_positive()
        assert probs[("quality", "agent")] > 0.9

    def test_multiple_metrics(self):
        ep = EffectPosteriors(posteriors={})
        ep.update_effect("quality", "language", [3.0])
        ep.update_effect("speed", "language", [8.0])
        assert len(ep.posteriors) == 2
        probs = ep.prob_positive()
        assert len(probs) == 2
