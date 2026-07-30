"""Tests for per-token cost estimation."""

from __future__ import annotations

import pytest

from retort.pricing import (
    OPENAI_PRICES,
    estimate_openai_cost_usd,
    normalize_model,
)


def test_known_model_costs_are_computed_from_published_rates():
    # gpt-5.6-luna: $1.00 in / $0.10 cached / $6.00 out per 1M.
    cost = estimate_openai_cost_usd(
        "gpt-5.6-luna", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert cost == pytest.approx(7.00)


def test_cached_tokens_are_billed_at_the_cached_rate_and_not_double_counted():
    """`input_tokens` INCLUDES the cached portion.

    Treating them as additive would badly inflate agentic runs, where cache
    reads dominate — exp-49 measured an Opus 5 run at 3.28 M cache reads
    against 33 K generated tokens.
    """
    # 1M prompt of which 900K cached: 100K @ $1.00/M + 900K @ $0.10/M = $0.19
    cost = estimate_openai_cost_usd(
        "gpt-5.6-luna",
        input_tokens=1_000_000,
        cached_input_tokens=900_000,
        output_tokens=0,
    )
    assert cost == pytest.approx(0.19)

    # Fully-cached prompt costs the cached rate, not zero and not full price.
    fully_cached = estimate_openai_cost_usd(
        "gpt-5.6-luna",
        input_tokens=1_000_000,
        cached_input_tokens=1_000_000,
        output_tokens=0,
    )
    assert fully_cached == pytest.approx(0.10)


def test_cached_greater_than_input_does_not_go_negative():
    cost = estimate_openai_cost_usd(
        "gpt-5.6-luna", input_tokens=100, cached_input_tokens=5_000, output_tokens=0
    )
    assert cost >= 0.0


def test_unknown_model_returns_none_rather_than_a_guess():
    """A fabricated price silently wins cheapest-qualifying rankings."""
    assert estimate_openai_cost_usd("totally-made-up", input_tokens=1, output_tokens=1) is None


def test_normalize_strips_provider_prefix_and_date_suffix():
    assert normalize_model("openai/gpt-5-codex") == "gpt-5-codex"
    assert normalize_model("gpt-5-codex-2026-01-15") == "gpt-5-codex"
    assert normalize_model("GPT-5.6-Luna") == "gpt-5.6-luna"
    # A genuine miss stays a miss.
    assert normalize_model("llama-4") not in OPENAI_PRICES


def test_judge_models_from_pr45_are_priced():
    """The Codex PR uses gpt-5.6-luna (implementer) and gpt-5.6-terra (judge)."""
    for m in ("gpt-5.6-luna", "gpt-5.6-terra"):
        assert estimate_openai_cost_usd(m, input_tokens=1000, output_tokens=1000) > 0


def test_zero_usage_is_zero_not_none():
    assert estimate_openai_cost_usd("gpt-5-codex", input_tokens=0, output_tokens=0) == 0.0


def test_price_table_is_dated_and_sourced():
    """Prices go stale; the table must say when and from where."""
    from retort import pricing

    assert pricing.PRICES_AS_OF
    assert pricing.PRICES_SOURCE.startswith("http")


def test_gpt56_charges_for_cache_writes_at_1_25x_input():
    """GPT-5.6+ bills cache WRITES at 1.25x the uncached input rate.

    Source: OpenAI prompt-caching guide — "Cache writes have no additional fee on
    models before the GPT-5.6 family"; on 5.6+ "cache writes cost 1.25x the
    uncached input token rate". Missing this under-reports the FIRST run of a
    batch, which is the one that populates the shared prefix.
    """
    from retort.pricing import charges_for_cache_writes

    assert charges_for_cache_writes("gpt-5.6-terra")
    assert not charges_for_cache_writes("gpt-5-codex")

    # Terra input $2.50/M -> a 1M-token cache write costs 2.50 * 1.25 = $3.125
    with_write = estimate_openai_cost_usd(
        "gpt-5.6-terra", input_tokens=0, output_tokens=0,
        cache_write_input_tokens=1_000_000,
    )
    assert with_write == pytest.approx(3.125)


def test_pre_56_families_write_to_cache_for_free():
    no_charge = estimate_openai_cost_usd(
        "gpt-5-codex", input_tokens=0, output_tokens=0,
        cache_write_input_tokens=1_000_000,
    )
    assert no_charge == pytest.approx(0.0)


def test_real_terra_cell_reproduces_the_recorded_cost():
    """Hand-checked against an exp-55 archive (effort=high, go, rep1).

    raw: input 214,564 / cached 196,608 (92%) / cache_write 0 / output 6,770
    """
    cost = estimate_openai_cost_usd(
        "gpt-5.6-terra",
        input_tokens=214_564, cached_input_tokens=196_608,
        cache_write_input_tokens=0, output_tokens=6_770,
    )
    assert cost == pytest.approx(0.1956, abs=0.001)
