"""Per-token cost estimation, for stacks whose CLI does not report a price.

WHY THIS EXISTS — the cost column has to mean ONE thing.

Retort's `cost_usd` is used to rank stacks ("cheapest model that clears your
language"), so every row must be the same kind of number. Today they are not:

* **Claude** (Max subscription) — the CLI reports `total_cost_usd`, which is the
  **list-price equivalent** of the tokens used. The subscription does not
  actually bill it. So it is already a per-token cost.
* **Local** (Hermes + oMLX) — genuinely \\$0 marginal, and recorded that way on
  purpose (`cost_override` in the reporting layer).
* **Codex** (ChatGPT subscription) — reports **no cost at all**. Left as-is it
  lands as \\$0, which is *not* a true \\$0: it is an unmeasured real cost. A
  cheapest-qualifying ranking would then pick Codex everywhere it passes, on a
  number that was never measured.

The fix is to put every metered stack on the same basis: **tokens × published
per-token rates**. That is what Claude already reports, so computing the same
thing for Codex makes the column comparable rather than coincidental.

A subscription's *marginal* cost being zero is a real and separate fact — it is
why the local stacks are ranked at \\$0 — but it is a property of the billing
arrangement, not of the stack's efficiency. List-price-per-token is what makes a
Claude row and a Codex row answerable to the same question.

PRICES GO STALE. The table below is dated and sourced; treat it as configuration,
not truth. An unknown model returns ``None`` rather than a guess — a fabricated
price is worse than a missing one, because it silently wins rankings.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Where the table came from and when. Update both when you touch the numbers.
PRICES_SOURCE = "https://developers.openai.com/api/docs/pricing"
PRICES_AS_OF = "2026-07-28"


@dataclass(frozen=True)
class TokenPrice:
    """USD per 1M tokens."""

    input: float
    cached_input: float
    output: float


# USD per 1M tokens, as of PRICES_AS_OF. `cached_input` is the discounted rate
# for the cached portion of the prompt.
OPENAI_PRICES: dict[str, TokenPrice] = {
    # GPT-5.6
    "gpt-5.6-sol": TokenPrice(5.00, 0.50, 30.00),
    "gpt-5.6-terra": TokenPrice(2.50, 0.25, 15.00),
    "gpt-5.6-luna": TokenPrice(1.00, 0.10, 6.00),
    # GPT-5.5 / 5.4
    "gpt-5.5": TokenPrice(5.00, 0.50, 30.00),
    "gpt-5.5-pro": TokenPrice(30.00, 30.00, 180.00),
    "gpt-5.4": TokenPrice(2.50, 0.25, 15.00),
    "gpt-5.4-mini": TokenPrice(0.75, 0.075, 4.50),
    "gpt-5.4-nano": TokenPrice(0.20, 0.02, 1.25),
    "gpt-5.4-pro": TokenPrice(30.00, 30.00, 180.00),
    # GPT-5.2 / 5.1 / 5
    "gpt-5.2": TokenPrice(1.75, 0.175, 14.00),
    "gpt-5.2-pro": TokenPrice(21.00, 21.00, 168.00),
    "gpt-5.1": TokenPrice(1.25, 0.125, 10.00),
    "gpt-5": TokenPrice(1.25, 0.125, 10.00),
    "gpt-5-mini": TokenPrice(0.25, 0.025, 2.00),
    "gpt-5-nano": TokenPrice(0.05, 0.005, 0.40),
    "gpt-5-pro": TokenPrice(15.00, 15.00, 120.00),
    # Codex family
    "gpt-5.3-codex": TokenPrice(1.75, 0.175, 14.00),
    "gpt-5.2-codex": TokenPrice(1.75, 0.175, 14.00),
    "gpt-5.1-codex-max": TokenPrice(1.25, 0.125, 10.00),
    "gpt-5.1-codex": TokenPrice(1.25, 0.125, 10.00),
    "gpt-5-codex": TokenPrice(1.25, 0.125, 10.00),
    "gpt-5.1-codex-mini": TokenPrice(0.25, 0.025, 2.00),
}


def normalize_model(model: str) -> str:
    """Strip provider prefixes and dated suffixes: ``openai/gpt-5-codex-2026-01-01``
    → ``gpt-5-codex``. Returns the input lowercased if nothing matches, so the
    caller still gets a miss rather than a wrong hit."""
    m = (model or "").strip().lower()
    if "/" in m:
        m = m.rsplit("/", 1)[-1]
    if m in OPENAI_PRICES:
        return m
    # Dated variants: drop a trailing -YYYY-MM-DD.
    parts = m.split("-")
    while len(parts) > 1:
        parts.pop()
        candidate = "-".join(parts)
        if candidate in OPENAI_PRICES:
            return candidate
    return m


def estimate_openai_cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float | None:
    """List-price cost for one run, or ``None`` if the model is not in the table.

    **Token semantics (OpenAI's, which Codex mirrors):**

    * ``input_tokens`` is the FULL prompt count and **includes** the cached
      portion. So the uncached remainder is billed at the input rate and
      ``cached_input_tokens`` at the (much lower) cached rate. Double-counting
      here would inflate long agentic runs badly, since cache reads dominate
      them — an Opus 5 run in exp-49 read 3.28 M cached tokens against 33 K
      generated.
    * ``output_tokens`` **includes** reasoning tokens; they are billed as
      output. Callers must NOT add ``reasoning_output_tokens`` on top.

    Both assumptions are worth re-checking against a real transcript when a new
    agent is wired up — see ``verify_token_semantics`` in the tests for the
    shape of that check.
    """
    price = OPENAI_PRICES.get(normalize_model(model))
    if price is None:
        return None
    cached = max(0, int(cached_input_tokens or 0))
    total_in = max(0, int(input_tokens or 0))
    uncached = max(0, total_in - cached)
    out = max(0, int(output_tokens or 0))
    return (
        uncached * price.input / 1_000_000
        + cached * price.cached_input / 1_000_000
        + out * price.output / 1_000_000
    )
