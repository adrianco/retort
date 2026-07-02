# Experiment 15 — Sonnet 5 vs existing models

> Auto-generated from `master.csv` by the experiment driver. Sonnet 5 is the only newly-run model; **Sonnet 4.6 and Opus 4.8 baselines are read from prior experiments in master.db, not re-run** (Retort's incremental design).

Sonnet 5 rows aggregated: **29**. Tasks with Sonnet 5 data: brazil-soccer-mcp, rest-api-crud.

**Caveats:** single replicate (cell scores noisy); the `sonnet-4.6` family is the historical `sonnet` alias; the hard-task Sonnet 5 runs use `brazil-bench-neutral` while the master baseline is the BDD-baked `brazil-soccer-mcp` variant, so hard-task cross-model deltas are indicative, not exact.


## Task: brazil-soccer-mcp

### Quality/coverage means by model

| model | n | code_quality | test_coverage | defect_rate | maintainability | idiomatic | token_efficiency | requirement_coverage |
|---|---|---|---|---|---|---|---|---|
| sonnet-5 | 14 | 0.88 | 0.92 | 1.00 | 0.68 | 0.84 | 0.27 | — |
| sonnet-4.6 | 48 | 0.86 | 0.91 | 0.94 | 0.60 | 0.71 | 0.17 | 0.95 |
| opus-4.8 | 26 | 0.86 | 0.87 | 1.00 | 0.58 | 0.80 | 0.35 | 1.00 |


### Cost/effort means by model

| model | n | cost_usd | tokens | duration_seconds |
|---|---|---|---|---|
| sonnet-5 | 14 | 7.53 | 15602120.93 | 1246.19 |
| sonnet-4.6 | 48 | 2.05 | 2744453.19 | 754.96 |
| opus-4.8 | 26 | 5.53 | 5324000.50 | 1027.82 |


### Sonnet 5 by language (this task)

| language | n | code_quality | test_coverage | defect_rate | maintainability | idiomatic | token_efficiency | requirement_coverage | cost_usd | tokens | duration_seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|
| csharp | 3 | 1.00 | 0.89 | 1.00 | 0.83 | 0.85 | 0.00 | — | 9.96 | 21491868.00 | 1399.10 |
| go | 3 | 1.00 | 0.80 | 1.00 | 0.59 | 0.87 | 0.00 | — | 5.96 | 11251454.00 | 1007.64 |
| python | 3 | 0.83 | 0.94 | 1.00 | 0.76 | 0.84 | 0.34 | — | 5.18 | 9836606.67 | 1031.58 |
| rust | 2 | 0.83 | 1.00 | 0.99 | 0.36 | 0.85 | 0.00 | — | 10.07 | 22375920.50 | 1672.09 |
| typescript | 3 | 0.73 | 1.00 | 1.00 | 0.77 | 0.79 | 0.93 | — | 7.32 | 15312688.67 | 1262.50 |


### Sonnet 5 by prompt methodology (this task)

| prompt | n | code_quality | test_coverage | defect_rate | maintainability | idiomatic | token_efficiency | requirement_coverage |
|---|---|---|---|---|---|---|---|---|
| bdd | 5 | 0.88 | 0.90 | 1.00 | 0.63 | 0.85 | 0.20 | — |
| none | 5 | 0.88 | 0.93 | 1.00 | 0.59 | 0.83 | 0.40 | — |
| tdd | 4 | 0.89 | 0.94 | 1.00 | 0.87 | 0.84 | 0.20 | — |


## Task: rest-api-crud

### Quality/coverage means by model

| model | n | code_quality | test_coverage | defect_rate | maintainability | idiomatic | token_efficiency | requirement_coverage |
|---|---|---|---|---|---|---|---|---|
| sonnet-5 | 15 | 0.88 | 0.87 | 1.00 | 0.75 | 0.72 | 0.35 | — |
| sonnet-4.6 | 37 | 0.77 | 0.78 | 0.82 | 0.74 | 0.64 | 0.39 | 0.69 |
| opus-4.8 | 45 | 0.88 | 0.95 | 0.87 | 0.69 | 0.79 | 0.26 | 1.00 |


### Cost/effort means by model

| model | n | cost_usd | tokens | duration_seconds |
|---|---|---|---|---|
| sonnet-5 | 15 | 1.10 | 1994248.00 | 237.49 |
| sonnet-4.6 | 37 | 0.40 | 557269.97 | 187.91 |
| opus-4.8 | 45 | 0.96 | 614346.27 | 240.38 |


### Sonnet 5 by language (this task)

| language | n | code_quality | test_coverage | defect_rate | maintainability | idiomatic | token_efficiency | requirement_coverage | cost_usd | tokens | duration_seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|
| csharp | 3 | 1.00 | 0.73 | 1.00 | 0.69 | 0.82 | 0.00 | — | 1.57 | 3035426.00 | 303.66 |
| go | 3 | 1.00 | 0.68 | 1.00 | 0.88 | 0.75 | 0.01 | — | 0.70 | 990567.33 | 154.89 |
| python | 3 | 0.83 | 0.99 | 1.00 | 0.50 | 0.42 | 0.67 | — | 0.83 | 1477534.67 | 161.29 |
| rust | 3 | 0.83 | 1.00 | 1.00 | 0.93 | 0.78 | 0.09 | — | 1.25 | 2258104.00 | 305.85 |
| typescript | 3 | 0.73 | 0.94 | 1.00 | 0.75 | 0.82 | 1.00 | — | 1.12 | 2209608.00 | 261.77 |


### Sonnet 5 by prompt methodology (this task)

| prompt | n | code_quality | test_coverage | defect_rate | maintainability | idiomatic | token_efficiency | requirement_coverage |
|---|---|---|---|---|---|---|---|---|
| bdd | 5 | 0.88 | 0.91 | 1.00 | 0.75 | 0.77 | 0.42 | — |
| none | 5 | 0.88 | 0.76 | 1.00 | 0.67 | 0.67 | 0.43 | — |
| tdd | 5 | 0.88 | 0.94 | 1.00 | 0.84 | 0.71 | 0.21 | — |


## Headline: Sonnet 5 vs Sonnet 4.6 on rest-api-crud

| metric | sonnet-5 | sonnet-4.6 | Δ (s5 − s46) |
|---|---|---|---|
| code_quality | 0.88 | 0.77 | +0.11 |
| test_coverage | 0.87 | 0.78 | +0.09 |
| defect_rate | 1.00 | 0.82 | +0.18 |
| maintainability | 0.75 | 0.74 | +0.02 |
| idiomatic | 0.72 | 0.64 | +0.08 |
| token_efficiency | 0.35 | 0.39 | -0.04 |
| cost_usd | 1.10 | 0.40 | +0.70 |
| tokens | 1994248.00 | 557269.97 | +1436978.03 |
| duration_seconds | 237.49 | 187.91 | +49.58 |

## Failures

1 of 15 hard-task (brazil) Sonnet 5 cells failed: **rust + tdd** — classified
**GENUINE** by `retort diagnose` (the code genuinely didn't build/pass; not a
scoring artefact recoverable by `rescore`). All 15 easy-task cells and the
other 14 hard-task cells completed. The failure is left as a real data point
rather than re-run. Rust was also the most expensive/token-heavy language for
Sonnet 5 on both tasks.

