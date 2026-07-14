# experiment-7 — results

**Opus-4.8 fast mode** (`/fast` — same model, faster output) on both tasks, vs the regular-4.8 baseline in experiments 5 & 6. 24 scored runs · generated from `master.db` (clean opus-4.6 second-opinion spec gate).

> **Cost note:** fast mode is billed at **2× the standard per-token rate** ($10/$50 vs $5/$25 per Mtok input/output — see the [Opus 4.8 announcement](https://www.anthropic.com/news/claude-opus-4-8)). The Claude CLI's reported `total_cost_usd` computes at the *standard* rate, so retort applies the 2× multiplier for fast-mode runs. The Cost column below is the **true billed cost** (already doubled).

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

## Brazil-soccer-MCP (hard task)

| Language | Model | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.8-fast | 3 | 3/3 = 1.00 | 1.00 | 712 | 6.18 | 0.83 |
| go | opus-4.8-fast | 3 | 3/3 = 1.00 | 0.62 | 959 | 9.90 | 1.00 |
| python | opus-4.8-fast | 3 | 3/3 = 1.00 | 0.92 | 967 | 9.91 | 0.67 |
| rust | opus-4.8-fast | 3 | 3/3 = 1.00 | 1.00 | 909 | 8.90 | 0.83 |

## REST-API CRUD (bookshop, easy task)

| Language | Model | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.8-fast | 3 | 3/3 = 1.00 | 1.00 | 208 | 1.37 | 0.83 |
| go | opus-4.8-fast | 3 | 3/3 = 1.00 | 0.71 | 140 | 1.17 | 1.00 |
| python | opus-4.8-fast | 3 | 3/3 = 1.00 | 0.97 | 90 | 0.74 | 0.89 |
| rust | opus-4.8-fast | 3 | 3/3 = 1.00 | 1.00 | 135 | 1.06 | 0.83 |

Every cell holds pass-proportion **1.00** — fast mode matched regular-4.8's reliability. But at the 2× price premium it is **more expensive than regular 4.8** on nearly every cell (and on the hard task it isn't even reliably faster). See the [README](../../../README.md#fast-mode-speed-for-a-2x-price-premium) for the full comparison.
