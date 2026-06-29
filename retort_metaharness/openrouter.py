"""OpenRouter metering helper.

Conformant with the effort's rules: the API key is read from ``/tmp/.orkey``
(never hardcoded, never committed), every call is metered (tokens + $), and a
published per-token price table converts token counts to USD so cost_per_task
is a real arithmetic quantity, not a guess.

This module is intentionally dependency-free (stdlib ``urllib``) so it adds no
packages to Retort. The real metaharness runner does its own OpenRouter I/O;
this helper exists for (a) the price table that the runner glue uses to compute
cost_per_task, and (b) an optional direct-call path for simple single-shot cells.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_KEY_PATH = "/tmp/.orkey"

# Published OpenRouter prices, USD per 1M tokens (prompt, completion).
# Used to convert measured token counts -> cost_per_task. Update as prices move.
# Unknown models fall back to DEFAULT_PRICE.
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    "deepseek/deepseek-v4-pro": (0.28, 0.42),
    "z-ai/glm-5.2": (0.30, 0.50),
    "anthropic/claude-opus-4.8": (5.00, 25.00),
    "openai/gpt-5.2": (1.25, 10.00),
}
DEFAULT_PRICE: tuple[float, float] = (1.00, 3.00)


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def cost_usd(openrouter_model: str, usage: Usage) -> float:
    """Convert a token usage to USD using the published price table."""
    p_in, p_out = PRICE_PER_MTOK.get(openrouter_model, DEFAULT_PRICE)
    return (usage.prompt_tokens * p_in + usage.completion_tokens * p_out) / 1_000_000.0


def read_key(path: str | Path = DEFAULT_KEY_PATH) -> str | None:
    """Read the OpenRouter key from ``/tmp/.orkey`` (or $OPENROUTER_API_KEY)."""
    env = os.environ.get("OPENROUTER_API_KEY")
    if env:
        return env.strip()
    p = Path(path)
    if p.exists():
        txt = p.read_text(encoding="utf-8").strip()
        if txt:
            return txt
    return None


def have_key(path: str | Path = DEFAULT_KEY_PATH) -> bool:
    return read_key(path) is not None


@dataclass
class ChatResult:
    content: str
    usage: Usage
    cost_usd: float
    model: str


def chat(
    openrouter_model: str,
    messages: list[dict[str, str]],
    *,
    key_path: str | Path = DEFAULT_KEY_PATH,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    timeout: float = 120.0,
) -> ChatResult:
    """Single metered chat completion via OpenRouter.

    Raises RuntimeError if no key is available. Meters tokens and computes USD.
    """
    key = read_key(key_path)
    if not key:
        raise RuntimeError(
            f"No OpenRouter key. Put it in {key_path} or set OPENROUTER_API_KEY."
        )
    body = json.dumps(
        {
            "model": openrouter_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))

    content = payload["choices"][0]["message"]["content"]
    u = payload.get("usage", {})
    usage = Usage(
        prompt_tokens=int(u.get("prompt_tokens", 0)),
        completion_tokens=int(u.get("completion_tokens", 0)),
    )
    return ChatResult(
        content=content,
        usage=usage,
        cost_usd=cost_usd(openrouter_model, usage),
        model=openrouter_model,
    )
