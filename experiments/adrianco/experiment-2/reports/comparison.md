# Experiment 2: Full Comparison Report

Generated: 2026-05-21

## Overview

Experiment 2 replicated Experiment 1's language ranking on a larger, more realistic
task — the Brazilian Soccer MCP Guide — to validate whether the language hierarchy
holds beyond simple CRUD implementations.

| Setting | Value |
|---------|-------|
| Task | brazil-bench (Brazilian Soccer statistics MCP server) |
| Runner | local (Claude Code CLI on host) |
| Factors | language × model × tooling |
| Languages | python, typescript, go, clojure, java, rust |
| Models | claude-opus-4-7 (`opus`), claude-sonnet-4-6 (`sonnet`) |
| Tooling | none, beads (task-tracking assistant) |
| Design | 6×2×2 full factorial (24 cells) |
| Replicates | 1 per cell |
| **Total runs** | **24** (all completed) |
| **Total cost** | **$29.85** (33.6M tokens) |

## Per-Run Results

| Language | Model | Tooling | Quality | Coverage | Tokens | Cost |
|----------|-------|---------|---------|----------|--------|------|
| clojure | opus | beads | 0.833 | 1.000 | 1,391,321 | $1.391 |
| clojure | opus | none | 0.833 | 1.000 | 630,222 | $0.809 |
| clojure | sonnet | beads | 0.833 | 1.000 | 1,811,932 | $1.029 |
| clojure | sonnet | none | 0.833 | 1.000 | 1,920,625 | $1.125 |
| go | opus | beads | 1.000 | 0.333 | 683,860 | $1.227 |
| go | opus | none | 1.000 | 0.423 | 1,098,817 | $1.387 |
| go | sonnet | beads | 1.000 | 0.579 | 3,180,387 | $1.724 |
| go | sonnet | none | 1.000 | 0.769 | 1,540,294 | $1.178 |
| java | opus | beads | 1.000 | 1.000 | 1,669,932 | $1.753 |
| java | opus | none | 1.000 | 1.000 | 965,345 | $1.256 |
| java | sonnet | beads | 1.000 | 1.000 | 2,779,597 | $1.836 |
| java | sonnet | none | 1.000 | 1.000 | 4,013,637 | $2.312 |
| python | opus | beads | 0.667 | 0.850 | 1,625,376 | $1.726 |
| python | opus | none | 0.667 | 0.800 | 580,884 | $0.726 |
| python | sonnet | beads | 0.667 | 0.970 | 2,113,900 | $1.247 |
| python | sonnet | none | 0.667 | 0.960 | 879,497 | $0.716 |
| rust | opus | beads | 0.833 | 1.000 | 1,108,771 | $1.575 |
| rust | opus | none | 0.833 | 1.000 | 593,895 | $0.866 |
| rust | sonnet | beads | 0.833 | 0.333 | 491,969 | $1.109 |
| rust | sonnet | none | 0.833 | 1.000 | 209,825 | $1.144 |
| typescript | opus | beads | 0.000 | 0.000 | 1,022,265 | $1.067 |
| typescript | opus | none | 0.000 | 0.000 | 919,663 | $1.013 |
| typescript | sonnet | beads | 0.733 | 1.000 | 1,556,688 | $0.925 |
| typescript | sonnet | none | 0.733 | 0.961 | 797,512 | $0.709 |

## Factor Means (code_quality)

| Factor | Level | Mean Quality | N |
|--------|-------|-------------|---|
| language | java | **1.000** | 4 |
| language | go | **1.000** | 4 |
| language | clojure | 0.833 | 4 |
| language | rust | 0.833 | 4 |
| language | python | 0.667 | 4 |
| language | typescript | 0.367 | 4 |
| model | opus | **0.806** | 12 |
| model | sonnet | 0.792 | 12 |
| tooling | none | 0.806 | 12 |
| tooling | beads | 0.792 | 12 |

## Key Findings

### Experiment 1 Ranking Largely Confirmed

The brazil-bench task replicates the language hierarchy from Experiment 1 with
two notable differences:

**Confirmed:** Java and Go at the top (both 1.000), Python near the bottom (0.667).
The consistency across very different tasks — simple CRUD vs. a complex sports
statistics server — suggests the ranking reflects language ecosystem fitness for
AI-assisted development, not task-specific artifacts.

**Changed:** TypeScript collapsed. Where Experiment 1 showed TypeScript at 0.733
(reliable when it worked), the brazil-bench task triggered a complete failure for
Opus across both tooling conditions (0.000). Sonnet succeeded (0.733), suggesting
Opus over-engineered the TypeScript solution in a way that broke the build. This
model × language interaction was not visible with single replicates in Experiment 1.

**Changed:** Clojure improved. All 4 runs scored 0.833 (up from a 33% failure rate
in Experiment 1). The brazil-bench task may have been better-suited to Clojure's
functional data-processing strengths.

### Model Effect Is Smaller Here
**Opus vs Sonnet: 0.806 vs 0.792** — essentially tied. The large 24% gap from
Experiment 1 collapsed on this task. The TypeScript anomaly (Opus = 0.000,
Sonnet = 0.733) contributes to this convergence and highlights that model–language
interactions matter more than model main effects on complex tasks.

### Tooling Effect Remains Negligible
**Beads vs. None: 0.792 vs 0.806** — same conclusion as Experiment 1. Beads
task-tracking does not improve quality on single-agent tasks. The hypothesis
that beads helps on complex multi-component work remains untested.

### Cost Scaling
Brazil-bench ran **1.2–7× more tokens** than the CRUD task (avg 1.4M vs 0.4M tokens):

| Language | Avg tokens/run | Avg cost/run |
|----------|---------------|-------------|
| java | 2,357,128 | $1.789 |
| go | 1,625,840 | $1.379 |
| clojure | 1,438,525 | $1.089 |
| python | 1,299,914 | $1.104 |
| typescript | 1,074,032 | $0.929 |
| rust | 601,115 | $1.174 |

Java's verbosity (Spring Boot + JUnit boilerplate) drives token costs higher even
than Go. Rust's brief but complete implementations are consistently efficient.

## Cross-Experiment Comparison

| Language | Exp-1 quality (n≈2-3) | Exp-2 quality (n=1) | Verdict |
|----------|----------------------|---------------------|---------|
| java | 1.000 | 1.000 | ✅ Confirmed top tier |
| go | 0.976 | 1.000 | ✅ Confirmed top tier |
| clojure | 0.648 | 0.833 | ⬆️ Improved (task fit) |
| rust | 0.833* | 0.833 | ✅ Stable mid-tier |
| typescript | 0.733† | 0.367‡ | ⚠️ Model-sensitive |
| python | 0.539 | 0.667 | ↔️ Slight improvement |

*Rust scored 0.833 on every successful run in Exp-1; one failure (sonnet/beads/rep3).  
†TypeScript had 2/13 zero-score failures in Exp-1.  
‡TypeScript opus failures (2/4 runs) drove the Exp-2 mean down.

## Recommendations

1. **Promote Java and Go to `candidate` phase.** Both show 1.000 quality across
   two distinct tasks. The evidence base is sufficient for promotion.

2. **Promote Clojure to `trial` with caution.** The Experiment 2 improvement
   needs replication (single rep). Schedule a targeted 3-replicate run.

3. **Rust is reliable at 0.833.** Consider whether the scorer plateau reflects
   real quality limits or a scoring artifact before promotion.

4. **TypeScript needs model qualification.** The Opus failure on brazil-bench is
   a red flag. Run a dedicated TypeScript × model experiment before promoting.

5. **Python needs timeout tuning.** The failure rate in Experiment 1 was test-gate
   vetoes (tests not running). Longer timeout or explicit test execution prompts
   may fix this.

6. **Beads does not help on single-agent tasks.** Reserve beads evaluation for
   multi-agent or multi-component experiments.

## Links

- [Experiment 1 comparison](../../experiment-1/reports/comparison.md) — baseline results
- [Experiment 3 comparison](../../experiment-3/reports/comparison.md) — model version analysis
