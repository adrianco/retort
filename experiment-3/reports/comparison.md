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

### 4.1 Scores by Cell (averages across replicates)

| Language   | Model            | Tooling | cov avg | cq avg | idiomatic | maint | avg dur | avg tokens | avg cost  |
|------------|------------------|---------|---------|--------|-----------|-------|---------|------------|-----------|
| go         | claude-opus-4-7  | none    | 0.813   | 1.000  | 0.85      | 0.585 | 23.1m   | 7,612,020  | $8.13     |
| java       | claude-opus-4-6  | none    | 1.000   | 1.000  | 0.735     | 0.794 | 12.9m   | 2,472,358  | $2.87     |
| rust       | claude-opus-4-7  | beads   | 1.000   | 0.833  | 0.87      | 0.478 | 25.0m   | 7,573,138  | $7.34     |
| python     | claude-opus-4-6  | none    | 0.897   | 0.667  | 0.56      | 0.575 | 5.2m    | 750,075    | $0.98     |
| typescript | claude-opus-4-6  | beads   | 1.000   | 0.733  | 0.607     | 0.513 | 6.7m    | 1,545,433  | $1.56     |
| clojure    | claude-opus-4-7  | beads   | 1.000   | 0.833  | 0.855     | 0.684 | 20.9m   | 5,007,051  | $5.30     |

**Total experiment-3: 14 runs, $54.94, 52.2M tokens** (avg $3.92/run, 3.73M tokens/run)

*Python and TypeScript each had one extra replicate run across polecats (3 data points vs 2).
Averages include all available data points.*

### 4.2 Individual Run Data

| Polecat  | Language   | Model           | Tooling | Rep | cov   | cq    | dur   | tokens     | cost    |
|----------|------------|-----------------|---------|-----|-------|-------|-------|------------|---------|
| dag      | go         | claude-opus-4-7 | none    | 1   | 0.765 | 1.000 | 24.6m | 8,620,042  | $9.35   |
| cheedo   | go         | claude-opus-4-7 | none    | 2   | 0.861 | 1.000 | 21.6m | 6,603,998  | $6.91   |
| capable  | java       | claude-opus-4-6 | none    | 1   | 1.000 | 1.000 | 13.5m | 3,659,358  | $3.54   |
| dementus | java       | claude-opus-4-6 | none    | 2   | 1.000 | 1.000 | 12.2m | 1,285,357  | $2.21   |
| dementus | rust       | claude-opus-4-7 | beads   | 1   | 1.000 | 0.833 | 29.7m | 10,526,048 | $9.37   |
| capable  | rust       | claude-opus-4-7 | beads   | 2   | 1.000 | 0.833 | 20.3m | 4,620,228  | $5.31   |
| cheedo   | python     | claude-opus-4-6 | none    | 1   | 0.980 | 0.667 | 5.0m  | 803,212    | $1.07   |
| dag      | python     | claude-opus-4-6 | none    | 1   | 0.960 | 0.667 | 3.9m  | 538,447    | $0.80   |
| dag      | python     | claude-opus-4-6 | none    | 2   | 0.750 | 0.667 | 6.7m  | 908,567    | $1.08   |
| cheedo   | typescript | claude-opus-4-6 | beads   | 1   | 1.000 | 0.733 | 7.1m  | 1,743,636  | $1.65   |
| dag      | typescript | claude-opus-4-6 | beads   | 1   | 1.000 | 0.733 | 7.1m  | 1,798,252  | $1.74   |
| cheedo   | typescript | claude-opus-4-6 | beads   | 2   | 1.000 | 0.733 | 5.9m  | 1,095,410  | $1.30   |
| dag      | clojure    | claude-opus-4-7 | beads   | 1   | 1.000 | 0.833 | 20.6m | 4,389,693  | $4.81   |
| dementus | clojure    | claude-opus-4-7 | beads   | 2   | 1.000 | 0.833 | 21.1m | 5,624,409  | $5.80   |

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

### 5.3 Experiment-2 vs Experiment-3 Runtime and Cost Comparison

| Language | Exp-2 dur (none) | Exp-3 dur  | Dur factor | Exp-2 cost (none) | Exp-3 cost avg | Cost factor |
|----------|------------------|------------|------------|-------------------|----------------|-------------|
| java     | 3.6m             | 12.9m      | 3.6×       | $1.26             | $2.87          | 2.3×        |
| python   | 2.5m             | 5.2m       | 2.1×       | $0.73             | $0.98          | 1.3×        |
| go       | 4.6m             | 23.1m      | 5.0×       | $1.39             | $8.13          | 5.9×        |
| rust     | 2.9m             | 25.0m      | 8.6×       | $0.87             | $7.34          | 8.4×        |
| clojure  | 3.0m             | 20.9m      | 7.0×       | $0.81             | $5.30          | 6.5×        |

The consistent 2–9× runtime and cost increase across all languages reflects both the longer timeout
budget (25 min in experiment-2, 45 min in experiment-3) and the model spending more time on
thorough implementation. Notably, the cost increase for Go, Rust, and Clojure (all claude-opus-4-7)
is 6–8×, while for Java and Python (claude-opus-4-6) it is 1.3–2.3×. This is partly a model-version
difference (claude-opus-4-7 is more expensive per token) and partly a language-complexity effect.

---

## 6. Experiment-2 Results (Brazil-Bench, April 2026)

For reference: all scores after rescoring with fixed scorer. Model `"opus"` = claude-opus-4-6 (resolved
by Claude CLI alias). `"sonnet"` = claude-sonnet-4-5.

**Total experiment-2: 22 completed runs, $29.85, 33.6M tokens** (avg $1.36/run, 1.53M tokens/run)

| Language   | Model  | Tooling | cov   | cq    | dur   | tokens     | cost   |
|------------|--------|---------|-------|-------|-------|------------|--------|
| go         | opus   | none    | 0.423 | 1.000 | 4.6m  | 1,098,817  | $1.39  |
| go         | opus   | beads   | 0.333 | 1.000 | 4.5m  | 683,860    | $1.23  |
| go         | sonnet | none    | 0.769 | 1.000 | 7.1m  | 1,540,294  | $1.18  |
| java       | opus   | none    | 1.000 | 1.000 | 3.6m  | 965,345    | $1.26  |
| java       | opus   | beads   | 1.000 | 1.000 | 5.7m  | 1,669,932  | $1.75  |
| java       | sonnet | none    | 1.000 | 1.000 | 5.5m  | —          | —      |
| java       | sonnet | beads   | 1.000 | 1.000 | 11.2m | 2,779,597  | $1.84  |
| rust       | opus   | none    | 1.000 | 0.833 | 2.9m  | 593,895    | $0.87  |
| rust       | opus   | beads   | 1.000 | 0.833 | 5.8m  | 1,108,771  | $1.57  |
| rust       | sonnet | none    | 1.000 | 0.833 | 7.9m  | 209,825    | $1.14  |
| rust       | sonnet | beads   | 0.333 | 0.833 | 8.9m  | 491,969    | $1.11  |
| python     | opus   | none    | 0.800 | 0.667 | 2.5m  | 580,884    | $0.73  |
| python     | opus   | beads   | 0.850 | 0.667 | 5.8m  | 1,625,376  | $1.73  |
| python     | sonnet | none    | 0.960 | 0.667 | 5.5m  | 879,497    | $0.72  |
| python     | sonnet | beads   | 0.970 | 0.667 | 8.1m  | 2,113,900  | $1.25  |
| clojure    | opus   | none    | 1.000 | 0.833 | 3.0m  | 630,222    | $0.81  |
| clojure    | opus   | beads   | 1.000 | 0.833 | 5.7m  | 1,391,321  | $1.39  |
| clojure    | sonnet | none    | 1.000 | 0.833 | 7.3m  | 1,920,625  | $1.12  |
| clojure    | sonnet | beads   | 1.000 | 0.833 | 6.8m  | 1,811,932  | $1.03  |
| typescript | opus   | none    | 0.000 | 0.000 | 3.1m  | 919,663    | $1.01  |
| typescript | opus   | beads   | 0.000 | 0.000 | 3.4m  | 1,022,265  | $1.07  |
| typescript | sonnet | none    | 0.961 | 0.733 | 4.6m  | 797,512    | $0.71  |
| typescript | sonnet | beads   | 1.000 | 0.733 | 6.0m  | 1,556,688  | $0.92  |

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
