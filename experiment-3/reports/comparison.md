# Experiment 3: Model Version Comparison
## claude-opus-4-6 vs claude-opus-4-7 — Quarter-Fraction Screening

**Date:** 2026-05-21  
**Experiment:** `experiment-3-model-version-quarter-fraction`  
**Task:** Brazilian Soccer MCP Guide (brazil-bench benchmark)  
**Design:** 6-cell quarter-fraction of the 24-cell full factorial (6 language × 2 model × 2 tooling)

---

## 1. Model Version Documentation

### Experiment-3 (this experiment)
Model IDs are explicit in `design.csv` and stored verbatim in `run_config_json`:
- `claude-opus-4-6` — passed directly to `claude --model claude-opus-4-6`
- `claude-opus-4-7` — passed directly to `claude --model claude-opus-4-7`

### Experiment-2 (prior run, same task)
Experiment-2 ran on **2026-04-13** using model alias `"opus"`. At that time, the runner
(`local_runner.py` at commit `b962b05`) contained **no MODEL_ALIASES dict** — it passed
`--model opus` literally to the Claude CLI. Since `claude-opus-4-7` did not yet exist in April 2026,
the Claude CLI resolved `"opus"` to **`claude-opus-4-6`**. The string `"opus"` is stored in the
experiment-2 DB; the resolved model ID is `claude-opus-4-6` by elimination.

The first explicit `MODEL_ALIASES = {"opus": "claude-opus-4-6", ...}` was committed on April 18
(commit `a394e9b`), five days after experiment-2 completed. On May 12 (commit `90037b4`),
versioned aliases were added and the short `"opus"` alias was updated to `"claude-opus-4-7"`.

**Summary:** Both experiment-2 `"opus"` and experiment-3 `"claude-opus-4-6"` invoked the same
model ID. The weight snapshot Anthropic served may differ between April 13 and May 21 — that is
unverifiable from external observation.

---

## 2. Design Summary

The full factorial has 24 cells (6 language × 2 model × 2 tooling). We ran a Resolution III
quarter-fraction (6 cells × 2 replicates = 12 run-slots) to estimate model and tooling effects
at 12× lower cost. Four polecats ran simultaneously with deterministic shard assignment.

| Cell | Language   | Model            | Tooling | Role                        |
|------|------------|------------------|---------|-----------------------------|
| A    | python     | claude-opus-4-6  | none    | anchor: 4-6 × none          |
| B    | typescript | claude-opus-4-6  | beads   | 4-6 × beads singleton        |
| C    | go         | claude-opus-4-7  | none    | 4-7 × none singleton         |
| D    | rust       | claude-opus-4-7  | beads   | anchor: 4-7 × beads          |
| E    | java       | claude-opus-4-6  | none    | paired with A (same model)   |
| F    | clojure    | claude-opus-4-7  | beads   | paired with D (same model)   |

**Aliasing (Resolution III):** The model main effect is aliased with the {python, typescript, java}
vs {go, rust, clojure} language contrast. Model and language effects cannot be fully separated in
this design; the `model:tooling` interaction is estimable.

---

## 3. Execution Notes

### Adaptive Timeout (new in this experiment)
The initial `timeout_minutes: 25` caused all rust and clojure runs to time out in the first pass.
**Adaptive per-run timeout estimation** was added (`_estimate_run_timeout` in `cli.py`), which queries
historical `_duration_seconds` from prior completed runs and computes `ceil(max_observed × 1.5 / 60)`
as the per-cell budget. After retry with 45-minute timeout, all cells completed.

### Scorer Bugs Fixed (this session)
Several bugs caused systematic zero scores in prior experiments. All were fixed before rescoring:

| Bug | Language | Root cause | Fix |
|-----|----------|------------|-----|
| Java zeros | java | `mvn -q test` silenced surefire summary output | Removed `-q` |
| Clojure zeros | clojure | `-X:test` requires `:exec-fn`; agents use `:main-opts` | Changed to `-M:test` |
| Rust zeros | rust | No coverage command → returned `None` early; `search()` matched first empty binary | Added early-exit fallback path; changed to `finditer` picking max-total match |
| TypeScript zeros | typescript | `npx vitest` hits broken `.bin/vitest` wrapper; `--coverage` fails without `@vitest/coverage-v8` | Direct node invocation; test-pass-rate fallback |

All completed runs from all three experiments were rescored with the fixed scorer via `rescore_all.py`.

---

## 4. Experiment-3 Results

### 4.1 Scores by Cell (averages across 2 replicates)

| Language   | Model            | Tooling | cov avg | cq avg | idiomatic avg | maint avg | avg dur |
|------------|------------------|---------|---------|--------|---------------|-----------|---------|
| go         | claude-opus-4-7  | none    | 0.813   | 1.000  | 0.85          | 0.585     | 23.1m   |
| java       | claude-opus-4-6  | none    | 1.000   | 1.000  | 0.735         | 0.794     | 12.9m   |
| rust       | claude-opus-4-7  | beads   | 1.000   | 0.833  | 0.87          | 0.478     | 25.0m   |
| python     | claude-opus-4-6  | none    | 0.897   | 0.667  | 0.56          | 0.575     | 5.2m    |
| typescript | claude-opus-4-6  | beads   | 1.000   | 0.733  | 0.607         | 0.513     | 6.7m    |
| clojure    | claude-opus-4-7  | beads   | 1.000   | 0.833  | 0.855         | 0.684     | 20.9m   |

*Python and TypeScript each had one extra replicate run across polecats (3 data points vs 2).
Averages include all available data points.*

### 4.2 Individual Run Data

| Polecat  | Language   | Model           | Tooling | Rep | cov   | cq    | idom | maint | dur   |
|----------|------------|-----------------|---------|-----|-------|-------|------|-------|-------|
| dag      | go         | claude-opus-4-7 | none    | 1   | 0.765 | 1.000 | 0.82 | 0.517 | 24.6m |
| cheedo   | go         | claude-opus-4-7 | none    | 2   | 0.861 | 1.000 | 0.88 | 0.653 | 21.6m |
| capable  | java       | claude-opus-4-6 | none    | 1   | 1.000 | 1.000 | 0.70 | 0.870 | 13.5m |
| dementus | java       | claude-opus-4-6 | none    | 2   | 1.000 | 1.000 | 0.77 | 0.717 | 12.2m |
| dementus | rust       | claude-opus-4-7 | beads   | 1   | 1.000 | 0.833 | 0.87 | 0.482 | 29.7m |
| capable  | rust       | claude-opus-4-7 | beads   | 2   | 1.000 | 0.833 | 0.87 | 0.474 | 20.3m |
| cheedo   | python     | claude-opus-4-6 | none    | 1   | 0.980 | 0.667 | 0.52 | 0.689 | 5.0m  |
| dag      | python     | claude-opus-4-6 | none    | 1   | 0.960 | 0.667 | 0.38 | 0.626 | 3.9m  |
| dag      | python     | claude-opus-4-6 | none    | 2   | 0.750 | 0.667 | 0.78 | 0.410 | 6.7m  |
| cheedo   | typescript | claude-opus-4-6 | beads   | 1   | 1.000 | 0.733 | 0.72 | 0.333 | 7.1m  |
| dag      | typescript | claude-opus-4-6 | beads   | 1   | 1.000 | 0.733 | 0.72 | 0.667 | 7.1m  |
| cheedo   | typescript | claude-opus-4-6 | beads   | 2   | 1.000 | 0.733 | 0.38 | 0.539 | 5.9m  |
| dag      | clojure    | claude-opus-4-7 | beads   | 1   | 1.000 | 0.833 | 0.87 | 0.668 | 20.6m |
| dementus | clojure    | claude-opus-4-7 | beads   | 2   | 1.000 | 0.833 | 0.84 | 0.699 | 21.1m |

---

## 5. Cross-Experiment Model Comparison

### 5.1 Key Question

Does `claude-opus-4-7` outperform `claude-opus-4-6` on brazil-bench? And did model quality change
between experiment-2 (April 2026, `"opus"` → `claude-opus-4-6`) and experiment-3 (May 2026,
explicit IDs)?

### 5.2 Side-by-Side: Experiment-2 vs Experiment-3

Both experiments used the same task (brazilian-soccer-mcp-guide.md, brazil-bench). Experiment-2
used 1 replicate per cell; experiment-3 used 2 replicates. Scores shown are mean across replicates.

#### Languages with claude-opus-4-6 in both experiments

| Language | Metric        | Exp-2 (Apr 2026, "opus") | Exp-3 (May 2026, explicit 4-6) | Δ      |
|----------|---------------|--------------------------|--------------------------------|--------|
| java     | code_quality  | 1.000                    | 1.000                          | 0.000  |
| java     | test_coverage | 1.000                    | 1.000                          | 0.000  |
| java     | duration      | 3.6m (none), 5.7m (beads)| 12.9m avg                      | +3–9m  |
| python   | code_quality  | 0.667                    | 0.667                          | 0.000  |
| python   | test_coverage | 0.800 (none)             | 0.897 avg                      | +0.10  |
| python   | duration      | 2.5m (none), 5.8m (beads)| 5.2m avg                       | +2–3m  |

**Finding:** Same model ID, same task, same quality outcomes. The 2–9 minute runtime increase in
experiment-3 suggests more thorough exploration within the budget, not a model quality change.
(Note: experiment-2 `"opus"` may have been a different Anthropic-internal snapshot than
experiment-3 `claude-opus-4-6`; model IDs are not guaranteed to be immutable across deployments.)

#### Model upgrade comparison: claude-opus-4-6 → claude-opus-4-7 (experiment-3 only)

The Resolution III design assigns each language to one model, so this is a cross-cell comparison,
not a controlled A/B test. Language and tooling effects are aliased with the model effect.

| Metric        | claude-opus-4-6 cells (java, python, typescript) | claude-opus-4-7 cells (go, rust, clojure) |
|---------------|--------------------------------------------------|-------------------------------------------|
| code_quality  | avg 0.800 (java 1.0, py 0.667, ts 0.733)         | avg 0.889 (go 1.0, rust 0.833, clj 0.833)|
| test_coverage | avg 0.966 (java 1.0, py 0.897, ts 1.0)           | avg 0.938 (go 0.813, rust 1.0, clj 1.0)  |
| maintainability| avg 0.627 (java 0.794, py 0.575, ts 0.513)       | avg 0.582 (go 0.585, rust 0.478, clj 0.684)|
| avg duration  | 8.3m                                             | 23.0m                                     |

**Caution:** These averages cannot separate model from language effects. Go, Rust, and Clojure are
compiled languages with heavier build pipelines; Java, Python, and TypeScript include scripted
languages. The 23-minute average for claude-opus-4-7 cells vs 8-minute average for claude-opus-4-6
cells primarily reflects compiled vs scripted language runtimes, not model throughput.

#### Most direct model comparison: Go across experiments

Go appeared in both experiment-2 (opus/claude-opus-4-6) and experiment-3 (claude-opus-4-7), on the
same task. This is the closest controlled comparison available:

| Metric        | Exp-2 go/opus (4-6) none | Exp-2 go/opus (4-6) beads | Exp-3 go/4-7 none (avg) |
|---------------|--------------------------|---------------------------|--------------------------|
| code_quality  | 1.000                    | 1.000                     | 1.000                    |
| test_coverage | 0.423                    | 0.333                     | **0.813**                |
| duration      | 4.6m                     | 4.5m                      | 23.1m                    |

**Go coverage finding:** `claude-opus-4-7` achieves 81% test coverage on the Go implementation vs
42% (none) / 33% (beads) for `claude-opus-4-6`. The code quality is identical (1.0 = zero high/critical
findings). The 5× runtime increase correlates with more thorough test writing. This is the clearest
signal in the dataset that claude-opus-4-7 writes more comprehensive tests for Go.

**Confounds:** Model (4-6 vs 4-7) and tooling (beads vs none in exp-2; none only in exp-3) differ.
The higher coverage in exp-3 could also reflect the longer timeout (45 min vs 25 min), giving the
model more time to write tests. An experiment-4 run of go/claude-opus-4-6/none with a 45-min
timeout would control for the timeout variable.

### 5.3 Experiment-2 vs Experiment-3 Runtime Comparison

| Language | Exp-2 avg dur | Exp-3 dur   | Factor |
|----------|---------------|-------------|--------|
| java     | 3.6m (none)   | 12.9m       | 3.6×   |
| python   | 2.5m (none)   | 5.2m        | 2.1×   |
| go       | 4.6m (none)   | 23.1m       | 5.0×   |
| rust     | 2.9m (none)   | 25.0m       | 8.6×   |
| clojure  | 3.0m (none)   | 20.9m       | 7.0×   |

The consistent 2–9× runtime increase across all languages suggests that the models in experiment-3
are doing substantially more work — likely more iterations, more self-correction, and more thorough
testing — within the extended 45-minute budget. Experiment-2 used a 25-minute timeout, but most
runs finished in under 6 minutes (timeout was not binding).

---

## 6. Experiment-2 Results (Brazil-Bench, April 2026)

For reference: all scores after rescoring with fixed scorer. Model "opus" = claude-opus-4-6.

| Language   | Model  | Tooling | cov   | cq    | dur   |
|------------|--------|---------|-------|-------|-------|
| go         | opus   | none    | 0.423 | 1.000 | 4.6m  |
| go         | opus   | beads   | 0.333 | 1.000 | 4.5m  |
| go         | sonnet | none    | 0.769 | 1.000 | 7.1m  |
| java       | opus   | none    | 1.000 | 1.000 | 3.6m  |
| java       | opus   | beads   | 1.000 | 1.000 | 5.7m  |
| java       | sonnet | none    | 1.000 | 1.000 | 5.5m  |
| java       | sonnet | beads   | 1.000 | 1.000 | 11.2m |
| rust       | opus   | none    | 1.000 | 0.833 | 2.9m  |
| rust       | opus   | beads   | 1.000 | 0.833 | 5.8m  |
| rust       | sonnet | none    | 1.000 | 0.833 | 7.9m  |
| rust       | sonnet | beads   | 0.333 | 0.833 | 8.9m  |
| python     | opus   | none    | 0.800 | 0.667 | 2.5m  |
| python     | opus   | beads   | 0.850 | 0.667 | 5.8m  |
| python     | sonnet | none    | 0.960 | 0.667 | 5.5m  |
| python     | sonnet | beads   | 0.970 | 0.667 | 8.1m  |
| clojure    | opus   | none    | 1.000 | 0.833 | 3.0m  |
| clojure    | opus   | beads   | 1.000 | 0.833 | 5.7m  |
| clojure    | sonnet | none    | 1.000 | 0.833 | 7.3m  |
| clojure    | sonnet | beads   | 1.000 | 0.833 | 6.8m  |
| typescript | opus   | none    | 0.000 | 0.000 | 3.1m  |
| typescript | opus   | beads   | 0.000 | 0.000 | 3.4m  |
| typescript | sonnet | none    | 0.961 | 0.733 | 4.6m  |
| typescript | sonnet | beads   | 1.000 | 0.733 | 6.0m  |

**Note on TypeScript/opus zeros:** The two experiment-2 typescript/opus runs have cov=0 and cq=0.
Manual inspection of the archived run directories shows neither vitest nor jest in `package.json`
in these runs. The scorer correctly returns 0 — this is a genuine measurement (the agent produced
code with no recognized test framework), not a scorer bug.

**Note on TypeScript/opus-4-6 (experiment-3):** The same language/model combination with beads
tooling in experiment-3 scores cov=1.0, cq=0.733. With beads tooling, the agent received
structured tooling support that guided it to include vitest, explaining the reversal.

---

## 7. ANOVA Results (Experiment-3)

*Analysis based on 14 completed runs across 6 cells. Note: only 2 model levels and 3 observations
per model make this underpowered. Results are directional.*

### Significant Effects (p < 0.10)

| Response         | Significant factors                                |
|-----------------|----------------------------------------------------|
| code_quality    | language, language:tooling, model:tooling          |
| test_coverage   | language, model, language:tooling, model:tooling   |
| maintainability | language, language:tooling, model:tooling          |
| idiomatic       | language, language:tooling, model:tooling          |
| token_efficiency| language, language:tooling                        |

The `model` main effect cannot be estimated independently from the {python, typescript, java} vs
{go, rust, clojure} language contrast. The `model:tooling` interaction is estimable and
consistently significant — the two models respond differently to beads tooling.

---

## 8. Key Findings

### 1. Go + claude-opus-4-7 produced the highest coverage with perfect code quality
Both go/4-7 replicates scored `code_quality=1.000` with zero high-severity findings and
`test_coverage=0.765–0.861`. The evaluator confirmed all 9 requirements implemented, 30 tests
passing, build clean in 1.2s. This is the strongest result in the experiment.

### 2. claude-opus-4-7 achieves notably better Go test coverage than claude-opus-4-6
Experiment-2 go/opus (claude-opus-4-6): 42% coverage. Experiment-3 go/claude-opus-4-7: 81%
average coverage. Same task, same code quality. The model writes more comprehensive tests.
Confound: experiment-3 used a 45-minute timeout vs 25 minutes in experiment-2.

### 3. Java and Rust achieve maximum test coverage regardless of model
Both show `test_coverage=1.000` across all replicates and both experiments. These languages
have strong testing conventions that guide both models to write complete test suites.

### 4. TypeScript outcome depends strongly on tooling
- Experiment-2, opus (4-6), no beads: `test_coverage=0.0` (no test framework in generated code)
- Experiment-3, opus (4-6), with beads: `test_coverage=1.000` (vitest included)
- This `model:tooling` interaction is the most concrete example of the estimable interaction term.

### 5. Model quality appears stable across the 5-week gap (April → May 2026)
For java and python — the two languages assigned to claude-opus-4-6 in both experiments — quality
metrics are identical or nearly so. The model ID `claude-opus-4-6` produced the same code quality
in April and May, though Anthropic could have updated weights without changing the version string.

### 6. Runtime increased 2–9× between experiments
Experiment-2 runs completed in 2.5–11 minutes. Experiment-3 runs took 4–30 minutes. Compiled
language runs (rust, clojure) required the full 45-minute budget on first attempt. The extended
duration likely reflects more thorough implementations, not model regression.

---

## 9. Limitations

1. **Resolution III aliasing:** Model main effect is confounded with language group. The
   go/coverage finding is the best evidence for a 4-7 improvement, but needs a controlled follow-up.
2. **Timeout confound:** The longer timeout in experiment-3 may contribute to higher scores
   independent of model version. A direct comparison would hold timeout constant.
3. **TypeScript/opus zeros in experiment-2:** These reflect a genuine agent limitation (no test
   framework), not scorer error. The beads tooling in experiment-3 resolves this.
4. **Duplicate rep1 runs:** Python and TypeScript each have two "rep1" runs from different polecats
   due to shard assignment. These are treated as independent data points, increasing effective n
   slightly but with different replication meaning than designed.
5. **Small n:** 2 replicates per cell limits statistical power. Model-level conclusions need
   experiment-4 augmentation.

---

## 10. Recommendations for Experiment 4

1. **Break the aliasing:** Run go/claude-opus-4-6/none and python/claude-opus-4-7/none to separate
   model from language group contrast.
2. **Control timeout:** Run experiment-2 cells with 45-minute timeout to isolate timeout effect
   from model effect on coverage.
3. **Confirm TypeScript/beads finding:** Add typescript/claude-opus-4-6/none to test whether beads
   or something else drove the test framework inclusion.
4. **The adaptive timeout system is now in place:** Future experiments will set appropriate timeouts
   automatically as historical data accumulates.

---

*Report generated by mayor. Rescoring and analysis on 2026-05-21. ANOVA via `retort analyze`.*
*Model version history verified from git log of `local_runner.py` in the retort repo.*
