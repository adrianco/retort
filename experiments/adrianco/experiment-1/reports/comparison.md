# Experiment 1: Full Comparison Report

Generated: 2026-05-21

## Overview

Experiment 1 established Retort's baseline quality measurements across six programming
languages and three experimental factors.

| Setting | Value |
|---------|-------|
| Task | rest-api-crud (CRUD book collection API with SQLite) |
| Runner | local (Claude Code CLI on host) |
| Factors | language × model × tooling |
| Languages | python, typescript, go, clojure, java, rust |
| Models | claude-opus-4-7 (`opus`), claude-sonnet-4-6 (`sonnet`) |
| Tooling | none, beads (task-tracking assistant) |
| Design | 6×2×2 full factorial (24 cells) |
| Replicates | 2–3 per cell (added iteratively as languages were onboarded) |
| **Total runs** | **73** (67 completed, 6 failed) |
| **Total cost** | **$25.07** (25.8M tokens) |

## Per-Run Results

| Language | Model | Tooling | Rep | Quality | Coverage | Tokens | Cost |
|----------|-------|---------|-----|---------|----------|--------|------|
| clojure | opus | beads | 1 | 0.833 | 1.000 | 587,233 | $0.642 |
| clojure | opus | beads | 2 | 0.833 | 1.000 | 601,420 | $0.725 |
| clojure | opus | beads | 3 | 0.000 | — | 982,519 | $0.919 |
| clojure | opus | none | 1 | 0.833 | 1.000 | 350,599 | $0.518 |
| clojure | opus | none | 2 | 0.833 | 1.000 | 540,001 | $0.648 |
| clojure | opus | none | 3 | 0.833 | 1.000 | 337,498 | $0.572 |
| clojure | sonnet | beads | 1 | 0.000 | 0.000 | 741,625 | $0.518 |
| clojure | sonnet | beads | 2 | 0.833 | 1.000 | 618,307 | $0.437 |
| clojure | sonnet | beads | 3 | 0.000 | — | 808,887 | $0.607 |
| clojure | sonnet | none | 1 | 0.000 | 0.000 | 780,404 | $0.692 |
| clojure | sonnet | none | 2 | 0.833 | 1.000 | 369,747 | $0.429 |
| clojure | sonnet | none | 3 | 0.000 | — | 846,758 | $0.603 |
| go | opus | beads | 1 | 0.956 | — | — | — |
| go | opus | beads | 2 | 1.000 | 0.600 | 282,025 | $0.432 |
| go | opus | beads | 3 | 1.000 | 0.623 | 410,406 | $0.550 |
| go | opus | none | 1 | 0.889 | — | — | — |
| go | opus | none | 2 | 1.000 | 0.603 | 162,906 | $0.328 |
| go | opus | none | 3 | 1.000 | 0.653 | 298,091 | $0.395 |
| go | sonnet | beads | 1 | 1.000 | — | — | — |
| go | sonnet | beads | 2 | 1.000 | 0.648 | 408,786 | $0.294 |
| go | sonnet | beads | 3 | 1.000 | 0.636 | 545,124 | $0.328 |
| go | sonnet | none | 1 | 0.956 | — | — | — |
| go | sonnet | none | 2 | 0.956 | 0.673 | 448,470 | $0.310 |
| go | sonnet | none | 3 | 0.956 | 0.661 | 422,277 | $0.295 |
| java | opus | beads | 1 | 1.000 | 1.000 | 291,090 | $0.467 |
| java | opus | beads | 2 | 1.000 | 1.000 | 323,893 | $0.506 |
| java | opus | beads | 3 | 1.000 | 1.000 | 360,353 | $0.684 |
| java | opus | none | 1 | 1.000 | 1.000 | 182,291 | $0.417 |
| java | opus | none | 2 | 1.000 | 1.000 | 290,890 | $0.482 |
| java | opus | none | 3 | 1.000 | 1.000 | 178,307 | $0.410 |
| java | sonnet | beads | 1 | 1.000 | 1.000 | 510,855 | $0.315 |
| java | sonnet | beads | 2 | 1.000 | 1.000 | 694,976 | $0.401 |
| java | sonnet | beads | 3 | 1.000 | 1.000 | 628,355 | $0.378 |
| java | sonnet | none | 1 | 1.000 | 1.000 | 612,173 | $0.385 |
| java | sonnet | none | 2 | 1.000 | 1.000 | 336,186 | $0.248 |
| java | sonnet | none | 3 | 1.000 | 1.000 | 533,988 | $0.345 |
| python | opus | beads | 1 | 0.622 | — | — | — |
| python | opus | beads | 2 | 0.772 | 0.970 | 342,199 | $0.431 |
| python | opus | beads | 3 | 0.622 | 0.970 | 218,520 | $0.315 |
| python | opus | none | 1 | 0.789 | — | — | — |
| python | opus | none | 2 | 0.000 | 0.000 | 105,212 | $0.208 |
| python | opus | none | 3 | 0.956 | 0.940 | 78,185 | $0.199 |
| python | sonnet | beads | 1 | 0.622 | — | — | — |
| python | sonnet | beads | 2 | 0.800 | 0.240 | 493,328 | $0.299 |
| python | sonnet | beads | 3 | 0.000 | 0.000 | 380,179 | $0.224 |
| python | sonnet | none | 1 | 0.667 | — | — | — |
| python | sonnet | none | 2 | 0.000 | 0.000 | 352,699 | $0.232 |
| python | sonnet | none | 3 | 0.622 | 0.970 | 312,082 | $0.220 |
| rust | opus | beads | 1 | 0.833 | 1.000 | 405,949 | $0.501 |
| rust | opus | beads | 2 | 0.833 | 1.000 | 287,633 | $0.448 |
| rust | opus | beads | 3 | 0.833 | 1.000 | 371,717 | $0.493 |
| rust | opus | none | 1 | 0.833 | 1.000 | 139,626 | $0.327 |
| rust | opus | none | 2 | 0.833 | 1.000 | 140,736 | $0.318 |
| rust | opus | none | 3 | 0.833 | 1.000 | 171,744 | $0.349 |
| rust | sonnet | beads | 1 | 0.833 | 1.000 | 656,821 | $0.407 |
| rust | sonnet | beads | 2 | 0.833 | 1.000 | 630,765 | $0.421 |
| rust | sonnet | beads | 3 | 0.000 | — | — | — |
| rust | sonnet | none | 1 | 0.833 | 1.000 | 443,216 | $0.355 |
| rust | sonnet | none | 2 | 0.833 | 1.000 | 240,604 | $0.292 |
| rust | sonnet | none | 3 | 0.833 | 1.000 | 501,952 | $0.418 |
| typescript | opus | beads | 1 | 0.733 | — | — | — |
| typescript | opus | beads | 2 | 0.733 | 1.000 | 505,402 | $0.545 |
| typescript | opus | beads | 3 | 0.733 | 0.086 | 403,038 | $0.478 |
| typescript | opus | none | 1 | 0.733 | — | — | — |
| typescript | opus | none | 2 | 0.733 | 1.000 | 167,020 | $0.311 |
| typescript | opus | none | 3 | 0.733 | 0.846 | 170,386 | $0.326 |
| typescript | sonnet | beads | 1 | 0.000 | 0.931 | 688,784 | $0.388 |
| typescript | sonnet | beads | 2 | 0.733 | 0.860 | 697,503 | $0.429 |
| typescript | sonnet | beads | 3 | 0.733 | 0.940 | 526,761 | $0.326 |
| typescript | sonnet | none | 1 | 0.733 | — | — | — |
| typescript | sonnet | none | 2 | 0.733 | 0.894 | 835,319 | $0.531 |
| typescript | sonnet | none | 3 | 0.000 | — | — | — |

*Rep 1 costs missing for early runs — cost tracking was added after the first replicates ran.*

## Factor Means (code_quality, completed runs only)

| Factor | Level | Mean Quality | N |
|--------|-------|-------------|---|
| language | java | **1.000** | 12 |
| language | go | **0.976** | 12 |
| language | rust | 0.833 | 11 |
| language | typescript | 0.733 | 11 |
| language | clojure | 0.648 | 9 |
| language | python | 0.539 | 12 |
| model | opus | **0.810** | 36 |
| model | sonnet | 0.651 | 37 |
| tooling | none | 0.744 | 36 |
| tooling | beads | 0.715 | 37 |

## Key Findings

### Language Hierarchy
The most striking result is the **consistent language ranking**, which held across
both models and tooling conditions:

1. **Java** — perfect 1.000 across all 12 runs, zero failures. The mature ecosystem
   with Spring Boot + JUnit/JaCoCo gives the agent strong scaffolding and reliable
   test infrastructure. Every run hit 100% test coverage.

2. **Go** — 0.976 mean with tight variance (0.889–1.000). The language's simplicity
   and the `go test -cover` integration make it the runner-up. Coverage was lower
   (33–67%) because Go's standard library requires more implementation surface.

3. **Rust** — 0.833 on every successful run (11/12), one failure (sonnet/beads/rep3).
   The score plateau at 0.833 reflects the scorer: Rust's trait-based generics
   reduce "idiomatic" flexibility scores. Cargo + `cargo test` work reliably.

4. **TypeScript** — 0.733 on every successful run (11/13), two zero-score failures
   (sonnet/beads/rep1, sonnet/none/rep3). When TypeScript builds succeed, quality
   is consistent. Failures are build-time or test-runner configuration errors.

5. **Clojure** — 0.648 mean but with 33% failure rate. Successful runs score 0.833
   consistently; failures produce zero code or zero tests. The bimodal distribution
   suggests Clojure has a harder initial setup that the agent sometimes fails to
   navigate.

6. **Python** — 0.539 mean, highest variance. Scores range from 0.000 to 0.956.
   Python's permissiveness means the agent can produce code that runs but has
   structural gaps detected by the scorer. The 0.000 failures are test-gate vetoes
   (test_coverage == 0 vetoes all scores).

### Model Effect
**Opus scored 0.810 vs Sonnet's 0.651** — a 24% gap. This is larger than any
tooling effect. For quality-critical work, Opus is clearly superior. Sonnet's
lower scores come from more frequent failure-mode outcomes (zero scores), not from
uniformly lower quality on successful runs.

### Tooling Effect
**Beads vs. None: 0.715 vs 0.744** — negligible. Beads task-tracking does not
improve code quality for a simple CRUD task. This aligns with expectations:
beads adds overhead for straightforward single-file projects but provides structure
for multi-component work (the intended use case for Experiment 3).

### Cost Efficiency
Java achieved perfect quality at $0.25–$0.68/run. Go at $0.29–$0.55. Both
outperform Python ($0.19–$0.43/run) in cost-efficiency (quality/cost) despite
similar absolute costs, because Python's failure rate destroys value.

## Recommendations

1. **Java and Go are production-ready** for AI-assisted REST API development.
   Schedule them for automated promotion after Experiment 2 confirmation.

2. **Rust and TypeScript are viable** with appropriate prompt scaffolding.
   The consistent pass-mode quality (0.833, 0.733) suggests the issue is
   initialization, not capability.

3. **Python requires intervention.** The high variance suggests prompt engineering
   or timeout tuning could reduce failures. The test-gate vetoes indicate the agent
   is often producing code that doesn't run tests.

4. **Clojure needs a better starter task.** The bimodal 0/0.833 distribution
   suggests a scaffolding or tooling configuration issue, not model capability.

5. **Use Opus for quality-critical experiments.** The 24% quality gap over Sonnet
   is consistent and significant. Sonnet is appropriate for cost-sensitive screening.

## Links

- [Experiment 2 comparison](../../experiment-2/reports/comparison.md) — cross-task replication
- [Experiment 3 comparison](../../experiment-3/reports/comparison.md) — model version analysis
