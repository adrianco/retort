# Experiment 24 — does the KV-cache trick rescue the 80B? (prefix cache ON vs OFF)

A methodology ablation, not a new model. Prompted by the
[qMLX / "min-maxing a Mac Studio"](https://mrzk.io/posts/qmlx-maximising-ai-psychosis-minmaxing-mac-studio/)
write-up, which reports enormous speedups from an on-disk KV **prefix cache**
(their number: ~137× on a large fixed prompt). Our earlier
[exp-22](../experiment-22-qwennext80b/RESULTS.md) ran **Qwen3-Coder-Next-80B-A3B**
and found it *slower and crashier* than the smaller 35B — but we later discovered
oMLX's SSD prefix cache is **OFF by default** (it needs `--paged-ssd-cache-dir`).
So exp-22 was re-prefilling context every turn. **Hypothesis:** the 80B's poor
result was a serving artifact; turn the cache on and it should speed up, stop
hitting the 30-minute wall, and score higher.

Same everything as exp-22 (Hermes + `hermes-lcm`, mainstream 4 languages, neutral
prompt, 3 replicates, default second-chance on). The **only** change: oMLX started
with `--paged-ssd-cache-dir ~/.cache/omlx-ssd --paged-ssd-cache-max-size 120GB`.

> Credit: Birgitta Böckeler (the local-model direction) and kamihack (the oMLX /
> serving pointers). KV-cache framing from the mrzk.io qMLX post.

## Result: the cache works — and it changes nothing here

| metric | exp-22 (cache **OFF**) | exp-24 (cache **ON**) |
|---|---:|---:|
| first-try pass-proportion | **0.33** (4/12) | **0.33** (4/12) |
| total req_cov passes (incl. repair) | 6 | 4 |
| crashed at the 30-min wall | 2 | 3 |
| completed-run avg duration | 555 s | 543 s |

Per language (cache ON): **go 2/3, python 2/3, rust 0/3, typescript 0/3.**
Rust and TypeScript, which occasionally passed in exp-22, regressed to zero here;
Go lost one replicate to a wall-crash. Within n=3-per-cell noise the headline is
flat, and if anything exp-24 is *worse* (no repair landed, two languages to zero).
**Enabling the prefix cache did not rescue the 80B.**

## Why — the cache is not the bottleneck; generation throughput is

The oMLX log proves the SSD prefix cache is **hitting**, even on this hybrid
(DeltaNet + dense) architecture — oMLX snapshots the "non-sliceable" stateful
layers to disk exactly as the post describes:

```
238 tokens in 7.93s (44.0 tok/s), prompt: 88358
```

An **88,358-token prompt** is prepared and 238 tokens generated in **7.9 s**.
Generation alone (238 ÷ 44 tok/s) is ~5.4 s, so the 88K-token prefix was restored
in **~2.5 s**. A *cold* 88K prefill on this model costs ~150 s. The cache is
working as advertised.

But it buys us nothing at the experiment level, because our runs are
**generation-bound, not prefill-bound**:

- The 80B generates at a median **~61 tok/s** (min 0.5, max 95 across the run).
- `hermes-lcm` grows the working context to **75–88K tokens** over a run.
- A turn that emits ~3.4K tokens is **~75 s of pure generation**, and the agentic
  loop needs many such turns to build + test a CRUD service.
- That marches into the **30-minute wall regardless of how fast the prefix loads.**

The mrzk.io result isn't wrong — it's the **mirror image** of our workload. Their
137× comes from a huge *fixed* prompt with little generation (all prefill, cache-
perfect). Agentic coding is a moderate prompt plus heavy multi-turn *generation*,
so prefix caching saves **seconds** while generation costs **minutes**.

## What this settles

1. **exp-22 was not a cache artifact.** The 80B's poor showing is its real
   behavior in this stack: low tok/s × many turns × large contexts → wall. Turning
   on the exact optimization that "should" have fixed it did not move the number.
   **"Bigger isn't better" stands, and now we know the mechanism.**
2. **The right lever for slow big models is generation throughput**, not the KV
   cache: multi-token / speculative decoding (oMLX MTP), a faster/smaller model, or
   capping context growth. This reframes the standing MTP note — it matters far
   more for the 80B than for the 35B, and only as a *crash→completion* converter,
   not a quality lever.
3. **The prefix cache is still worth leaving on** — it's free correctness-neutral
   latency on the prefill side and would help a *different* workload (long fixed
   system prompt, short completions). It simply isn't our bottleneck.

**Qwen3.6-35B-A3B remains the best local stack.** This ablation is kept in its own
`retort.db` and deliberately **not** merged into `master.db`: it re-runs an
existing model with a serving change, so folding it into the model grid would
double-count the 80B. The durable takeaway is methodological — *measure where the
time actually goes before attributing a model's score to the model.*

*Setup: `mlx-community/Qwen3-Next-80B-A3B-Instruct-4bit` (44.8 GB) via oMLX on
:8080 with `--paged-ssd-cache-dir`; Hermes + `hermes-lcm`; M5 MacBook Pro 64 GB,
GPU wired limit 56 GB. Cache-hit and throughput figures from the oMLX server log.*
