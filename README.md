# Retort

**Platform Evolution Engine** — Distill the best from the combinatorial mess.

Retort applies statistical Design of Experiments (DoE) to systematically evaluate AI-assisted development tooling stacks. It generates fractional factorial designs across languages, coding agents, and frameworks, executes experiments in isolated playpens, scores the results, and promotes or retires stacks based on measured confidence.

## Status: 1.0 Beta

> Retort 1.0 beta is **feature-complete for single-agent `claude-code` experiments** with the `LocalRunner`. The CLI surface, scoring metrics, and storage schema are stable. This is the version we used to run **six experiments — 180+ completed runs and ~$200 in API costs** — comparing languages, two tasks, and three Claude Opus generations (4.6 / 4.7 / 4.8). A live `retort monitor` dashboard and an extend-only adaptive timeout were added during this work.
>
> **What works:** `LocalRunner`, all 8 built-in scorers, fractional-factorial design generation, ANOVA + effects reporting, SQLite storage, resumable sharded runs, parallel bulk evaluation, auto-evaluation skills pipeline, `cost_limit_usd` budget enforcement, and the full experiment lifecycle (screening → trial → production).
>
> **What is not yet implemented:** `DockerRunner` (skeleton only — `LocalRunner` is the supported path), agents other than `claude-code` (unsupported agents now raise an error at startup), the `intake`/`scheduler` paths.
>
> **Scoring gate:** A run where tests don't execute scores **0 across all metrics** — a Starlette-incompatible Python run that writes perfect code still fails if pytest can't import. `test_coverage == 0` vetoes the entire `ScoreVector`. The `findings` scorer reads `assessment.json` produced by the `evaluate-run` + `file-run-issues` skill pipeline and applies a weighted penalty for critical/high/medium/low findings.

## Experiment 1 Results

📊 **[Browse the live web report →](https://rawcdn.githack.com/adrianco/retort/main/experiment-1/reports/web/index.html)** (sortable leaderboard with per-stack drill-downs, token/cost data, and links to per-run code reviews)

Full data is also in [`experiment-1/reports/`](experiment-1/reports/) — ANOVA, per-stack maturity, full CSV, and the same static-HTML web report. See [`experiment-1/reports/comparison.md`](experiment-1/reports/comparison.md) for the complete per-run analysis.

**Setup:** 6 languages (python, typescript, go, rust, java, clojure) × 2 models (opus, sonnet) × 2 tooling (none, beads) × 2–3 replicates = 73 runs against the bundled `rest-api-crud` task (CRUD book collection API). **Final tally: 67 of 73 runs completed, 6 failed. Total cost ≈ $25, ≈ 25.8M tokens.**

**Evaluation scores** (from `retort evaluate` + `evaluate-run` skill): `PenScore` = 1.0 minus weighted findings penalty (critical×0.25, high×0.10, medium×0.03, low×0.01); `ReqCov` = fraction of TASK.md requirements implemented. Runs where tests didn't execute score 0.

**Multiplicative ANOVA** (default: log10 transform, since cost/tokens/duration scale by ratios not constants):

| Response | Significant factors |
|---|---|
| `code_quality` | language only (p < 1e-18) |
| `_tokens` | language + model + tooling |
| `_cost_usd` | language + model + tooling |
| `_duration_seconds` | language + model + tooling |

Switching from additive to multiplicative ANOVA surfaced model + tooling effects on the cost-like metrics that the additive model treated as noise. See [`reports/anova.txt`](experiment-1/reports/anova.txt).

**Top stacks by maturity:** **Java sweeps quality 1.000** in all four model/tooling combinations. Go's `sonnet/beads` ties at quality 1.000 too. Generate the full maturity report with `retort maturity --db experiment-1/retort.db`.

### Per-stack means (live data)

Sortable + drill-downable in the [web report](https://rawcdn.githack.com/adrianco/retort/main/experiment-1/reports/web/index.html). `PenScore` and `ReqCov` are from the `evaluate-run` bulk evaluation. Bold = perfect penalty score.

| Language | Model | Tooling | n | Quality (mean) | Tokens (mean) | Cost (mean) | PenScore | ReqCov |
|---|---|---|---|---|---|---|---|---|
| clojure | opus | beads | 2/3 | 0.556 | 723,724 | $0.762 | **1.000** | 1.000 |
| clojure | opus | none | 3/3 | 0.833 | 409,366 | $0.579 | **1.000** | 1.000 |
| clojure | sonnet | beads | 3/3 | 0.556 | 722,939 | $0.520 | 0.830 | 0.939 |
| clojure | sonnet | none | 3/3 | 0.556 | 665,636 | $0.575 | 0.967 | 0.972 |
| go | opus | beads | 3/3 | 0.985 | 346,215 | $0.491 | **1.000** | 1.000 |
| go | opus | none | 3/3 | 0.963 | 230,498 | $0.361 | **1.000** | 1.000 |
| go | sonnet | beads | 3/3 | **1.000** | 476,955 | $0.311 | 0.995 | 0.500 |
| go | sonnet | none | 3/3 | 0.956 | 435,373 | $0.303 | **1.000** | 1.000 |
| java | opus | beads | 3/3 | **1.000** | 325,112 | $0.552 | **1.000** | 1.000 |
| java | opus | none | 3/3 | **1.000** | 217,162 | $0.436 | **1.000** | — |
| java | sonnet | beads | 3/3 | **1.000** | 611,395 | $0.365 | **1.000** | 1.000 |
| java | sonnet | none | 3/3 | **1.000** | 494,115 | $0.326 | **1.000** | 1.000 |
| python | opus | beads | 3/3 | 0.672 | 280,359 | $0.373 | **1.000** | 1.000 |
| python | opus | none | 3/3 | 0.582 | 91,698 | $0.203 | 0.500 | 0.727 |
| python | sonnet | beads | 3/3 | 0.474 | 436,753 | $0.262 | 0.400 | 0.800 |
| python | sonnet | none | 3/3 | 0.430 | 332,390 | $0.226 | 0.995 | 1.000 |
| rust | opus | beads | 3/3 | 0.833 | 355,099 | $0.481 | **1.000** | 1.000 |
| rust | opus | none | 3/3 | 0.833 | 150,702 | $0.331 | **1.000** | 0.500 |
| rust | sonnet | beads | 3/3 | 0.556 | 643,793 | $0.414 | **1.000** | 1.000 |
| rust | sonnet | none | 3/3 | 0.833 | 395,257 | $0.355 | **1.000** | 1.000 |
| typescript | opus | beads | 3/3 | 0.733 | 454,220 | $0.512 | **1.000** | 1.000 |
| typescript | opus | none | 3/3 | 0.733 | 168,703 | $0.319 | **1.000** | 1.000 |
| typescript | sonnet | beads | 3/3 | 0.489 | 637,682 | $0.381 | 0.900 | 0.950 |
| typescript | sonnet | none | 3/3 | 0.489 | 835,319 | $0.531 | 0.500 | 0.591 |

**Headlines:**
- **Java, Go, Rust, and Clojure/opus consistently hit PenScore 1.000** on this task — no findings above threshold.
- **Python is the outlier.** `python/opus/none` and `python/sonnet/beads` scored 0.50 and 0.40 due to a Starlette 1.0 compatibility break that prevented tests from executing (which zeroes all scores under the new test-gate rule). Other Python cells pass cleanly.
- **Requirement coverage diverges from penalty score.** `go/sonnet/beads` has PenScore 0.995 but ReqCov 0.500 — the code is high quality but only implements half the spec. The old `code_quality` scorer missed this.
- **Beads helps only for Go.** Pattern consistent with experiment-1 ANOVA findings.

## Experiment 2 Results — brazil-bench (cross-task)

📊 **[Web report →](https://rawcdn.githack.com/adrianco/retort/main/experiment-2/reports/web/index.html)**

Full per-run analysis: [`experiment-2/reports/comparison.md`](experiment-2/reports/comparison.md).

A second experiment run against [`brazil-bench/benchmark-template`](https://github.com/brazil-bench/benchmark-template) — a much harder task: MCP server, CSV ingest of Kaggle data, BDD tests with 16 canonical requirements. **24 completed runs (24 cells), 1 replicate each, screening pass. Total cost $29.85, 33.6M tokens (avg $1.24/run).**

**Single-task ANOVA on `code_quality`:** only language significant (consistent with experiment-1).

**Cross-task ANOVA** (91 rows = experiment-1's 67 + experiment-2's 24, `task` as a factor):

| Response | Significant factors |
|---|---|
| `code_quality` | language |
| `_tokens` | language + model + tooling + **task** + language:tooling + **language:task** + model:tooling + **model:task** |
| `_cost_usd` | similar + model:tooling |
| `_duration_seconds` | every main effect + 5 interactions (incl. **model:task**, **tooling:task**) |

**The `model:task` interaction is the headline finding.** Opus vs sonnet behaves *differently* on hard (brazil-bench) vs easy (rest-api-crud) tasks. The simple "best stack on rest-api-crud is best everywhere" assumption from experiment-1 doesn't fully generalize for the resource-cost dimensions.

### Experiment-2 evaluation scores (brazil-bench)

`PenScore` and `ReqCov` from `evaluate-run` bulk evaluation. Brazil-bench is a harder task (MCP server + CSV ingest + BDD tests) so scores spread more widely.

| Language | Model | Tooling | Quality | PenScore | ReqCov | Notes |
|---|---|---|---|---|---|---|
| clojure | opus | beads | 0.833 | **1.000** | — | |
| clojure | opus | none | 0.833 | **1.000** | — | |
| clojure | sonnet | beads | 0.833 | **1.000** | 0.889 | |
| clojure | sonnet | none | 0.833 | **1.000** | — | |
| go | opus | beads | 1.000 | **1.000** | 1.000 | |
| go | opus | none | 1.000 | 0.620 | 0.667 | |
| go | sonnet | beads | 1.000 | 0.650 | 0.000 | 1 critical — BDD scaffold with no data |
| go | sonnet | none | 1.000 | 0.900 | 0.500 | |
| java | opus | beads | 1.000 | 0.940 | 0.900 | |
| java | opus | none | 1.000 | **1.000** | — | |
| java | sonnet | beads | 1.000 | **1.000** | 1.000 | |
| java | sonnet | none | 1.000 | 0.000 | 0.067 | **11 critical** — catastrophic failure |
| python | opus | beads | 0.667 | **1.000** | — | |
| python | opus | none | 0.667 | **1.000** | 1.000 | |
| python | sonnet | beads | 0.667 | **1.000** | — | |
| python | sonnet | none | 0.667 | **1.000** | 0.917 | |
| rust | opus | beads | 0.833 | 0.450 | 0.143 | 1 critical |
| rust | opus | none | 0.833 | 0.750 | — | 1 critical |
| rust | sonnet | beads | 0.833 | 0.400 | 0.143 | |
| rust | sonnet | none | 0.833 | 0.990 | 1.000 | |
| typescript | opus | beads | 0.000 | **1.000** | — | |
| typescript | opus | none | 0.000 | **1.000** | 1.000 | |
| typescript | sonnet | beads | 0.733 | — | — | |
| typescript | sonnet | none | 0.733 | **1.000** | 1.000 | |

**Headlines for brazil-bench:**
- **Python sweeps clean** — all four cells hit PenScore 1.000, reversing the experiment-1 pattern (Starlette issue is task-specific, not language-specific).
- **Java/sonnet/none catastrophically fails** (11 criticals, PenScore 0.000) — a single cell failure, not a model trend; the same model/tooling is fine in all other combinations.
- **Rust struggles on the harder task** — all four cells below 1.000, consistent with Rust's complexity wall on multi-component tasks.
- **`model:task` interaction confirmed by evaluation scores**: opus outperforms sonnet on brazil-bench for Go and Java; sonnet leads on rust/none.

**Pareto frontier across both tasks** (`retort report pareto --data combined.csv --metric code_quality --metric -_cost_usd`):

| | |
|---|---|
| **Rank 0 (Pareto-optimal)** | `go / sonnet / beads` — quality 1.000, cost $0.311 |
| Rank 1 | `java / sonnet / none` — quality 1.000, cost $0.326 |
| Rank 2 | `go / sonnet / none`, `java / opus / none`, `python / opus / none`, `rust / opus / none` |

Every other stack is dominated. **`go / sonnet / beads` is the only stack that no other stack beats on both quality AND cost simultaneously.**

## Experiment 3 Results — Model Version Comparison (claude-opus-4-6 vs claude-opus-4-7)

📊 **[Full report →](experiment-3/reports/comparison.md)**

A quarter-fraction screening experiment on the same brazil-bench task, designed to estimate the effect of upgrading from `claude-opus-4-6` to `claude-opus-4-7`. **6 cells × 2 replicates = 12 run-slots, executed across 4 parallel shards (May 2026).**

**Model version provenance:** Experiment-2 used model alias `"opus"` which resolved to `claude-opus-4-6` via the Claude CLI (claude-opus-4-7 did not yet exist in April 2026). Experiment-3 uses explicit versioned model IDs: `claude-opus-4-6` and `claude-opus-4-7`.

**Design (Resolution III quarter-fraction):** Each language is assigned to one model to maximize coverage; model main effect is aliased with the compiled-vs-scripted language contrast.

**Total: 14 runs, $54.94, 52.2M tokens** (avg $3.92/run — 3.3× higher than experiment-2's $1.24/run avg)

| Language | Model | Tooling | test_coverage | code_quality | avg duration | avg tokens | avg cost |
|---|---|---|---|---|---|---|---|
| go | claude-opus-4-7 | none | **0.813** | **1.000** | 23.1m | 7,612,020 | $8.13 |
| java | claude-opus-4-6 | none | 1.000 | **1.000** | 12.9m | 2,472,358 | $2.87 |
| rust | claude-opus-4-7 | beads | 1.000 | 0.833 | 25.0m | 7,573,138 | $7.34 |
| python | claude-opus-4-6 | none | 0.897 | 0.667 | 5.2m | 750,075 | $0.98 |
| typescript | claude-opus-4-6 | beads | 1.000 | 0.733 | 6.7m | 1,545,433 | $1.56 |
| clojure | claude-opus-4-7 | beads | 1.000 | 0.833 | 20.9m | 5,007,051 | $5.30 |

**Headlines:**
- **Go + claude-opus-4-7 achieves 81% test coverage vs 42% for claude-opus-4-6 on the same task** — the clearest model-version signal in the dataset. Code quality is identical (1.000 = zero high-severity findings). The 5× longer runtime in experiment-3 correlates with more thorough test writing.
- **Java and Rust hit 100% test coverage regardless of model version.** Java scores code_quality 1.000 in both experiments; consistent with experiment-2.
- **TypeScript + beads tooling enables test frameworks.** Experiment-2 typescript/opus scores 0.0 (no test framework generated); experiment-3 typescript/claude-opus-4-6/beads scores 1.000 — the `model:tooling` interaction matters more than model version alone.
- **Runs take 2–9× longer than experiment-2 — and it's the model, not the timeout.** The timeout only ever *fails* a run that exceeds it; a run that completes does so in its natural time regardless of the budget. The longer durations are genuine model behavior: `claude-opus-4-7`/`4-8` spend far more time per run on brazil-bench than `4-6`/`sonnet` did (see the four-model duration ladder under [Time taken](#time-taken)). The adaptive timeout (`_estimate_run_timeout`) is extend-only — it just keeps a legitimately slow run from being killed.
- **Same model (claude-opus-4-6), same task, same quality.** Java and Python show identical `code_quality` across the April→May gap, suggesting model quality is stable.

**Scorer fixes (applied in this experiment, rescored across all experiments):** Java MVN `-q` flag silenced surefire output (removed); Clojure test alias was wrong (`-X:test` → `-M:test`); Rust lacked a coverage-command path (added tests-only fallback); TypeScript vitest invoked via broken `.bin/` wrapper (switched to direct `node` invocation with test-pass-rate fallback).

## Experiment 4 Results — Adding claude-opus-4-8 (three-way)

📊 **[Full report →](experiment-4/reports/comparison.md)**

A quarter-fraction augmentation of experiment 3 that adds the third Opus generation, `claude-opus-4-8`, on the same brazil-bench task — 3 new cells × 2 replicates. **6 runs, $32.15, 33.1M tokens.**

The headline is the **controlled Go test-coverage trajectory** (go/none, the one cell with a point on all three versions):

| Version | code_quality | **test_coverage** |
|---|---|---|
| claude-opus-4-6 (exp-2) | 1.000 | 0.42 |
| claude-opus-4-7 (exp-3) | 1.000 | **0.81** |
| claude-opus-4-8 (exp-4) | 1.000 | 0.44 |

**Headlines:**
- **4.7's Go coverage spike was a peak, not a trend.** 4.8 reverts to ~4.6-level coverage (0.44), with *less* runtime — so it is a behavioral difference, not a timeout artifact. Code quality stays a flat 1.000 throughout. The "newer model writes more tests" effect was specific to 4.7.
- **Python code quality improved at 4.8** for the first time across the program: 0.667 (4.6) → **0.833** (4.8), with PenScore 1.0 / ReqCov 1.0.
- **4.8 is cheaper and faster than 4.7 on the matched Go cell** (−28% cost, −24% time) while matching 4.6 coverage.
- **Clojure/4-8 flagged** for manual review (perfect mechanical scores but evaluator ReqCov 0.0 — a grep-based matcher artifact to confirm).

## Experiment 5 Results — 4.7 vs 4.8 full factorial (brazil-bench) — *in progress*

A **full** 24-cell factorial (6 language × {claude-opus-4-7, claude-opus-4-8} × {none, beads} × 3 replicates = 72 runs) on brazil-bench — the de-aliased confirmation of experiment 4's model-version findings (a full factorial removes the Resolution III aliasing). Run single-shard and resumed across usage-limit windows; **results pending completion**. (This experiment is the reason `retort monitor` reports failed runs as *pending retry* rather than done — see [CLI Commands](#cli-commands).)

**Early duration signal (partial):** on this harder task, `claude-opus-4-8` runs *materially longer* than `4-7` on the cells finished so far — python/none **+73%** (12.7m → 22.1m), typescript/beads **+73%**, typescript/none **+33%**, python/beads +2%. This is the **opposite** of the near-flat bookshop result: if it holds, the model×task interaction extends to wall-clock — 4-8 spends more time on hard tasks. (Final numbers pending completion.)

## Experiment 6 Results — 4.7 vs 4.8 full factorial (bookshop / rest-api-crud)

📊 **[Data →](experiment-6/results.csv)**

The same full 4.7×4.8 factorial as experiment 5, but on the lighter `rest-api-crud` (books CRUD API) task — a **cross-task** confirmation. **71/72 runs completed (1 java/4-8/none rep timed out at 45m), all 24 cells valid. $64.01, 50.2M tokens.**

**`claude-opus-4-7` and `claude-opus-4-8` are a statistical dead heat**, and the language hierarchy is identical across both versions:

| | code_quality | test_coverage | cost/run |
|---|---|---|---|
| claude-opus-4-7 | 0.861 | 0.929 | $0.84 |
| claude-opus-4-8 | 0.860 | 0.941 | $0.96 |

| Language | 4.7 cq | 4.8 cq | 4.7 cov | 4.8 cov |
|---|---|---|---|---|
| java | 1.000 | 1.000 | 1.00 | 1.00 |
| go | 1.000 | 1.000 | 0.68 | 0.70 |
| rust | 0.833 | 0.833 | 1.00 | 1.00 |
| clojure | 0.833 | 0.833 | 1.00 | 1.00 |
| typescript | 0.733 | 0.733 | 0.89 | 0.97 |
| python | 0.766 | 0.781 | 1.00 | 0.99 |

**Time taken (per-run wall-clock, minutes):** language-dominated, and the 4.7-vs-4.8 *median* is flat — but 4.8 has a heavy right tail on the JVM languages.

| Language | median | mean | max | 4.7 mean | 4.8 mean |
|---|---|---|---|---|---|
| python | 1.8 | 1.9 | 3.5 | 1.7 | 2.0 |
| typescript | 2.4 | 2.5 | 3.2 | 2.6 | 2.4 |
| go | 2.6 | 2.6 | 3.2 | 2.8 | 2.5 |
| rust | 2.8 | 3.0 | 4.5 | 2.9 | 3.1 |
| java | 3.2 | 4.5 | **17.2** | 3.0 | 6.2 |
| clojure | 4.1 | 6.0 | **26.8** | 3.5 | 8.5 |

Overall median 2.8m (4.7) vs 2.7m (4.8) — flat. The mean diverges (+47%) only because 4.8 produced single runs of 17m (java) and 27m (clojure) where 4.7 never exceeded ~4.5m — plus the one 45-min `java/4-8/none` timeout. **ANOVA on log10(duration):** language `p < 1e-6` (dominant), tooling `p = 0.0096` (beads adds time), model `p = 0.061` (marginal — the tail). Duration tracks cost and tokens closely.

**Headlines:**
- **Model version is a second-order effect.** Per-language code_quality is identical between 4.7 and 4.8; 4.8 costs slightly more. The language ladder (java/go = 1.0 > rust/clojure = 0.83 > python ≈ ts) is unchanged by the model bump — consistent with experiments 1–3.
- **Cross-task generalization:** the strong model-version movements seen on brazil-bench (Go coverage, Python quality) do **not** appear on this simpler task — the model effect is task-dependent.

## Experiment Summary

| Experiment | Task | Runs | Cost | Tokens | Key Finding |
|---|---|---|---|---|---|
| 1 | rest-api-crud | 67/73 | $25.07 | 25.8M | Language dominates: Java=1.0, Go=0.98, Rust=0.83 |
| 2 | brazil-bench | 24/24 | $29.85 | 33.6M | model×task interaction; TypeScript model-sensitive |
| 3 | brazil-bench (4.6 vs 4.7) | 14/14 | $54.94 | 52.2M | Opus-4.7 adds 2× test coverage on Go |
| 4 | brazil-bench (+4.8, ¼-frac) | 6/6 | $32.15 | 33.1M | 4.7's Go-coverage spike doesn't hold at 4.8; Python cq rises |
| 5 | brazil-bench (4.7×4.8 full) | *in progress* | — | — | De-aliased 4.7-vs-4.8 confirmation (resuming across limit windows) |
| 6 | rest-api-crud (4.7×4.8 full) | 71/72 | $64.01 | 50.2M | 4.7 ≈ 4.8 (cq 0.861 vs 0.860); language still dominates |
| **Total (excl. exp-5)** | | **182/189** | **$206.02** | **194.9M** | Language dominates; model version is a second-order, task-dependent effect |

### All four models head-to-head

The CRUD/bookshop task was run with **sonnet-4.5 and opus-4.6** (experiment 1) and **opus-4.7 and opus-4.8** (experiment 6) — the same task across all four models, so they can be compared directly (caveat: exp-1 and exp-6 ran on different dates; both were rescored with the fixed scorers):

| Model | n | code_quality | duration (median) | cost/run |
|---|---|---|---|---|
| claude-sonnet-4-5 | 32 | 0.752 | 2.9m | $0.37 |
| claude-opus-4-6 | 35 | 0.833 | **2.3m** | $0.45 |
| claude-opus-4-7 | 36 | **0.861** | 2.8m | $0.84 |
| claude-opus-4-8 | 35 | 0.860 | 2.7m | $0.96 |

- **Quality:** opus > sonnet (+0.08), and it rises 4-6 → 4-7 (+0.03) then **plateaus** — 4-8 matches 4-7.
- **Speed:** `opus-4-6` is the **fastest** model here; each newer opus is a little slower, and 4-8 adds a heavy right tail (java/clojure runs of 17–27m, and a 45-min timeout).
- **Cost:** roughly **doubles** from sonnet/4-6 (~$0.40) to 4-7/4-8 (~$0.90) — newer opus is pricier per run, not cheaper.
- **Net:** on this task `opus-4-7` is the value sweet spot (top quality, moderate cost); `4-8` costs ~14% more and runs with a heavier tail for no quality gain; `4-6` is the cheap-and-fast pick at slightly lower quality; `sonnet-4-5` is cheapest but lowest quality.

**On the harder brazil-bench task** the same four models ran across experiments 2–5, and per-run **duration climbs steeply** with each newer Opus generation — the opposite of the near-flat bookshop result:

| Model | source | duration (median) | mean |
|---|---|---|---|
| claude-opus-4-6 | exp-2 | 4.0m | 4.2m |
| claude-sonnet-4-5 | exp-2 | 7.1m | 7.2m |
| claude-opus-4-7 | exp-5 (matched cells) | 11.0m | 11.4m |
| claude-opus-4-8 | exp-5 (matched cells) | 15.5m | 16.5m |

Each generation runs roughly **1.5–2× longer** than the last (`opus-4-6` ≈ 4m → `4-7` ≈ 11m → `4-8` ≈ 16m), with `sonnet-4-5` (~7m) between 4-6 and 4-7. The cleanest contrasts are within a single experiment: in exp-2, `sonnet-4-5` ran **+70%** vs `opus-4-6`; in exp-5's matched cells, `opus-4-8` ran **+44%** vs `4-7`. (Durations are comparable across experiments — the timeout only fails a run that exceeds it, it does not change how long a completed run takes. The opus 4-6 → 4-7 → 4-8 quality/coverage trajectory on brazil-bench is in experiments 3–5 above.)

### Time taken

Wall-clock per run is driven first by **task**, then **language**, then (weakly, and task-dependently) **model version** — the same ordering as cost and tokens, with which duration is tightly correlated.

- **Task dominates.** The same languages run **~5–9× longer** on brazil-bench (MCP server, CSV ingest, BDD tests) than on the bookshop CRUD task: Go ≈ 2.6m vs ≈ 23m, Python ≈ 1.9m vs ≈ 13m, Clojure ≈ 4m vs ≈ 21m. Pick the task budget accordingly.
- **Language is the next factor, and the ranking is stable.** Scripted languages (python, typescript) are fastest; JVM/compiled (java, clojure, rust, go) are slower, and **java + clojure carry the longest right tails** (occasional runs many× the median).
- **Model effect on duration is small on easy tasks but large on hard ones — and newer is slower.** On bookshop the four models are within ~0.6m of each other (`opus-4-6` quickest at 2.3m; `4-7 ≈ 4-8`). On brazil-bench the model effect explodes: each newer Opus generation runs **~1.5–2× longer** (`4-6` ≈ 4m → `4-7` ≈ 11m → `4-8` ≈ 16m; matched-cell `4-8` is **+44%** vs `4-7`), plus a heavier tail of runaway runs that occasionally exceed the timeout and fail. This `model:task` interaction on duration mirrors the one on quality. (The timeout never lengthens a run — it only fails one that overruns; retort's adaptive timeout is **extend-only** so a legitimately slow run isn't killed.)

The practical implication: budget by **task first** (a hard task is a 5–9× multiplier), watch the **java/clojure tails**, and don't expect a newer model to be faster or cheaper — newer Opus generations cost ~2× more than `4-6`/`sonnet` and, on hard tasks, run **1.5–2× longer** for the same quality.

## Installation

### The easy way: ask Claude Code

Retort has a few environment gotchas (it needs Python ≥3.11, and `OApackage` is a C++ extension that must be built with `cmake`). The fastest install is to let Claude Code sort them out — point it at a directory and ask:

```text
$ cd Documents/GitHub
$ claude
> clone and install https://github.com/adrianco/retort here

⏺ Done. Retort is cloned and installed, and all tests pass.

  Setup steps I had to take (the system default python3 is 3.9.6, but retort needs ≥3.11):
  - Installed cmake via Homebrew — required to build OApackage (a C++ extension
    with no prebuilt wheel for this platform).
  - Created a virtualenv with Homebrew's Python 3.12 at retort/.venv.
  - Ran pip install -e ".[dev,test]" — built retort and oapackage from source.

  Verification:
  - retort --help loads and lists all commands.
  - Test suite: 573 passed.
```

It will also offer to install the per-language toolchains and the `claude` / `bd` CLIs when you set up your first experiment. Prefer to do it by hand? Read on.

### Prerequisites

`pip install` only fetches the Python deps. To actually run experiments you also need:

| Requirement | Why | Install |
|---|---|---|
| **Python 3.11+** | Runtime | https://www.python.org/downloads/ |
| **C/C++ toolchain + cmake** | `OApackage` (orthogonal arrays) is a C++ extension; no manylinux wheel on every platform | `apt install build-essential cmake` (Debian/Ubuntu) / `xcode-select --install` (macOS) |
| **`claude` CLI, authenticated** | The only currently-implemented agent runner shells out to `claude -p ...` | https://docs.claude.com/claude-code · run `claude` once to log in |
| **`bd` (beads) CLI** | Required only if any factor uses `tooling: beads` (the bundled examples do). The agent runs `bd init`/`bd create` inside its playpen | https://github.com/steveyegge/beads |
| **Per-language toolchains** | The scorer builds and tests the generated code. Install the toolchain for every language you list as a factor level. | `python` (already), `node` ≥ 20 + `npm` for typescript, `go` ≥ 1.22, `rustup` for rust |
| **Docker** *(optional, future)* | `DockerRunner` is a skeleton; `LocalRunner` is the supported path today. Only install if you plan to develop the Docker path. | https://docs.docker.com/get-docker/ |

### Install retort

```bash
git clone https://github.com/adrianco/retort.git
cd retort
pip install -e ".[dev,test]"
```

### Devcontainer / Codespaces

`.devcontainer/` provisions Python 3.12 + the C++ toolchain + Node + Go + Rust + the `claude` and `bd` CLIs via `post-create.sh`. Open the repo in GitHub Codespaces or VS Code "Dev Containers: Reopen in Container" and the prereqs are handled automatically. You'll still need to authenticate `claude` interactively the first time.

### Verify

```bash
retort --help                # CLI loads → Python deps OK
claude --version             # Claude CLI present
bd --version                 # Beads present (only needed for tooling=beads)
```

## Quick Start

### Drive it with Claude Code (recommended)

You don't have to hand-write `workspace.yaml` or do the fractional-factorial math. Open `claude` in the repo, **describe the experiment you want in plain language**, and let it design the matrix, check prerequisites, estimate cost, confirm the decisions that actually matter, and run it. Every experiment in this repo was built this way:

```text
> I want to run a quarter fraction experiment 4 that extends experiment 3,
  which compared opus 4.6 and 4.7, to compare opus 4.8 as well

⏺ Two findings that shape the design:
  - claude CLI is present (v2.1.156) — good.
  - bd (beads) is NOT installed. Experiment-3 used tooling: beads in several
    cells … so any beads cell in experiment-4 needs beads installed first.

  Experiment-3 is a 6-cell Resolution III quarter-fraction of a 24-cell
  factorial (6 language × 2 model × 2 tooling), 2 replicates. Adding
  claude-opus-4-8 makes model a 3-level factor → the full factorial becomes
  3 × 6 × 2 = 36 cells, and a quarter-fraction is 9 cells.

  Before I build and run this (real API spend — exp-3 cost ~$55 — and hours
  of wall-clock), confirm a few design decisions:

⏺ User answered Claude's questions:
  · How should experiment-4 be structured?  → Augment exp-3 (reuse + add 4.8)
  · bd (beads) isn't installed. Tooling?     → Install bd, keep beads cells
  · Execute the runs, or set up and stop?    → Set up, then run it
```

Claude then writes `experiment-4/workspace.yaml` + `design.csv`, installs the language toolchains it needs, runs the cells, and reports results — watch live with `retort monitor experiment-4`. It also handles the messy parts in practice: resuming cleanly across API usage-limit windows, retrying failures, and flagging cost before it spends.

### Or drive the CLI directly

```bash
# Initialize a workspace
retort init my-eval
cd my-eval

# Edit workspace.yaml to define your factors, responses, and tasks.
# Add design.fraction: 0.25 to run a quarter-fraction instead of the full design.
# Then generate a screening design matrix (optional — run does this automatically)
retort design generate --phase screening --config workspace.yaml -o design.csv

# Execute experiment runs (uses design.fraction from workspace.yaml automatically)
retort run --phase screening --config workspace.yaml

# Watch live progress (completed/remaining, cost, ETA, failures)
retort monitor my-eval --watch

# Predict unrun cells from a fractional run
retort analyze --data results.csv -r code_quality -f language -f model -f tooling --predict

# Or pass a hand-edited CSV to run any arbitrary subset
retort run --phase screening --config workspace.yaml --design design.csv

# Compute main effects and interactions
retort report effects --db retort.db --matrix-id 1 --metric code_quality

# Evaluate a promotion gate
retort promote my-stack --from screening --to trial \
    --evidence '{"p_value": 0.05}' --config workspace.yaml
```

## Running at scale (parallel shards)

Retort runs standalone — `pip install` + the `claude` CLI is enough to drive everything above, including parallel execution. `retort run --shard N/M` runs only the cells a deterministic hash assigns to shard N of M; all shards share one `retort.db` with per-run commits, so two shards never pick the same cell and a crash loses at most one run.

The simplest way to run a multi-shard experiment is to **ask Claude Code to do it** — it launches the workers, watches them with `retort monitor`, stops when it sees an API usage limit, and `--resume`s after each reset to bank progress. Or start the shards yourself with plain bash:

```bash
for s in 0 1 2 3; do
    nohup retort run --phase screening --config experiment-2/workspace.yaml \
        --resume --shard $s/4 > experiment-2/shard-$s.log 2>&1 &
done
wait
```

Watch progress (and catch usage limits) in another shell:

```bash
retort monitor experiment-2 --watch
```

**Caveat — usage limits are cumulative.** Concurrent shards multiply per-second token usage and hit provider usage limits faster; but the limit tracks *total* consumption, so even a single sequential shard hits it on a large experiment. Start with a low shard count, watch rate-limit headers, and rely on `--resume` (which skips completed cells) to continue across reset windows.

## CLI Commands

| Command | Description |
|---------|-------------|
| `retort init <name>` | Create a new workspace with config template and SQLite database |
| `retort design generate` | Generate a fractional factorial design matrix (screening or characterization) |
| `retort run` | Execute experiment runs: design matrix, playpen provisioning, scoring, storage. Honors `design.fraction` from config; `--design <csv>` overrides with a manually-edited design file |
| `retort promote` | Evaluate promotion gates for stack lifecycle transitions |
| `retort report effects` | Compute and export main effects and interaction effects (text, JSON, CSV) |
| `retort export csv` | Export experiment runs + scores to CSV for `retort analyze` and external tools |
| `retort maturity` | Score each stack's maturity (replicate agreement, completion rate, score level, coverage) and suggest a lifecycle phase |
| `retort report web` | Generate static HTML reports (sortable leaderboard + per-stack drill-downs); respects experiment.visibility for private experiments |
| `retort export merge` | Combine multiple experiment CSVs into one with an experiment-tag column, for cross-experiment ANOVA |
| `retort report pareto` | Identify Pareto-optimal stacks across multiple objectives; minimize cost-like metrics with `-` prefix |
| `retort run --shard N/M` | Run only the slice of cells owned by shard N (of M); deterministic partition for parallel shard workers sharing one retort.db |
| `retort monitor <experiment>` | Live progress dashboard from the run DB: completed/remaining, per-cell coverage, cost/tokens, throughput + ETA, failures. `retort monitor experiment-5` infers the db/config by convention; `--watch` refreshes; `--json` for machines. Failed runs are reported as *pending retry* (they re-run under `--resume --retry-failed`), so a resumed run isn't mistaken for done |
| `retort analyze` | Run ANOVA analysis on experiment data with optional residual diagnostics |
| `retort intake` | Ingest a new candidate (factor level) and generate D-optimal augmentation runs |
| `retort report dashboard` | Show full workspace status dashboard (experiments, lifecycle, budget) |
| `retort plugin list` | List installed retort plugins and their scorer/runner contributions |
| `retort plugin show <name>` | Show details for a specific scorer or runner |

## Configuration

Retort workspaces are configured via `workspace.yaml`:

```yaml
factors:
  language:
    levels: [python, typescript, go]
  agent:
    levels: [claude-code, cursor, copilot]
  framework:
    levels: [fastapi, nextjs, stdlib]

responses:
  - code_quality
  - token_efficiency
  - build_time
  - test_coverage

tasks:
  - source: bundled://rest-api-crud

playpen:
  runner: local            # 'local' is the supported path; 'docker' is a skeleton
  replicates: 3
  timeout_minutes: 30
  cost_limit_usd: 50.00   # optional: abort experiment if accumulated cost exceeds this

design:
  screening_resolution: 3
  significance_threshold: 0.10
  fraction: 0.25            # optional: quarter-fraction (6 cells from 24); omit for full fractional factorial

promotion:
  screening_to_trial: { p_value: 0.10 }
  trial_to_production: { posterior_confidence: 0.80 }
```

When `fraction` is set, `retort run` automatically uses a balanced subset that covers every factor level at least once. After the run, use `retort analyze --predict` to project point estimates and 95% CIs for every unrun cell. You can also override the fraction with a manually-edited CSV via `retort run --design design.csv`.

## Architecture

```
src/retort/
├── cli.py              # Click-based CLI entry point
├── analysis/           # ANOVA, Bayesian updating (conjugate NIG), Pareto frontier, residual diagnostics
├── config/             # Pydantic config schema and YAML loader
├── design/             # Factor registry and fractional factorial generator (pyDOE3)
├── playpen/            # Isolated execution: DockerRunner, task loading, prompt building
├── plugins.py          # Pluggy-based plugin system for custom scorers and runners
├── scoring/            # Score collection with pluggable scorers (code_quality, token_efficiency, build_time)
├── promotion/          # Lifecycle state machine, configurable gates, immutable changelog
├── reporting/          # Effects computation, export (text, JSON, CSV), and status dashboard
├── scheduler/          # Candidate intake, D-optimal augmentation, budget tracking, run queue
└── storage/            # SQLAlchemy models and Alembic migrations (SQLite)
```

### Key Concepts

- **Factors**: Variables under test (language, agent, framework) with discrete levels
- **Design Matrix**: Fractional factorial design that efficiently covers the factor space
- **Playpen**: Isolated execution environment where each experiment run executes
- **Scoring**: Pluggable metrics collected from run artifacts
- **Promotion**: Evidence-based lifecycle transitions (candidate → screening → trial → production → retired)

## Implementation Status

Honest accounting of what is tested end-to-end versus implemented but not exercised.

| Area | Status | Notes |
|------|--------|-------|
| **Design generation** | ✅ Working | Fractional factorial (pyDOE3), mixed-level support, `design.fraction` config, `--design <csv>` override, `DesignMatrix.from_csv()`, `retort analyze --predict` for unrun cells. Full unit test coverage. |
| **LocalRunner + scoring** | ✅ Working | Exercised end-to-end across 180+ runs covering 6 languages. 8 scorers: `code_quality`, `test_coverage`, `test_quality`, `token_efficiency`, `defect_rate`, `maintainability`, `idiomatic`, `findings`. Scoring gate: `test_coverage == 0` vetoes all scores. `evaluate-run` + `file-run-issues` skills auto-invoked after each run. `retort evaluate --workers N` for bulk re-evaluation. |
| **Resume / sharding** | ✅ Working | `--resume` skips recorded `(config, replicate)` pairs; `--retry-failed` retries failures. `--shard N/M` deterministic partition for parallel shard workers. Per-run DB commit = at most one lost run on interrupt. Run artifacts archived to `runs/<cell>/rep<N>/`. Resume cleanly banks progress across API-usage-limit windows. |
| **Monitoring** | ✅ Working | `retort monitor <experiment>` reads the run DB for live progress, per-cell coverage, cost/tokens, session-aware throughput + ETA, and failures. Text / `--json` / `--watch`. Failed runs counted as pending (re-run under `--retry-failed`), not done. |
| **Adaptive timeout** | ✅ Working | `_estimate_run_timeout` sizes each run from historical per-cell timing and is **extend-only** — floored at the configured `timeout_minutes`, so a slow language gets more time but an early, history-poor run is never killed under budget. |
| **Factor system** | ✅ Working | `language`, `model` (with alias table, versioned IDs), `tooling` (beads instructions), `prompt` (named `.md` files in `prompts/`), `org_context`. Any additional factor flows through `stack.extra` automatically. |
| **Budget enforcement** | ✅ Working | `cost_limit_usd` in config is enforced during `retort run` — experiment aborts if accumulated cost exceeds the limit. Error surfaced immediately via `click.ClickException`. |
| **Agent validation** | ✅ Working | Unsupported agents raise a clear error at experiment startup, before any runs execute. Only `claude-code` is implemented. |
| **MLflow sink** | ✅ Implemented | Logs factor levels, scores, and telemetry per run. Enabled by `mlflow:` block in `workspace.yaml`. Not covered by integration tests. |
| **Local inference cost** | ✅ Working | `local_inference_cost` block computes `_cost_usd` from wall-clock duration × (electricity + amortized hardware) for local/offline models. |
| **DockerRunner** | 🟡 Implemented | `provision()` and `execute()` implemented with timeout and teardown. **Not validated end-to-end** — use `runner: local` for now. |
| **Promotion + lifecycle** | 🟡 Code present | State machine, gates, changelog, `retort promote`. Exercised in unit tests; not yet driven by a real promotion decision. |
| **ANOVA / analysis** | 🟡 Lightly exercised | `retort analyze` with additive and multiplicative transforms, residual diagnostics, `--predict` for fractional designs. Verified on real experiment-1/2/3 data for main effects; interaction + Bayesian paths lightly tested. |
| **Reporting** | 🟡 Mostly working | `retort report effects`, `report web`, `report pareto`, `report wardley`, `report aliasing`, `report dashboard` all implemented. `wardley` and `aliasing` verified in code; not exercised against live experiment data. |
| **Scheduler / intake** | 🔴 Stub | `retort intake` (D-optimal augmentation) implemented but untested against real candidates. |
| **Multi-agent** | 🔴 Not implemented | Only `claude-code` is wired in `LocalRunner`. Unsupported agents raise a `click.ClickException` at experiment startup — no silent skipping. |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev,test]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/retort/
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
