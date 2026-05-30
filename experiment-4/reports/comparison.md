# Experiment 4: Three-Way Model Comparison
## claude-opus-4-6 vs claude-opus-4-7 vs claude-opus-4-8 — Quarter-Fraction Augmentation

**Date:** 2026-05-30
**Experiment:** `experiment-4-opus-4-8-three-way`
**Task:** Brazilian Soccer MCP Guide (brazil-bench benchmark)
**Design:** 3 new `claude-opus-4-8` cells (2 replicates each = 6 runs) augmenting the
6-cell experiment-3 quarter-fraction, extending the model factor to three levels
(4-6 / 4-7 / 4-8) of the now 36-cell full factorial (6 language × 3 model × 2 tooling).

---

## 1. What this experiment adds

Experiment-3 compared `claude-opus-4-6` and `claude-opus-4-7` on brazil-bench. This
experiment adds the third level, `claude-opus-4-8`, run on the **same task, same
scorers, same 2 replicates, and same 45-minute timeout** so the new cells are directly
comparable to the carried-over 4-6/4-7 cells from experiment-3 (and the 4-6 cells from
experiment-2).

The three new cells were chosen to span the score range observed in experiment-3 and,
crucially, to **complete the Go test-coverage trajectory** that was the single clearest
signal in experiment-3:

| Cell | Language | Model | Tooling | Why |
|------|----------|-------|---------|-----|
| G | go | claude-opus-4-8 | none | Completes go/none across 4-6 → 4-7 → 4-8 (controlled) |
| H | python | claude-opus-4-8 | beads | python/beads 4-6 → 4-8; tests quality movement |
| I | clojure | claude-opus-4-8 | none | clojure/none 4-6 → 4-8 on a JVM language |

**Note on reuse:** experiment-3's SQLite database is gitignored and was not present in a
fresh clone, so the six experiment-3 cells are carried over from its published results
and run archives rather than re-executed. Only the three new 4-8 cells were run.

---

## 2. Experiment-4 Results (claude-opus-4-8)

### 2.1 Per-cell means (2 replicates each)

| Language | Model | Tooling | code_quality | test_coverage | maintainability | idiomatic | tokens | cost | duration | PenScore | ReqCov |
|----------|-------|---------|--------------|---------------|-----------------|-----------|--------|------|----------|----------|--------|
| go | claude-opus-4-8 | none | **1.000** | 0.444 | 0.586 | 0.675 | 5,986,812 | $5.85 | 17.6m | **1.00** | **1.00** |
| python | claude-opus-4-8 | beads | 0.833 | 0.860 | 0.448 | 0.740 | 5,596,049 | $5.19 | 16.0m | **1.00** | **1.00** |
| clojure | claude-opus-4-8 | none | 0.833 | 1.000 | 0.653 | 0.860 | 4,954,742 | $5.04 | 17.5m | 0.10 | 0.00 |

**Total experiment-4: 6 runs, $32.15, 33.1M tokens** (avg $5.36/run, 5.5M tokens/run).
`defect_rate = 1.000` on all six runs. `PenScore` (1.0 − weighted findings penalty) and
`ReqCov` (fraction of canonical requirements matched) are from the auto-evaluation
(`evaluate-run` skill, model=haiku) that ran after each cell.

### 2.2 Individual run data

| Language | Tooling | Rep | code_quality | test_coverage | maintainability | idiomatic | tokens | cost | duration |
|----------|---------|-----|--------------|---------------|-----------------|-----------|--------|------|----------|
| go | none | 1 | 1.000 | 0.409 | 0.591 | 0.470 | 7,014,305 | $6.57 | 18.9m |
| go | none | 2 | 1.000 | 0.480 | 0.581 | 0.880 | 4,959,319 | $5.12 | 16.2m |
| python | beads | 1 | 0.833 | 0.920 | 0.290 | 0.780 | 6,146,871 | $5.46 | 16.0m |
| python | beads | 2 | 0.833 | 0.800 | 0.611 | 0.700 | 5,045,227 | $4.93 | 15.9m |
| clojure | none | 1 | 0.833 | 1.000 | 0.640 | 0.900 | 5,344,221 | $5.41 | 18.3m |
| clojure | none | 2 | 0.833 | 1.000 | 0.660 | 0.820 | 4,565,262 | $4.66 | 16.6m |

---

## 3. The headline: Go test-coverage trajectory across three versions

`go/none` is the one cell with a data point for **every** model version on the same task,
holding language **and** tooling constant — the cleanest controlled comparison in the
whole program.

| Version | Source | code_quality | **test_coverage** | duration | tokens | cost |
|---------|--------|--------------|-------------------|----------|--------|------|
| claude-opus-4-6 | exp-2 | 1.000 | 0.42 | 4.6m | 1.10M | $1.39 |
| claude-opus-4-7 | exp-3 | 1.000 | **0.81** | 23.1m | 7.61M | $8.13 |
| claude-opus-4-8 | exp-4 | 1.000 | 0.44 | 17.6m | 5.99M | $5.85 |

**Finding: 4-7's high Go coverage was a peak, not a trend.** Coverage went
0.42 → 0.81 → 0.44. `claude-opus-4-8` reverts to roughly `claude-opus-4-6`'s coverage on
Go, after `claude-opus-4-7` spiked. Code quality stayed perfect (1.000) across all three
versions, and 4-8's go cell scored a clean PenScore 1.0 / ReqCov 1.0 — so the lower
coverage is "fewer tests written," not "broken code." Critically, **4-8 used less wall
time than 4-7 (17.6m vs 23.1m) but did not hit the timeout**, so this is a genuine
behavioral difference, not a budget cutoff.

The experiment-3 conclusion — *"claude-opus-4-7 writes more comprehensive Go tests"* —
is now best read as **specific to 4-7**, not a monotonic generational improvement.

---

## 4. Other per-language trajectories

### 4.1 Python — quality improved at 4-8

`python` code_quality had been pinned at 0.667 in every prior experiment (4-6 in both
exp-2 and exp-3). At 4-8 it moves for the first time:

| Version | Source | Tooling | code_quality | test_coverage | cost |
|---------|--------|---------|--------------|---------------|------|
| claude-opus-4-6 | exp-2 | beads | 0.667 | 0.85 | $1.73 |
| claude-opus-4-8 | exp-4 | beads | **0.833** | 0.86 | $5.19 |

`python/4-8/beads` also scored PenScore 1.0, ReqCov 1.0, with a 52-test suite and all
performance targets met (per the evaluator). This is the only language whose
code_quality ladder moved across the three versions.

### 4.2 Clojure — flat scorer metrics, but a requirements-coverage flag

| Version | Source | Tooling | code_quality | test_coverage | PenScore | ReqCov |
|---------|--------|---------|--------------|---------------|----------|--------|
| claude-opus-4-6 | exp-2 | none | 0.833 | 1.000 | — | — |
| claude-opus-4-8 | exp-4 | none | 0.833 | 1.000 | 0.10 | 0.00 |

The mechanical scorers (code_quality, test_coverage) are flat and high, but the
auto-evaluator returned **PenScore 0.10 / ReqCov 0.00** for clojure/4-8 — 9 high-severity
`requirement_missing` findings ("No matching code found" for the canonical players,
clubs, and standings). The generated clojure code's **own** tests pass (coverage 1.0),
yet the evaluator could not match the benchmark's concrete dataset requirements.

This mirrors the `ReqCov`-vs-quality divergence seen in experiments 1–2 (e.g.
go/sonnet/beads: high quality, ReqCov 0.5). Because the requirement matcher is
text/grep-based, it can under-count when data lives in EDN/resource files it does not
scan, so **this cell is flagged for manual confirmation** rather than treated as a
definitive 4-8 regression. It is the one result here that warrants a follow-up.

---

## 5. Cost and runtime: where 4-8 sits

Across the three Go data points, `claude-opus-4-8` lands **between** 4-6 and 4-7 on the
resource-cost dimensions, much closer to a "calm" profile than 4-7's exhaustive one:

| Version | Go duration | Go tokens | Go cost |
|---------|-------------|-----------|---------|
| 4-6 | 4.6m | 1.10M | $1.39 |
| 4-7 | 23.1m | 7.61M | $8.13 |
| 4-8 | 17.6m | 5.99M | $5.85 |

`claude-opus-4-7` was the resource outlier (5× the runtime and 6× the cost of 4-6 on Go).
`claude-opus-4-8` pulls back from that: ~28% cheaper and ~24% faster than 4-7 on Go,
while delivering the same perfect code quality and 4-6-level coverage. The pattern across
all three new 4-8 cells is consistent — 15.9–18.9 minutes, $4.66–$6.57, 4.6M–7.0M
tokens — a tighter band than 4-7 showed in experiment-3.

---

## 6. Code quality remains language-dominated

Consistent with experiments 1–3, the dominant driver of `code_quality` is still
**language**, not model version. At 4-8 the ladder is unchanged: go 1.000 > python 0.833
≈ clojure 0.833 — the same ordering seen for 4-6 and 4-7. The only model-version movement
in the entire `code_quality` response across four experiments is python's 0.667 → 0.833
bump at 4-8 (Section 4.1).

---

## 7. Key findings

1. **4-7's Go coverage spike does not generalize to 4-8.** The controlled go/none
   trajectory is 0.42 → 0.81 → 0.44. 4-8 behaves like 4-6 on Go test thoroughness, with
   perfect code quality throughout. The strongest experiment-3 signal was 4-7-specific.
2. **Python code quality improved at 4-8** for the first time across the program
   (0.667 → 0.833), with PenScore 1.0 / ReqCov 1.0 and a 52-test suite.
3. **4-8 is cheaper and faster than 4-7** on the matched Go cell (−28% cost, −24% time)
   while matching 4-6 coverage and perfect quality — 4-8 did not inherit 4-7's
   resource-heavy, test-exhaustive behavior.
4. **Clojure/4-8 needs manual review:** scorers are perfect but the evaluator flagged
   ReqCov 0.0 (grep-based matcher; possible false negative on EDN/resource data).
5. **Language still dominates code quality**, as in every prior experiment; model version
   is a second-order effect except for the python bump.

---

## 8. Limitations

1. **Resolution III aliasing (unchanged from exp-3):** in the full augmented design the
   model main effect is partially confounded with language-group contrasts. The
   per-language trajectories in Sections 3–4 are the controlled comparisons that sidestep
   this; the cross-cell model average is not reported because it is confounded.
2. **Single new cell per language.** Each 4-8 language point is one cell × 2 replicates.
   The Go trajectory is the only fully controlled (same language + tooling) 3-version
   comparison; python and clojure compare only 4-6 ↔ 4-8.
3. **Carried-over cells, not re-run.** The 4-6/4-7 numbers come from experiments 2–3, run
   on earlier dates; Anthropic may serve different weight snapshots under the same version
   string over time (the same caveat experiment-3 documented).
4. **Evaluator is heuristic.** PenScore/ReqCov come from a haiku grep-based matcher; the
   clojure ReqCov 0.0 in particular should be confirmed by inspection before being treated
   as a regression.
5. **n = 2 per cell.** Directional, not powered for significance on the model factor.

---

## 9. Recommendation for a possible experiment 5

If the python and clojure signals are worth confirming, a controlled follow-up would run
`go/4-8/none` again alongside `python/4-8/none` and `clojure/4-8/beads` (matching the
exact tooling of the prior-version cells) plus a manual clojure requirement audit, to turn
the 4-6 ↔ 4-8 two-point comparisons into clean three-version trajectories like Go's.

---

*Report generated 2026-05-30. Scores from `retort` core scorers + `evaluate-run`
(model=haiku). 4-6/4-7 reference values from `experiment-2/` and `experiment-3/` reports.*
