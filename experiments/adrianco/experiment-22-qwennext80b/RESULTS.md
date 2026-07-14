# Experiment 22 — a bigger model doesn't help: Qwen3-Coder-Next-80B vs the 35B

Drop the **80B-A3B** sibling onto the exact same stack that gave the best local
result (Hermes-lcm → oMLX → MLX), on the bookshop task's mainstream four
languages, and compare head-to-head with [exp-18](../experiment-18-hermes-35b-lcm/RESULTS.md)'s
**Qwen3.6-35B-A3B (0.38–0.50)**. The question: does doubling the model raise the
ceiling or crack Rust? Neutral prompt, 3 replicates, default self-repair second
chance on.

> Credit: Birgitta Böckeler (direction) and kamihack (the oMLX/model/tool-template
> pointers behind this stack).

## Result: bigger is *not* better here — slower, more non-terminating, no more reliable

| language | 35B (exp-18 neutral, first-try) | **80B first-try** | 80B repair-adjusted |
|---|---:|---:|---:|
| python | 1.00 | 0.33 | 0.33 |
| go | 0.67 | **1.00** | 1.00 |
| typescript | 0.33 | 0.00 | 0.17 |
| rust | 0.00 | 0.00 | 0.17 |
| **overall** | **0.50** | **0.33** | **0.42** |

- **On the metric that matters — first-try pass-proportion — the 80B is *worse*
  than the 35B: 0.33 vs 0.50.** Even counting the default second chance (repaired
  passes at half credit) it reaches only 0.42, still below the 35B's first-try
  0.50. Doubling the parameters bought no reliability on this easy task.
- **The 80B is slower and markedly more prone to non-termination.** It averaged
  ~12.6 min/run and produced **2 crashes** — a Rust run that ran to the 30-min
  wall having emitted **3.9M tokens**, and a TypeScript run that crashed *with*
  0.77 coverage (the code was nearly there; the agent just never stopped). The
  bigger model is more verbose, so it hits the wall more often — a net negative
  on a bounded harness.
- **The one real difference is noise, not signal.** Go went 2/3 → 3/3, Python 3/3
  → 1/3 — swings consistent with single-digit-replicate variance on a task both
  models find easy. The second chance did earn the 80B a TypeScript and a Rust
  repair (0.5 each), but not enough to overcome the slower, crashier first pass.

## How to read it

This is the local mirror of the cloud finding that "at the top, extra spend buys
nothing." The 35B was **already competent** on mainstream languages — so there is
no reliability headroom for a bigger model to capture, and the 80B's extra size
shows up only as **more tokens, more time, and more runs that never terminate.**
For this class of task, **Qwen3.6-35B-A3B remains the best local stack**, and the
next thing worth trying is not a *bigger* model but a *different* one —
**Devstral Small 2** (24B, agent-tuned, fast) is the queued next arm: a different
bet than "just scale up."

*Data in `master.db`. Setup: `mlx-community/Qwen3-Coder-Next-4bit` (~45 GB) served
by oMLX; identical Hermes-lcm stack to exp-18.*
