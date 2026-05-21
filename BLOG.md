# Measuring AI Coding Assistants Scientifically: What We Learned Running 111 Experiments

*May 2026 — Adrian Cockcroft*

---

When evaluating AI coding assistants, most teams rely on developer intuition, cherry-picked demos, or single-task benchmarks run once. We wanted something better: a systematic, reproducible, statistically-grounded method that could tell us *which combination of language, model, and tooling actually produces the best code* — and by how much.

That's why we built **Retort**: a Design of Experiments platform for AI-assisted development. This post describes what we built, how we ran three connected experiments totaling 111 runs and $110 in API costs, and what we found.

## The Core Insight: DoE for AI Evaluations

Statistical **Design of Experiments** (DoE) was developed in the 1920s for agricultural research — Fisher wanted to know which soil treatments, fertilizers, and plant varieties maximized crop yield. The insight was that you couldn't just vary one factor at a time; you needed to vary everything simultaneously in a structured way to detect interactions.

The same problem applies to AI coding stacks. The question isn't "is Go better than Python?" — it's "which combination of language + model + tooling + task is better, and why?" A single benchmark run can't answer that. A full factorial experiment (every combination × multiple replicates) is too expensive. DoE's **fractional factorial designs** give you statistically valid answers at a fraction of the cost.

Retort automates this workflow:
1. Define your factors (language, model, tooling) and their levels (go/python/java, opus/sonnet, beads/none)
2. Generate an efficient design matrix (full factorial or quarter-fraction)
3. Execute experiment runs in isolated "playpens" using the Claude Code CLI
4. Score the outputs with 8 built-in metrics
5. Run ANOVA to identify which factors are statistically significant
6. Promote or retire stacks based on measured confidence

## What We Measured

Every experiment run produces a complete source code implementation of a specified task. Retort's scoring pipeline evaluates the output on 8 dimensions:

- **`code_quality`** — the headline metric: 1.0 minus a weighted penalty for high-severity findings from a LLM-based code reviewer (`evaluate-run` skill). A critical finding costs 0.25; a high finding 0.10.
- **`test_coverage`** — actual line coverage percentage from pytest-cov, go test -cover, cargo-llvm-cov, etc. A score of 0 here vetoes all other metrics (the "test gate").
- **`test_quality`** — detects and rewards BDD test patterns (Given/When/Then scenarios) with a bonus over plain unit tests.
- **`defect_rate`** — fraction of runs that fail to build or test at all. Lower is better.
- **`maintainability`** — LLM assessment of code maintainability (cyclomatic complexity, SOLID principles, documentation quality).
- **`idiomatic`** — how well the code uses language-specific idioms and conventions.
- **`token_efficiency`** — output tokens / input tokens ratio (cost efficiency proxy).
- **`findings`** — count-weighted severity score from the code review skill.

The **test gate** is important: if a run produces code where tests can't execute (import errors, missing dependencies, compilation failures), the entire score vector zeroes out. This prevents gaming the quality scorer with impressive-looking but non-functional code.

## Experiment 1: Baseline Language Comparison

**Task:** REST API CRUD — a book collection API with SQLite, CRUD endpoints, and validation. A realistic but simple backend service.

**Design:** 6 languages × 2 models × 2 tooling = 24 cells, 2–3 replicates each = 73 runs.

**Cost:** $25.07 / 25.8M tokens.

The headline finding was stark: **language dominates everything else**. ANOVA on `code_quality` found only language significant (p < 1e-18). Model and tooling effects were statistically indistinguishable from noise for this metric.

The language ranking:

| Language | Mean quality | Notes |
|----------|-------------|-------|
| Java | **1.000** | Perfect across all 12 runs, zero failures |
| Go | **0.976** | Tight variance, 0.889–1.000 |
| Rust | 0.833 | Consistent on every successful run |
| TypeScript | 0.733 | Consistent when working; 2/13 failures |
| Clojure | 0.648 | Bimodal: either 0.833 or 0.000 |
| Python | 0.539 | Highest variance; most 0.000 failures |

Java's dominance has a structural explanation: Spring Boot + JUnit + JaCoCo provides a complete, scaffolded ecosystem that the agent rarely misses. The task requirements map almost 1:1 to Spring conventions. The agent can follow the well-worn path without structural decisions.

Go's near-perfect score reflects similar scaffolding: `go mod init`, `go test ./...`, and the language's simplicity make it hard to produce non-functional code.

Python's variance tells a different story: permissive syntax and multiple valid project structures mean the agent makes different structural choices each run. Some work perfectly; others hit Starlette 1.0 compatibility issues that prevent test execution and trigger the test gate veto.

**Model effect:** Opus outscored Sonnet (0.810 vs 0.651), but this gap came primarily from different failure rates — Sonnet more often produced non-functional code — not from worse code on successful runs. For quality-critical work, Opus is worth the cost premium.

**Tooling effect:** Beads vs. no beads — essentially zero difference (0.715 vs 0.744). Task-tracking assistance doesn't improve code quality on simple single-file projects.

## Experiment 2: Cross-Task Validation (Brazil Bench)

We'd measured quality on one task. But do these rankings hold for harder, more realistic work?

**Task:** Brazilian Soccer MCP Guide — an MCP server that ingests Kaggle CSV data and exposes soccer statistics through a Model Context Protocol interface with 16 canonical BDD requirements.

This is genuinely hard. The agent needs to parse CSVs, build a query layer, implement MCP protocol scaffolding, and write Cucumber/pytest-bdd tests that match specified scenarios. The breadth of cross-cutting concerns tests planning ability, not just syntax knowledge.

**Design:** 24 cells (same 6×2×2 factorial), 1 replicate each, screening pass.

**Cost:** $29.85 / 33.6M tokens (1.2× more tokens per run than experiment 1).

The language hierarchy held at the top — **Java and Go both scored 1.000** — but the middle shifted:

| Finding | Experiment 1 | Experiment 2 |
|---------|-------------|-------------|
| TypeScript | 0.733 (reliable) | **0.367** (Opus failures) |
| Clojure | 0.648 (50% failure rate) | **0.833** (all succeed) |
| Python | 0.539 (test gate issues) | **0.667** (Starlette fixed) |

The most important finding was a **model × task interaction**. On the simple CRUD task, Opus and Sonnet performed similarly (failure mode differences). On the harder MCP task, TypeScript/Opus produced broken builds across both tooling conditions — Sonnet did not. This interaction means "Opus is always better" is wrong: model × language × task combinations matter.

The cross-task ANOVA (91 rows pooling both experiments) found `model:task` as a significant interaction — validating that results from one task don't cleanly generalize.

**Pareto frontier:** Across both tasks, only `go/sonnet/beads` was Pareto-optimal (no other stack beats it on both quality AND cost simultaneously). Java/sonnet/none was rank 1.

## Experiment 3: Model Version Comparison (Opus-4.6 vs Opus-4.7)

By the time we ran experiment 3, `claude-opus-4-7` had launched. We wanted to know: does the newer model produce better code?

Simple question, tricky answer. You can't just run both models on every cell — that doubles the experiment cost. Instead, we used a **Resolution III quarter-fraction**: 6 of 24 cells, each language assigned to one model version. This gives us a main effect estimate for model version, aliased with higher-order interactions.

**Design:** 6 cells × 2 replicates = 12 planned slots (14 actual runs; 2 cells needed an extra replicate due to a timeout).

**Cost:** $54.94 / 52.2M tokens. **This is 3.3× more expensive per run than experiment 2.**

The cost jump came from adaptive timeouts. The system learned from experiment 2 timing data and allocated longer budgets for compiled languages: Go and Rust got 45-minute windows instead of 25 minutes. The agent used that time — and produced substantially more tests.

**Model version findings:**

- **Go + opus-4.7: 81% test coverage vs 42% for opus-4.6** on the same task. Code quality was identical (1.000). The newer model wrote more thorough test suites when given the time.
- **Java and Rust: 100% coverage regardless of model version.** The language ecosystem scaffolding is so strong that model version doesn't matter much here.
- **Model quality is stable across time:** Python and Java cells run in May 2026 with opus-4.6 scored identically to April runs — no quality regression.

## The Infrastructure: How Retort Works

Running 111 experiments required robust tooling. Here's how Retort handles the practical challenges:

**Parallelism via sharding.** `retort run --shard 2/4` runs only the cells owned by shard 2 of 4. Ownership is a deterministic hash of `(config_key, replicate)` — two polecats never pick the same cell. All shards write to the same SQLite file; per-run commit ensures at most one lost run on crash.

**Gas Town orchestration.** We ran experiments using [Gas Town](https://github.com/steveyegge/gastown), an AI-agent orchestration system where "polecats" (worker agents) each own a git worktree. The mayor (coordinator) dispatches runs, monitors progress, handles failures, and manages the merge queue. Four polecats working in parallel completed experiment 3 in a few hours instead of a day.

**Adaptive timeouts.** `_estimate_run_timeout` queries the database for historical timing on the same cell and sets the next timeout to 1.5× the prior run's 90th-percentile duration. Languages like Rust that compile from scratch get longer budgets; quick Python runs get shorter ones. This dramatically reduced wasted compute from conservative fixed timeouts.

**Auto-evaluation.** After each successful run, Retort automatically invokes the `evaluate-run` skill (a Claude invocation that reads the generated code and TASK.md and produces findings). When the `file-run-issues` skill is also present, both are chained into a single cold-start — one Claude invocation instead of two. Results are archived alongside the source code.

**Cost enforcement.** The `cost_limit_usd` config field enforces a hard budget cap during runs. When accumulated cost across all shards exceeds the limit, `retort run` aborts with a clear error. This prevents runaway experiments from surprising you with a large API bill.

## Scorer Engineering

Getting scoring right was harder than getting experiments right.

**The test gate.** Early experiments showed that code quality scores were meaningless when tests didn't execute. A sophisticated implementation of a broken dependency graph looks impressive but fails functionally. We added a veto: `test_coverage == 0` sets all metrics to zero. This changed experiment 1's rankings significantly — Python's "successful" runs with 0% coverage were revealed as failures.

**Language-specific coverage.** Each language needs a different coverage toolchain:
- Python: `pytest --cov=. --cov-report=term`
- Go: `go test -cover ./...` (parse per-package percentages, take mean)
- TypeScript: detect jest vs vitest from `package.json`, invoke appropriately
- Java: `mvn test jacoco:report` (with fallback to plain `mvn test` + pass rate)
- Rust: `cargo-llvm-cov` if available, else `cargo test` + pass rate
- Clojure: `clojure -M:test` (the `-X:test` exec-fn alias that agents sometimes use doesn't produce test output Retort can parse)

We fixed four scorer bugs during experiment 3 and applied the fixes retroactively across all experiments:
1. Java's `-q` (quiet) flag silenced Surefire test output — removed
2. Clojure's test alias was `-X:test` (exec-fn) instead of `-M:test` (main-opts) — fixed
3. Rust had no coverage path — added tests-only fallback with pass rate
4. TypeScript's vitest invocation via `.bin/` wrapper failed outside `node_modules/.bin/` — switched to direct `node dist/cli.js` invocation

## What the Numbers Tell Us

Across three experiments, some patterns hold consistently:

**Java and Go are production-ready for AI-assisted development.** Both achieve 1.000 quality across two very different tasks (simple CRUD and complex MCP server) with multiple model/tooling combinations. The evidence base is strong enough for automated promotion.

**Language matters more than model.** ANOVA consistently finds language as the dominant factor for `code_quality`. Switching from Sonnet to Opus (2× price) gives you less improvement than switching from Python to Go. Choose your language ecosystem carefully.

**Task difficulty changes rankings.** TypeScript's Opus failures on brazil-bench didn't appear in experiment 1. Single-task benchmarks miss model × language × task interactions that only become visible across multiple tasks.

**Beads task-tracking doesn't help single-agent CRUD.** The tooling effect was statistically insignificant across both tasks and both models. This doesn't mean beads is useless — it means it's solving a different problem (multi-step coordination) that our tasks didn't exercise.

**Newer models write more tests.** Opus-4.7's biggest measurable improvement over opus-4.6 was test coverage, not code quality. For quality benchmarks that don't measure tests, this difference is invisible. For real-world code that you'll rely on, it matters.

## What's Next

Retort 1.0 beta is the platform we built to answer these questions. The experiments above represent what we actually know — not what we hope or assume. The ranking of Java > Go > Rust > TypeScript > Clojure > Python is a measurement, not an opinion.

We're planning:
- **Experiment 4:** Claude-sonnet-4-6 vs newer Sonnet releases on the same brazil-bench task
- **Experiment 5:** Multi-agent tooling (beads vs cursor vs copilot) on complex multi-component tasks where coordination assistance actually matters
- **Longer tasks:** The MCP server task took 10–45 minutes. We want to measure quality on day-long or week-long projects where planning and context management become limiting factors

If you want to run your own experiments — different languages, different tasks, different agents — Retort is [open source](https://github.com/adrianco/retort). The quick start is genuinely quick: `pip install`, `retort init`, edit `workspace.yaml`, `retort run`.

The combinatorial mess of AI-assisted development is real. Measuring it systematically is the only way out.

---

*Retort is Apache-2.0 licensed. All experiment data, per-run code archives, and evaluation reports are in the repository.*
