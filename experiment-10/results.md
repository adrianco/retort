# experiment-10 — results

**Claude Fable 5** (`claude-fable-5`) on both tasks, vs the regular-Opus-4.8 baseline (exp-5/6) and Opus-4.8 **fast mode** (exp-7) on the *same* cells. 24 scored runs (4 languages × 3 replicates × 2 tasks), `requirement_coverage` from the opus-4.6 second-opinion spec gate.

> **Cost note:** Fable 5 is priced at **$10/$50 per Mtok input/output — 2× Opus 4.8's standard rate** ($5/$25), i.e. the *same* per-token rate as Opus-4.8 fast mode, but it is a **distinct model** (the CLI prices it natively, so no 2× post-correction is applied — the figures below are the model's reported cost). It sits a tier **above** Opus 4.8.

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

## Brazil-soccer-MCP (hard task)

| Language | Model | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | fable-5 | 3 | 3/3 = 1.00 | 1.00 | 1163 | 9.49 | 0.83 |
| go | fable-5 | 3 | 3/3 = 1.00 | 0.78 | 998 | 8.59 | 1.00 |
| python | fable-5 | 3 | 3/3 = 1.00 | 0.94 | 932 | 8.20 | 0.78 |
| rust | fable-5 | 3 | 3/3 = 1.00 | 1.00 | 1061 | 9.63 | 0.83 |
| **all** | **fable-5** | **12** | **12/12 = 1.00** | 0.93 | **1039** | **8.98** | — |

## REST-API CRUD (bookshop, easy task)

| Language | Model | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | fable-5 | 3 | 3/3 = 1.00 | 1.00 | 187 | 1.35 | 0.83 |
| go | fable-5 | 3 | 3/3 = 1.00 | 0.73 | 149 | 1.09 | 1.00 |
| python | fable-5 | 3 | 3/3 = 1.00 | 0.98 | 96 | 0.76 | 0.64 |
| rust | fable-5 | 3 | 3/3 = 1.00 | 1.00 | 142 | 1.00 | 0.83 |
| **all** | **fable-5** | **12** | **12/12 = 1.00** | 0.93 | **143** | **1.05** | — |

## Headline: a tier above 4.8 buys no measurable reliability — at ~2× the cost

Every Fable 5 cell holds pass-proportion **1.00**, on both tasks, all four languages. So does regular Opus 4.8, and so does Opus-4.8 fast mode. **Where 4.8 is already 1.00, a model a tier above it has nowhere to go** — the reliability ceiling is already reached.

Same-cell comparison (4 shared languages, hard task):

| Model | Pass (Brazil) | Pass (REST) | Speed Brazil (s) | Cost Brazil ($) | Per-tok rate |
|---|---:|---:|---:|---:|---|
| opus-4.8 (exp-5/6) | 1.00 | 1.00 | ~947 | ~5.09 | $5/$25 |
| opus-4.8-fast (exp-7) | 1.00 | 1.00 | ~887 | ~8.72 | $10/$50 |
| **fable-5 (exp-10)** | **1.00** | **1.00** | **~1039** | **~8.98** | $10/$50 |

Per-language, hard task (Pass · Speed s · Cost $):

| Lang | fable-5 | opus-4.8 | opus-4.8-fast |
|---|---|---|---|
| clojure | 1.00 · 1163 · 9.49 | 1.00 · 942 · 4.58 | 1.00 · 712 · 6.18 |
| go | 1.00 · 998 · 8.59 | 1.00 · 867 · 4.59 | 1.00 · 959 · 9.90 |
| python | 1.00 · 932 · 8.20 | 1.00 · 899 · 5.10 | 1.00 · 967 · 9.91 |
| rust | 1.00 · 1061 · 9.63 | 1.00 · 1081 · 6.09 | 1.00 · 909 · 8.90 |

**Answer to the key question — does paying for a tier above Opus 4.8 buy any measurable reliability where 4.8 is already 1.00?** No. On these eight cells (4 languages × 2 tasks) Fable 5 matches Opus-4.8's perfect pass-proportion exactly — 12/12 on each task — at roughly **2× the dollar cost** and, on the hard task, with **no speed benefit** (it was in fact the slowest of the three: ~1039 s vs ~947 s regular and ~887 s fast). Fable 5 shares fast mode's $10/$50 rate but, unlike fast mode, doesn't even buy latency here. On work where 4.8 already gets it completely right every time, the more expensive tier is pure overhead. (A harder task — one where 4.8 itself dips below 1.00 — would be needed to expose any reliability headroom Fable 5 might have; these two tasks don't reach that regime.)

---

## Rerun outcomes (experiments 1, 2, 5)

The overnight pipeline attempted to re-run tooling-broken cells in experiments 1, 2, and 5 (clojure `lein`, exp-2 go, exp-1 python, plus java/rust) under the fixed harness. **The rerun harness itself failed:** every re-run produced an *instant* failure — ~1–4 s wall-clock, **$0 cost, all-zero scores** — i.e. the model was never actually launched. The rerun log records the result plainly: **"0 completed, 36 failed"** for experiment-5.

Worse, the broken rerun *overwrote previously-good runs* in the live DBs:

| Experiment | Before rerun | After rerun | Net effect |
|---|---|---|---|
| experiment-1 | 67 completed / 6 failed | 64 completed / 14 failed | **lost 3 completed, +8 failed** (python opus/sonnet cells corrupted) |
| experiment-2 | 22 completed / 2 failed | 22 completed / 2 failed | unchanged |
| experiment-5 | 36 completed / 36 failed | 18 completed / 54 failed | **lost 18 completed** (all `tooling=none` cells corrupted) |

**Action taken:** the corrupted `retort.db` files for experiment-1 and experiment-5 were **restored from their `.pre-rerun.bak` snapshots** (integrity-checked OK). experiment-2 was untouched by the rerun and left as-is. **Zero previously-failed cells were recovered** by the rerun — it recovered nothing and damaged good data, so it was rolled back in full.

### Genuine vs. tooling, judged from the (restored) pre-rerun artifacts

With the rerun a no-op, the failed-cell landscape is exactly the pre-rerun one. Classifying by failure signature (instant ~1 s, $0 = harness/tooling artifact; multi-minute run that then fails the gate = genuine):

- **experiment-5 — `beads` tooling on clojure / java / rust (both opus-4.7 and opus-4.8): tooling artifact.** Each is 0/3 with **~1.3–1.5 s instant failures** — the `beads` runner never launched the build for `lein` / `gradle` / `cargo`. The *matching `tooling=none` cells for the same languages and models all passed 3/3* (clojure/go/java/python/rust/typescript ≈ 860–1430 s real runs, `requirement_coverage = 1.0`). These are not model failures; they remain **unrecovered** (the rerun meant to fix them was broken). `beads` was already dropped from later experiments for exactly this instability.
- **experiment-2 — go/sonnet/beads and java/sonnet/none (n=1 each): tooling artifact.** Both are instant ~1.2 s, $0 failures with no error text — harness, not model. Still unrecovered.
- **experiment-1 — clojure opus/sonnet failures: genuine.** These ran **240–318 s** before failing the spec gate — the model genuinely produced a non-conforming Clojure implementation on one of three replicates. Each affected cell still passed **2/3**, so the per-cell pass-proportion (0.66) already reflects real model variance. The rust/typescript sonnet single-replicate failures have no recorded duration and are ambiguous, but each cell likewise passed ≥2/3.

**Bottom line:** no cell changed state as a result of the reruns. The README/per-language tables are unaffected by the rerun attempt; the only correction folded in here is the restoration of the two DBs the broken rerun had corrupted.

---

*Generated 2026-06-10. Fable 5 runs: `experiment-10/{bookshop,brazil}/retort.db`. Baselines: opus-4.8 = exp-6 (REST) / exp-5 (Brazil), `tooling=none`; opus-4.8-fast = exp-7. The overnight re-aggregate into `master.db`/`master.csv` failed (`--csv` arg error in the pipeline), so `master.csv` does not yet include Fable 5 or the restored DBs; the numbers above come directly from the per-experiment DBs.*
