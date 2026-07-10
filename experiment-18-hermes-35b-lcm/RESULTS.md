# Experiment 18 — the "best option" local stack cracks TypeScript

**The stack the whole local-model thread was building toward:** the **Hermes**
agent with the **`hermes-lcm`** plugin (a lossless, DAG-structured, SQLite-backed
context engine) driving **Qwen3.6-35B-A3B** (MLX 4-bit) served by **oMLX**, on the
bookshop task, `language[python, go, typescript, rust] × prompt[neutral, ATDD]`,
3 replicates, spec-gated by opus-4.8. $0 inference.

Three things change together vs [experiment-17](../experiment-17-hermes/RESULTS.md)
(Hermes on the 30B): a **stronger model** (35B vs 30B), **MLX serving via oMLX**
(whose Qwen tool-call kernels parse the `<tool_call><function=…>` format `mlx-lm`
could not), and Hermes' **advanced context engine** enabled (exp-17 used only its
default compression and *lost* to omp). So this is the "best option" stack, not a
clean single-variable ablation.

> Credit: **Birgitta Böckeler** (the [local-models writeup](https://martinfowler.com/articles/exploring-gen-ai/local-models-for-coding-experiences.html)
> that set the direction) and **kamihack** (@kamihack@mastodon.cr), whose hints —
> install oMLX via DMG, the real 35B MLX model, and the tool-call chat template —
> unblocked this entire stack.

---

## Result: the best local pass-proportion yet — and TypeScript finally passes

| prompt | language | pass | best req_cov | note |
|---|---|---:|---:|---|
| neutral | python | **3/3** | 1.00 | perfect |
| neutral | go | **2/3** | 1.00 | |
| neutral | typescript | **1/3** | 1.00 | **first local TS pass ever** |
| neutral | rust | 0/3 | 0.00 | 2 crashed (never terminated) |
| ATDD | python | 1/3 | 1.00 | |
| ATDD | go | 1/3 | 1.00 | |
| ATDD | typescript | **1/3** | 1.00 | |
| ATDD | rust | 0/3 | 0.00 | 1 crashed |
| **overall** | | **0.38 (9/24)** | | neutral **0.50**, ATDD 0.25 |

**The four-way comparison** on the same easy task (bookshop CRUD), all local
configs against the cloud frontier:

| stack | overall | neutral | **TypeScript** | python (neutral) |
|---|---:|---:|---:|---:|
| omp / Qwen3-Coder-30B (exp-16) | 0.33 | 0.33 | **0/3** | 3/3 |
| Hermes-default / 30B (exp-17) | 0.12 | 0.08 | **0/3** | 1/3 |
| **Hermes-lcm / Qwen3.6-35B (exp-18)** | **0.38** | **0.50** | **1/3 (both prompts)** | 3/3 |
| Claude frontier | ~0.98 | — | 1.00 | 0.94 |

- **TypeScript is cracked.** Every prior local configuration — omp and default
  Hermes alike — scored **0/3** on TypeScript. This stack passes it on **both**
  neutral and ATDD. That is the headline: the combination of a stronger model,
  MLX serving, and lossless context is what finally gets a local model over the
  TypeScript bar.
- **Best local reliability to date** — 0.38 overall, and **0.50 on the neutral
  prompt** (the highest any local stack has reached here), up from omp's 0.33 and
  a big jump over default Hermes' 0.12. So the `hermes-lcm` context engine
  *earns its keep* — the same agent without it (exp-17) was the worst local
  result; with it, on a stronger model, it is the best.
- **Faster and leaner, too.** MLX on oMLX (with its Qwen-specific Metal kernels)
  ran the 35B *faster* than the 30B on llama.cpp — the Python cell finished in
  ~250 s at ~420 K tokens with full coverage.
- **`neutral` beats `ATDD` again** (0.50 vs 0.25) — the third experiment in a row
  where the heavier test-first methodology hurts a local model rather than
  helping. Save ATDD for strong models.

## The one holdout: Rust never terminates

Rust stayed **0/3** — and the failure mode is specifically **non-termination**:
even after lowering Hermes' `max_turns` to 30, three Rust runs ran to retort's
30-minute hard wall and were recorded as **`crashed`** (one crashed *with* 0.70
coverage — the code was nearly there, the agent just never stopped). The 35B is
even more prone to the "keep going forever" behaviour on Rust than the 30B was.
This is now visible as a distinct signal because a `crashed` run (agent never
completed) is tracked separately from a `failed` one (a real, if unsuccessful,
data point) — the retry loop re-runs only the crashes, and the ETA/monitor treat
a genuine failure as progress.

## How to read it

The arc is: a local model on a laptop went from **0/3 on TypeScript and ~0.33
overall** (omp) to **passing TypeScript and 0.38 overall (0.50 on neutral)** —
purely by upgrading the *stack around the model*: MLX serving that handles the
model's tool format, a model one size up, and an agent that doesn't throw away its
own context. It is still far from the cloud frontier's ~0.98, and Rust remains out
of reach, but for the first time a free, private, on-device stack clears an *easy*
task's hardest language. That is a meaningfully different answer than "local
models can't do it."

*Data in `master.db`. Setup: oMLX serving `Qwen3.6-35B-A3B` on :8080; Hermes with
`hermes-lcm` (`plugins.enabled: [hermes-lcm]`, `context.engine: lcm`); provider
`api: http://127.0.0.1:8080/v1`, `api_mode: openai`. See `bookshop/workspace.yaml`.*
