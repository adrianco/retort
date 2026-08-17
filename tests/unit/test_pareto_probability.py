"""Monte-Carlo Pareto probability — 62 lines of statistics nothing called.

Found unused by M1's dead-code pass. Two trivial accessors alongside it were
deleted; this one was kept and covered instead. It is substantial, it consumes
the `NormalInverseGamma` posteriors from the live `bayesian` module, and
untested Monte-Carlo code is a liability rather than an asset — a wrong answer
here would look entirely plausible.

The cases below have answers derivable without running the sampler.
"""
from __future__ import annotations

import numpy as np

from retort.analysis.bayesian import NormalInverseGamma
from retort.analysis.pareto import prob_pareto_non_dominated


def _posterior(values):
    """A posterior fitted to observations, so its mean sits near their mean."""
    return NormalInverseGamma().update(np.asarray(values, dtype=float))


def test_a_clearly_dominant_solution_is_almost_certainly_non_dominated():
    """Better on every metric ⇒ P ≈ 1, and the loser ⇒ P ≈ 0."""
    post = {
        "good": {"quality": _posterior([0.95] * 8), "speed": _posterior([0.95] * 8)},
        "bad": {"quality": _posterior([0.10] * 8), "speed": _posterior([0.10] * 8)},
    }
    p = prob_pareto_non_dominated(post, ["quality", "speed"], n_samples=2000)

    assert p["good"] > 0.95
    assert p["bad"] < 0.05


def test_a_genuine_trade_off_leaves_both_on_the_frontier():
    """Each wins one metric ⇒ neither dominates ⇒ both ≈ 1."""
    post = {
        "fast": {"quality": _posterior([0.20] * 8), "speed": _posterior([0.95] * 8)},
        "careful": {"quality": _posterior([0.95] * 8), "speed": _posterior([0.20] * 8)},
    }
    p = prob_pareto_non_dominated(post, ["quality", "speed"], n_samples=2000)

    assert p["fast"] > 0.95
    assert p["careful"] > 0.95


def test_probabilities_are_probabilities():
    post = {n: {"m": _posterior([v] * 6)} for n, v in
            (("a", 0.9), ("b", 0.5), ("c", 0.1))}
    p = prob_pareto_non_dominated(post, ["m"], n_samples=1000)

    assert set(p) == {"a", "b", "c"}
    assert all(0.0 <= v <= 1.0 for v in p.values())


def test_overlapping_posteriors_are_uncertain_not_decisive():
    """Nearly identical evidence must NOT produce a confident winner.

    This is the property that makes the function worth keeping: a plain
    point-estimate frontier would pick a winner from noise, and this should not.
    """
    post = {
        "x": {"m": _posterior([0.50, 0.52, 0.48, 0.51])},
        "y": {"m": _posterior([0.51, 0.49, 0.50, 0.52])},
    }
    p = prob_pareto_non_dominated(post, ["m"], n_samples=3000)

    assert 0.2 < p["x"] < 1.0
    assert 0.2 < p["y"] < 1.0


def test_seed_makes_it_reproducible():
    post = {n: {"m": _posterior([v] * 6)} for n, v in (("a", 0.8), ("b", 0.4))}
    a = prob_pareto_non_dominated(post, ["m"], n_samples=500, rng_seed=7)
    b = prob_pareto_non_dominated(post, ["m"], n_samples=500, rng_seed=7)
    assert a == b
