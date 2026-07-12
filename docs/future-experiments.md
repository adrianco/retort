# Future experiments & model candidates

A running scratchpad of ideas to try next, so they aren't lost. Nothing here is
committed to; it's a queue. Current stack context: the local-model work runs on a
**MacBook Pro M5, 64 GB** (GPU wired limit raised to ~56 GB), serving MLX models
via **oMLX** and driving them with the **Hermes** agent (+ `hermes-lcm` lossless
SQLite context). Best result so far: exp-18, Qwen3.6-35B-A3B, **0.38** pass-
proportion on bookshop (cracked TypeScript; Rust still fails/non-terminates).

Credits for the local-model direction: **Birgitta Böckeler** (the
[local-models writeup](https://martinfowler.com/articles/exploring-gen-ai/local-models-for-coding-experiences.html))
and **kamihack** (@kamihack@mastodon.cr) for the oMLX / model / tool-template
pointers.

---

## Candidate models to test next (claim better than what we've run, and fit 64 GB)

Fit budget: ~56 GB wired GPU → **~45 GB weight ceiling** (leaving room for KV +
compute buffers). We've already run Qwen3-Coder-30B-A3B and Qwen3.6-35B-A3B (both
MoE, ~3B active, ~18–20 GB Q4).

| Model | Size (total/active) | Fit on 64 GB (MLX) | Claim vs ours | Tool format |
|---|---|---|---|---|
| **Qwen3-Coder-Next (80B-A3B)** ⭐ primary | 80B / 3B MoE | 4-bit ≈ **44.8 GB** (tight; reduce ctx) or 3-bit ≈ **34 GB** (comfortable) | "~96% of the 480B flagship"; "comparable to 10–20× more active params" | **Same Qwen `<tool_call>` format oMLX already parses** — zero new integration risk |
| ~~**Devstral Small 2 (24B)**~~ **BLOCKED** | 24B dense | ~14 GB Q4 — fits fine | 68% SWE-bench; agent-tuned | **oMLX does NOT parse Devstral's Mistral `[TOOL_CALLS]` format** (it emits the call as text; Hermes executes nothing — gate-probe on `mlx-community/Devstral-Small-2507-4bit` confirmed). Same wall as exp-12. Would need a different serving layer (vLLM with the mistral tool parser, or llama.cpp with the right template). |
| gpt-oss-120b | 117B / 5.1B MoE | **~64–65 GB — likely won't fit** at 56 GB wired | best raw coder (83% Multi-LCB; Codeforces 2622) | Harmony format; only if we push memory limits (OOM risk) |
| GLM-4.5-Air / 4.7-Flash | ~100B+ MoE | borderline → probably too tight | SWE-bench ~57.6% (Air) | MLX-tested; confirm exact size before trying |

**Excluded — too big (multi-GPU tier):** MiniMax M3 (428B/23B; 4-bit ≈ 228 GB —
tops open SWE-Bench Pro but no chance), GLM-4.6 (355B), DeepSeek-V4-Pro,
Kimi K2.6, Qwen3-Coder-480B.

**Recommendation:** add **Qwen3-Coder-Next (80B-A3B)** first — the bigger sibling
of what we've run, same architecture/tool-format, strongest fitting quality
claim. Direct "80B vs 35B, same stack" comparison: does doubling the model crack
Rust / raise the 0.38 ceiling? Optionally add **Devstral Small 2** as a cheap
second arm (different bet: agent-tuned, not just bigger).

> **Status — the fitting + tool-calling search is largely exhausted; Qwen3.6-35B
> remains the best local stack.**
> - **exp-22 (Qwen3-Coder-Next-80B):** bigger is NOT better — first-try 0.33 vs
>   the 35B's 0.50, slower, more non-terminating (Rust to the wall at 3.9M
>   tokens). The 35B has no headroom to improve on (local mirror of "at the top,
>   extra spend buys nothing"). Did not expand to 9 languages.
> - **Devstral (different bet, exp-23):** unblocked by switching the serving layer
>   to **llama.cpp `--jinja`** (parses the Mistral tool format oMLX can't) — the
>   "allow for either layer" result. But it scored the WORST (0.17, 7/12 never
>   terminating), and it's tuned for OpenHands not Hermes (wrong harness). Neither
>   bigger nor agent-tuned-different beat the general 35B.
> - **What's left, all with a catch:** gpt-oss-120b (best raw coder but ~64 GB —
>   over the 56 GB wired limit; would need to push memory limits) or gpt-oss-20b
>   (fits, Harmony format — oMLX has a `harmony` reasoning parser, tool-parse
>   unverified — but 20B is unlikely to beat the 35B); GLM/MiniMax/DeepSeek are
>   all too big. To try Devstral or a Mistral-family coder, switch the serving
>   layer to vLLM or llama.cpp (they parse the Mistral tool format).
>
> **Bottom line:** among models that both fit 64 GB and tool-call cleanly via
> oMLX, **Qwen3.6-35B-A3B is the winner.** Further gains need either more memory
> (bigger models) or a different serving layer (broader tool-format support).

MLX builds seen: `mlx-community/Qwen3-Next-80B-A3B-Instruct-4bit` (44.8 GB,
general instruct); `majentik/Qwen3-Coder-Next-MLX-3bit` (~34 GB, coding-tuned);
`unsloth/Qwen3-Coder-Next-GGUF` (llama.cpp fallback).

---

## exp-21 — self-repair with evaluation feedback

Give exp-20's **near-miss** failures a **second try, prompted with the evaluation
results**, across all 9 languages, and measure the lift over the exp-20 baseline.
This is the model's first sight of the *independent* evaluation (it never saw the
spec-gate's requirement checklist or the scorer's build/test errors first pass),
so it's a clean test of self-repair.

- **Scope:** every exp-20 failed cell that produced a code artifact (skip $0
  crashes with no code).
- **Feedback (both, per failure type):** spec-failed runs → `assessment.json`
  `top_findings` (unmet requirements); tests-didn't-run runs → scorer /
  `retort diagnose` build-test error.
- **Mechanism:** seed a fresh playpen with the failed code + TASK.md, inject a
  REPAIR prompt ("your previous attempt is here; the evaluation found <feedback>;
  fix it, don't start over"), run the same stack, rescore + spec-gate. New
  exp-21 DB; compare pass-proportion vs exp-20 per language.
- **Attempts:** one second try to start; extend to an iterative loop if it helps.
- **Scoring — half credit on pass-proportion ONLY; quality metrics reflect final
  quality.** A repaired pass is worth less as a *reliability* signal (it needed the
  evaluation handed to it), but the *code it ends up with* is as good as it is. So:
  - **Repair-adjusted pass-proportion** (headline): first-try pass = 1.0,
    second-try/repaired pass = **0.5**, still-failing = 0.
  - **All quality/coverage metrics stay at their true final values** — code_quality,
    test_coverage, defect_rate, maintainability, idiomatic, requirement_coverage,
    token_efficiency are recorded raw (the repaired code's actual quality). Do NOT
    halve them.
  - The 0.5 is a *pass-count* weight applied at the reporting layer, not a
    discount on the stored scores. Gate on raw req_cov; a repaired req_cov==1.0
    is a real pass that simply counts 0.5 toward the adjusted pass-proportion.
- **Build:** needs a seed-workspace + augment-prompt hook (a `retort repair`
  subcommand or a script reusing LocalRunner) plus a repair-adjusted scorer view.

---

## Resolved — KV prefix cache (exp-24)

- **SSD prefix cache does NOT rescue the 80B.** oMLX's on-disk prefix cache is off
  by default (`--paged-ssd-cache-dir` enables it), so exp-22 ran without it. exp-24
  turned it on and re-ran the identical 80B grid:
  [RESULTS](../experiment-24-qwennext80b-cached/RESULTS.md). First-try pass-
  proportion **0.33 → 0.33**, crashes **2 → 3**, completed-run duration unchanged.
  The cache demonstrably *hits* (an 88K-token prefix restored in ~2.5 s vs ~150 s
  cold, hybrid DeltaNet layers snapshotted to disk correctly) — but our runs are
  **generation-bound, not prefill-bound**: the 80B does ~61 tok/s, `hermes-lcm`
  grows context to 75–88K tokens, each turn is ~75 s of generation, and many turns
  march into the 30-min wall regardless of prefill speed. The mrzk.io 137× is the
  mirror image of our workload (huge fixed prompt, little generation). **"Bigger
  isn't better" stands; the mechanism is throughput, not caching.** Leave the cache
  on (free prefill latency) but don't expect pass-proportion from it.

## Cheap opportunistic checks

- **oMLX 0.5.0 MTP (multi-token prediction) — now the top speed lever.** exp-24
  showed the binding constraint is **generation throughput**, so lossless
  speculative decoding is the right thing to try next: does faster generation let
  slow-but-terminating runs (esp. the 80B, and Rust/Go on the 35B) finish before
  the 30-min wall (crash → completed)? It won't raise *quality*, but converting
  crashes to real data points is exactly what our wall-bound failures need. Matters
  far more for the slow 80B than the 35B.
- **Timeout / turn-cap tuning.** Several failures were non-termination at the
  wall. A higher timeout or lower `max_turns` converts crashes to real data
  points more cleanly than MTP does.

---

## Standing method notes

- Incremental design: add ONE new model/factor at a time; run only the new cells;
  compare against `master.db`. Never re-run existing baselines.
- Spec-gate always ON. Clean archive bloat (truncate `_agent_stdout.log`, strip
  node_modules/target) before committing.
- After each experiment: update `model-blog.md` + push to GitHub.
