# Retort

**Platform Evolution Engine** — Distill the best from the combinatorial mess.

Retort applies statistical Design of Experiments (DoE) to systematically evaluate AI-assisted development tooling stacks. It generates fractional factorial designs across languages, coding agents, and frameworks, executes experiments in isolated playpens, scores the results, and promotes or retires stacks based on measured confidence.

## Status: Active Development (Alpha)

> Retort is **pre-1.0 and under active development**. The CLI surface, scoring metrics, and storage schema may change between commits. The code is published so others can read it, fork it, and reproduce experiments — not yet as a stable tool to depend on.
>
> **What works today:** `LocalRunner`, all 8 built-in scorers (`code_quality`, `test_coverage`, `test_quality`, `defect_rate`, `maintainability`, `token_efficiency`, `idiomatic`, `findings`), fractional-factorial design generation, ANOVA + effects reporting, SQLite storage, resumable runs, parallel bulk evaluation (`retort evaluate --workers N`), and the `evaluate-run` skill pipeline that scores generated code against task requirements and produces per-run `evaluation.md`, `findings.jsonl`, and `assessment.json`.
>
> **What does not yet work end-to-end:** `DockerRunner` (skeleton only — `LocalRunner` is the supported path), agents other than `claude-code`, the `intake`/`scheduler` paths. See [Implementation Status](#implementation-status) for details.
>
> **Scoring gate:** A run where tests don't execute scores **0 across all metrics** — a Starlette-incompatible Python run that writes perfect code still fails if pytest can't import. `test_coverage == 0` vetoes the entire `ScoreVector`. The `findings` scorer reads `assessment.json` produced by the `evaluate-run` + `file-run-issues` skill pipeline and applies a weighted penalty for critical/high/medium/low findings.

## Experiment 1 Results

📊 **[Browse the live web report →](https://rawcdn.githack.com/adrianco/retort/main/experiment-1/reports/web/index.html)** (sortable leaderboard with per-stack drill-downs, token/cost data, and links to per-run code reviews)

Full data is also in [`experiment-1/reports/`](experiment-1/reports/) — ANOVA, per-stack maturity, full CSV, and the same static-HTML web report. Below is the headline.

**Setup:** 6 languages (python, typescript, go, rust, java, clojure) × 2 models (opus, sonnet) × 2 tooling (none, beads) × 3 replicates = 72 runs against the bundled `rest-api-crud` task. Java + clojure added in a follow-up extension run. **Final tally: 67 of 73 runs completed, 6 failed. Total cost ≈ $25, ≈ 25.8M tokens.**

**Evaluation scores** (from `retort evaluate` + `evaluate-run` skill, April 2026): `PenScore` = 1.0 minus weighted findings penalty (critical×0.25, high×0.10, medium×0.03, low×0.01); `ReqCov` = fraction of TASK.md requirements implemented. Runs where tests didn't execute score 0.

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

Sortable + drill-downable in the [web report](https://rawcdn.githack.com/adrianco/retort/main/experiment-1/reports/web/index.html). `PenScore` and `ReqCov` are from the April 2026 `evaluate-run` bulk evaluation. Bold = perfect penalty score.

| Language | Model | Tooling | n | Quality (mean) | Tokens (mean) | Cost (mean) | PenScore | ReqCov |
|---|---|---|---|---|---|---|---|---|
| clojure | opus | beads | 2/3 | 0.556 | 723,724 | $0.762 | **1.000** | 1.000 |
| clojure | opus | none | 3/3 | 0.833 | 409,366 | $0.579 | **1.000** | 1.000 |
| clojure | sonnet | beads | 3/3 | 0.556 | 722,939 | $0.520 | 0.830 | 0.939 |
| clojure | sonnet | none | 3/3 | 0.556 | 665,636 | $0.575 | 0.967 | 0.972 |
| go | opus | beads | 2/2 | 0.985 | 346,215 | $0.491 | **1.000** | 1.000 |
| go | opus | none | 2/2 | 0.963 | 230,498 | $0.361 | **1.000** | 1.000 |
| go | sonnet | beads | 2/2 | **1.000** | 476,955 | $0.311 | 0.995 | 0.500 |
| go | sonnet | none | 1/2 | 0.956 | 435,373 | $0.303 | **1.000** | 1.000 |
| java | opus | beads | 3/3 | **1.000** | 325,112 | $0.552 | **1.000** | 1.000 |
| java | opus | none | 2/3 | **1.000** | 217,162 | $0.436 | **1.000** | — |
| java | sonnet | beads | 2/3 | **1.000** | 611,395 | $0.365 | **1.000** | 1.000 |
| java | sonnet | none | 2/3 | **1.000** | 494,115 | $0.326 | **1.000** | 1.000 |
| python | opus | beads | 2/2 | 0.672 | 280,359 | $0.373 | **1.000** | 1.000 |
| python | opus | none | 2/2 | 0.789 | 91,698 | $0.203 | 0.500 | 0.727 |
| python | sonnet | beads | 1/2 | 0.696 | 436,753 | $0.262 | 0.400 | 0.800 |
| python | sonnet | none | 2/2 | 0.637 | 332,390 | $0.226 | 0.995 | 1.000 |
| rust | opus | beads | 3/3 | 0.833 | 355,099 | $0.481 | **1.000** | 1.000 |
| rust | opus | none | 2/3 | 0.833 | 150,702 | $0.331 | **1.000** | 0.500 |
| rust | sonnet | beads | 2/3 | 0.556 | 643,793 | $0.414 | **1.000** | 1.000 |
| rust | sonnet | none | 3/3 | 0.833 | 395,257 | $0.355 | **1.000** | 1.000 |
| typescript | opus | beads | 1/2 | 0.733 | 454,220 | $0.512 | **1.000** | 1.000 |
| typescript | opus | none | 2/2 | 0.733 | 168,703 | $0.319 | **1.000** | 1.000 |
| typescript | sonnet | beads | 2/3 | 0.550 | 637,682 | $0.381 | 0.900 | 0.950 |
| typescript | sonnet | none | 2/2 | 0.489 | 835,319 | $0.531 | 0.500 | 0.591 |

**Headlines:**
- **Java, Go, Rust, and Clojure/opus consistently hit PenScore 1.000** on this task — no findings above threshold.
- **Python is the outlier.** `python/opus/none` and `python/sonnet/beads` scored 0.50 and 0.40 due to a Starlette 1.0 compatibility break that prevented tests from executing (which zeroes all scores under the new test-gate rule). Other Python cells pass cleanly.
- **Requirement coverage diverges from penalty score.** `go/sonnet/beads` has PenScore 0.995 but ReqCov 0.500 — the code is high quality but only implements half the spec. The old `code_quality` scorer missed this.
- **Beads helps only for Go.** Pattern consistent with experiment-1 ANOVA findings.

## Experiment 2 Results — brazil-bench (cross-task)

📊 **[Web report →](https://rawcdn.githack.com/adrianco/retort/main/experiment-2/reports/web/index.html)**

A second experiment run against [`brazil-bench/benchmark-template`](https://github.com/brazil-bench/benchmark-template) — a much harder task: MCP server, CSV ingest of Kaggle data, BDD tests with 16 canonical requirements. **24 cells, 1 replicate each, screening pass.** Results combine with experiment-1 to give cross-task ANOVA insights.

**Single-task ANOVA on `code_quality`:** only language significant (consistent with experiment-1).

**Cross-task ANOVA** (89 rows = experiment-1's 67 + experiment-2's 22, `task` as a factor):

| Response | Significant factors |
|---|---|
| `code_quality` | language |
| `_tokens` | language + model + tooling + **task** + language:tooling + **language:task** + model:tooling + **model:task** |
| `_cost_usd` | similar + model:tooling |
| `_duration_seconds` | every main effect + 5 interactions (incl. **model:task**, **tooling:task**) |

**The `model:task` interaction is the headline finding.** Opus vs sonnet behaves *differently* on hard (brazil-bench) vs easy (rest-api-crud) tasks. The simple "best stack on rest-api-crud is best everywhere" assumption from experiment-1 doesn't fully generalize for the resource-cost dimensions.

### Experiment-2 evaluation scores (brazil-bench, April 2026)

`PenScore` and `ReqCov` from `evaluate-run` bulk evaluation. Brazil-bench is a harder task (MCP server + CSV ingest + BDD tests) so scores spread more widely.

| Language | Model | Tooling | PenScore | ReqCov | Notes |
|---|---|---|---|---|---|
| clojure | opus | beads | — | — | eval missed |
| clojure | opus | none | **1.000** | — | |
| clojure | sonnet | beads | **1.000** | 0.889 | |
| clojure | sonnet | none | **1.000** | — | |
| go | opus | beads | **1.000** | 1.000 | |
| go | opus | none | 0.620 | 0.667 | |
| go | sonnet | beads | 0.650 | 0.000 | 1 critical — BDD scaffold with no data |
| go | sonnet | none | 0.900 | 0.500 | |
| java | opus | beads | 0.940 | 0.900 | |
| java | opus | none | **1.000** | — | |
| java | sonnet | beads | **1.000** | 1.000 | |
| java | sonnet | none | 0.000 | 0.067 | **11 critical** — catastrophic failure |
| python | opus | beads | **1.000** | — | |
| python | opus | none | **1.000** | 1.000 | |
| python | sonnet | beads | **1.000** | — | |
| python | sonnet | none | **1.000** | 0.917 | |
| rust | opus | beads | 0.450 | 0.143 | 1 critical |
| rust | opus | none | 0.750 | — | 1 critical |
| rust | sonnet | beads | 0.400 | 0.143 | |
| rust | sonnet | none | 0.990 | 1.000 | |
| typescript | opus | beads | **1.000** | — | |
| typescript | opus | none | **1.000** | 1.000 | |
| typescript | sonnet | beads | — | — | eval missed |
| typescript | sonnet | none | **1.000** | 1.000 | |

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

For prediction of unmeasured cells (when running fewer cells of a fractional design), use `retort analyze --predict` — emits 95% CIs for cells you didn't run, fitted from cells you did.

## Installation

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

```bash
# Initialize a workspace
retort init my-eval
cd my-eval

# Edit workspace.yaml to define your factors, responses, and tasks
# Then generate a screening design matrix
retort design generate --phase screening --config workspace.yaml -o design.csv

# Execute experiment runs
retort run --phase screening --config workspace.yaml

# Compute main effects and interactions
retort report effects --db retort.db --matrix-id 1 --metric code_quality

# Evaluate a promotion gate
retort promote my-stack --from screening --to trial \
    --evidence '{"p_value": 0.05}' --config workspace.yaml
```

## Running at scale with Gas Town (optional)

Retort runs standalone — `pip install` + `claude` CLI is enough to drive every command above. There is **no Gas Town dependency**.

That said, real experiments are long-running, parallelizable, and benefit from an orchestrator. [Gas Town](https://github.com/steveyegge/gastown) is the orchestrator we use during development; it adds:

- **Parallel execution.** `gt sling` dispatches a slice of the design to a polecat (a worker agent in its own git worktree). Multiple polecats share one `retort.db` via `retort run --shard N/M --resume`. The `--shard` partition is a deterministic hash, so two polecats never both pick the same cell, and per-run sqlite commits keep concurrent writers safe.
- **Patrol + escalation.** `witness` watches the merge queue; `refinery` patrols it; mail/escalations route to the mayor agent if anything sticks.
- **Auto-evaluation.** With gt + `bd` (beads) installed, the `evaluate-run` and `file-run-issues` skills file findings as tracked beads in your project — survives session resets and shows up in queries.

Pattern:

```bash
gt sling re-ucc retort --crew alpha   --args "retort run --phase screening --config experiment-2/workspace.yaml --resume --shard 0/4"
gt sling re-ucc retort --crew bravo   --args "retort run --phase screening --config experiment-2/workspace.yaml --resume --shard 1/4"
gt sling re-ucc retort --crew charlie --args "retort run --phase screening --config experiment-2/workspace.yaml --resume --shard 2/4"
gt sling re-ucc retort --crew delta   --args "retort run --phase screening --config experiment-2/workspace.yaml --resume --shard 3/4"
```

**Without Gas Town, the same parallelism works in plain bash:**

```bash
for s in 0 1 2 3; do
    nohup retort run --phase screening --config experiment-2/workspace.yaml \
        --resume --shard $s/4 > shard-$s.log 2>&1 &
done
wait
```

**Caveats if you choose the gt path:**

- Some current gt 0.12.0 rough edges (project-id mismatches, missing `bd agent` subcommand, `gt dolt fix-metadata` vs `rig-config-sync` disagreement) are documented in `re-o5b` in the beads tracker. None block work; they produce noisy telemetry warnings.
- Concurrent runs multiply per-second token usage. Keep the shard count to a value the Anthropic API tier comfortably supports — start at 2× and monitor rate-limit headers before going higher.

## CLI Commands

| Command | Description |
|---------|-------------|
| `retort init <name>` | Create a new workspace with config template and SQLite database |
| `retort design generate` | Generate a fractional factorial design matrix (screening or characterization) |
| `retort run` | Execute experiment runs: design matrix, playpen provisioning, scoring, storage |
| `retort promote` | Evaluate promotion gates for stack lifecycle transitions |
| `retort report effects` | Compute and export main effects and interaction effects (text, JSON, CSV) |
| `retort export csv` | Export experiment runs + scores to CSV for `retort analyze` and external tools |
| `retort maturity` | Score each stack's maturity (replicate agreement, completion rate, score level, coverage) and suggest a lifecycle phase |
| `retort report web` | Generate static HTML reports (sortable leaderboard + per-stack drill-downs); respects experiment.visibility for private experiments |
| `retort export merge` | Combine multiple experiment CSVs into one with an experiment-tag column, for cross-experiment ANOVA |
| `retort report pareto` | Identify Pareto-optimal stacks across multiple objectives; minimize cost-like metrics with `-` prefix |
| `retort run --shard N/M` | Run only the slice of cells owned by shard N (of M); deterministic partition for parallel polecats sharing one retort.db |
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

design:
  screening_resolution: 3
  significance_threshold: 0.10

promotion:
  screening_to_trial: { p_value: 0.10 }
  trial_to_production: { posterior_confidence: 0.80 }
```

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
- **Playpen**: Isolated Docker environment where each experiment run executes
- **Scoring**: Pluggable metrics collected from run artifacts
- **Promotion**: Evidence-based lifecycle transitions (candidate → screening → trial → production → retired)

## Implementation Status

Honest accounting. "Code exists" ≠ "tested end-to-end against real data."

| Phase | Status | Notes |
|-------|--------|-------|
| **Phase 0: Skeleton** | ✅ Working | Project structure, Pydantic config schema, factor registry, fractional-factorial design generation, SQLite/SQLAlchemy storage, `retort init`, `retort design generate`. Covered by unit tests. |
| **Phase 1: Playpen + Scoring** | ✅ Working | `LocalRunner` exercised end-to-end against `rest-api-crud` and `brazil-bench`. All 8 scorers implemented and exercised: `code_quality`, `test_coverage`, `test_quality` (BDD bonus), `token_efficiency`, `defect_rate`, `maintainability`, `idiomatic`, `findings` (reads `assessment.json` from `evaluate-run` skill). **Scoring gate:** `test_coverage == 0` vetoes all scores. `evaluate-run` + `file-run-issues` skills wired into `retort run` and bulk `retort evaluate --workers N`. **`DockerRunner` is still a skeleton.** |
| **Phase 2: Promotion + Reporting** | 🟡 Code present, lightly exercised | Lifecycle state machine, promotion gates, changelog, multi-format export, `retort promote`, `retort report effects` exist and unit-test. Not yet run on a real promotion decision. |
| **Phase 3: Analysis** | 🟡 Code present, lightly exercised | ANOVA + residual diagnostics (statsmodels), Bayesian conjugate-NIG updating (scipy), Pareto frontier, `retort analyze`. Verified on synthetic data; not yet on a complete experiment-1 dataset with replicates. |
| **Phase 4: Polish** | 🟡 Mostly working | D-optimal augmentation + candidate intake (`retort intake`), pluggy plugin system, status dashboard, Pareto frontier (`retort report pareto`), promotion gates (`retort promote`) all exercised against real data. Scheduler/budget tracking still inert (no `cost_limit_usd` enforcement); Wardley overlay + aliasing reports exist but minimally verified. |
| **Resume / archive** | ✅ Working | `retort run --resume` skips already-recorded `(config, replicate)` pairs; `--retry-failed` retries failed ones. Each run's `/tmp` workspace is copied to `<workspace>/runs/<cell>/rep<N>/` before teardown so artifacts survive interrupts and `/tmp` cleanup. Per-run DB commit means an interrupt loses at most one run. |

### Known gaps and bugs

- `DockerRunner` not validated — use `runner: local` in `workspace.yaml` for now
- Only `claude-code` is wired up as an agent
- `idiomatic` scorer makes a Claude haiku call per run (~$0.001/run); cached per workspace in `.idiomatic_cache.json`
- `retort intake` / D-optimal augmentation untested against a real candidate
- Bundled tasks `cli-data-pipeline` and `react-dashboard` exist but haven't been run end-to-end
- `evaluate-run` skill timeout is 600s per run (evaluate + file-run-issues chained in one call); runs on very large codebases may hit the limit
- 8 of 61 experiment-1 runs and 2 of 24 experiment-2 runs missed evaluation (rc=143 SIGTERM under load from concurrent haiku workers) — re-run with `retort evaluate --workers 2` on the missing runs

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
