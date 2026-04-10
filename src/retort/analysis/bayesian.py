"""Bayesian updating with conjugate priors for effect-size estimation.

Uses the Normal-Inverse-Gamma (NIG) conjugate family so that posterior
updates are closed-form (no MCMC needed).  The NIG prior on (mu, sigma^2)
yields a marginal Student-t posterior on mu, from which credible intervals
and promotion-gate probabilities are computed via scipy.

Typical flow
------------
1. Create a ``NormalInverseGamma`` prior (uninformative defaults provided).
2. Call ``update(observations)`` with observed effect sizes.
3. Query ``credible_interval()``, ``posterior_mean``, or
   ``prob_greater_than(threshold)`` to feed promotion gates.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike
from scipy import stats


@dataclass
class NormalInverseGamma:
    """Normal-Inverse-Gamma posterior for (mu, sigma^2).

    Parameterisation follows Murphy (2007):
        mu | sigma^2  ~  N(mu_0, sigma^2 / kappa)
        sigma^2        ~  InvGamma(alpha, beta)

    The marginal posterior on mu (integrating out sigma^2) is a scaled
    Student-t with 2*alpha degrees of freedom.

    Parameters
    ----------
    mu_0 : float
        Prior mean of the effect.
    kappa : float
        Pseudo-observation count weighting the prior mean (> 0).
    alpha : float
        Shape of the inverse-gamma on variance (> 0).
    beta : float
        Scale of the inverse-gamma on variance (> 0).
    """

    mu_0: float = 0.0
    kappa: float = 1.0
    alpha: float = 1.0
    beta: float = 1.0

    def __post_init__(self) -> None:
        if self.kappa <= 0:
            raise ValueError(f"kappa must be > 0, got {self.kappa}")
        if self.alpha <= 0:
            raise ValueError(f"alpha must be > 0, got {self.alpha}")
        if self.beta <= 0:
            raise ValueError(f"beta must be > 0, got {self.beta}")

    def update(self, observations: ArrayLike) -> NormalInverseGamma:
        """Return a new posterior after observing *observations*.

        Parameters
        ----------
        observations : array-like of float
            New data points (e.g. per-run effect sizes for one metric).

        Returns
        -------
        NormalInverseGamma
            Updated posterior (this object is not mutated).
        """
        obs = np.asarray(observations, dtype=np.float64)
        if obs.size == 0:
            return NormalInverseGamma(
                mu_0=self.mu_0,
                kappa=self.kappa,
                alpha=self.alpha,
                beta=self.beta,
            )
        n = obs.size
        x_bar = float(obs.mean())
        sample_var = float(obs.var(ddof=0))  # biased variance for NIG update

        kappa_n = self.kappa + n
        mu_n = (self.kappa * self.mu_0 + n * x_bar) / kappa_n
        alpha_n = self.alpha + n / 2.0
        beta_n = (
            self.beta
            + 0.5 * n * sample_var
            + 0.5 * (n * self.kappa / kappa_n) * (x_bar - self.mu_0) ** 2
        )
        return NormalInverseGamma(
            mu_0=mu_n,
            kappa=kappa_n,
            alpha=alpha_n,
            beta=beta_n,
        )

    # ------------------------------------------------------------------
    # Marginal posterior on mu  (Student-t)
    # ------------------------------------------------------------------

    @property
    def posterior_mean(self) -> float:
        """Posterior mean of mu."""
        return self.mu_0

    @property
    def posterior_variance(self) -> float:
        """Posterior variance of mu (finite when alpha > 1)."""
        if self.alpha <= 1:
            return float("inf")
        return float(self.beta / (self.kappa * (self.alpha - 1)))

    @property
    def _marginal_t(self) -> stats.t:
        """Marginal Student-t distribution on mu."""
        df = 2.0 * self.alpha
        loc = self.mu_0
        scale = np.sqrt(self.beta / (self.kappa * self.alpha))
        return stats.t(df=df, loc=loc, scale=scale)

    def credible_interval(self, level: float = 0.95) -> tuple[float, float]:
        """Symmetric credible interval for mu.

        Parameters
        ----------
        level : float
            Probability mass inside the interval (default 0.95).

        Returns
        -------
        (lower, upper)
        """
        if not 0 < level < 1:
            raise ValueError(f"level must be in (0, 1), got {level}")
        tail = (1.0 - level) / 2.0
        t = self._marginal_t
        lo = float(t.ppf(tail))
        hi = float(t.ppf(1.0 - tail))
        return (lo, hi)

    def prob_greater_than(self, threshold: float) -> float:
        """P(mu > threshold) under the marginal posterior.

        Useful for promotion gates: e.g. P(effect > 0) > 0.80.
        """
        return float(1.0 - self._marginal_t.cdf(threshold))

    def prob_less_than(self, threshold: float) -> float:
        """P(mu < threshold) under the marginal posterior."""
        return float(self._marginal_t.cdf(threshold))


# ------------------------------------------------------------------
# Multi-effect convenience wrapper
# ------------------------------------------------------------------


@dataclass
class EffectPosteriors:
    """Collection of posteriors keyed by (metric, factor/interaction) name.

    Provides bulk queries used by the promotion gate logic.
    """

    posteriors: dict[tuple[str, str], NormalInverseGamma]

    def update_effect(
        self,
        metric: str,
        effect: str,
        observations: ArrayLike,
    ) -> None:
        """Update (or initialise) the posterior for one (metric, effect) pair."""
        key = (metric, effect)
        prior = self.posteriors.get(key, NormalInverseGamma())
        self.posteriors[key] = prior.update(observations)

    def credible_intervals(
        self, level: float = 0.95
    ) -> dict[tuple[str, str], tuple[float, float]]:
        """Return credible intervals for every tracked effect."""
        return {k: v.credible_interval(level) for k, v in self.posteriors.items()}

    def prob_positive(self) -> dict[tuple[str, str], float]:
        """P(effect > 0) for every tracked effect."""
        return {k: v.prob_greater_than(0.0) for k, v in self.posteriors.items()}
