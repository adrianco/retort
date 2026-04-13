# Retort

**Platform Evolution Engine** — Distill the best from the combinatorial mess.

Retort applies statistical Design of Experiments (DoE) to systematically evaluate AI-assisted development tooling stacks. It generates fractional factorial designs across languages, coding agents, and frameworks, executes experiments in isolated playpens, scores the results, and promotes or retires stacks based on measured confidence.

## Status: Active Development (Alpha)

> Retort is **pre-1.0 and under active development**. The CLI surface, scoring metrics, and storage schema may change between commits. The code is published so others can read it, fork it, and reproduce experiments — not yet as a stable tool to depend on.
>
> **What works today:** `LocalRunner` (executes the `claude` CLI on the host), 3 built-in scorers (`code_quality`, `build_time`, token/cost capture), fractional-factorial design generation, ANOVA + effects reporting, SQLite storage, and resumable runs (`retort run --resume`) with per-run workspace archival.
>
> **What does not yet work end-to-end:** `DockerRunner` (skeleton only — `LocalRunner` is the supported path), agents other than `claude-code`, the `intake`/`scheduler` paths, and the `bundled://` task sources beyond `rest-api-crud`. See [Implementation Status](#implementation-status) for details.
>
> **Currently in flight:** Experiment 1 is being re-run with `replicates: 3` to get past the n=1 results below. Rust was added as a fourth language. Results will replace the table when the run completes.

## Experiment 1 Results

📊 **[Browse the live web report →](https://rawcdn.githack.com/adrianco/retort/main/experiment-1/reports/web/index.html)** (sortable leaderboard with per-stack drill-downs, token/cost data, and links to per-run code reviews)

Full data is also in [`experiment-1/reports/`](experiment-1/reports/) — ANOVA, per-stack maturity, full CSV, and the same static-HTML web report. Below is the headline.

**Setup:** 6 languages (python, typescript, go, rust, java, clojure) × 2 models (opus, sonnet) × 2 tooling (none, beads) × 3 replicates = 72 runs against the bundled `rest-api-crud` task. Java + clojure added in a follow-up extension; first 4 languages still have their original replicates.

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

Sortable + drill-downable in the [web report](https://rawcdn.githack.com/adrianco/retort/main/experiment-1/reports/web/index.html). Bold quality means perfect 1.000.

| Language | Model | Tooling | n | Quality (mean) | Tokens (mean) | Cost (mean) | Duration (mean) |
|---|---|---|---|---|---|---|---|
| clojure | opus | beads | 2/3 | 0.556 | 723,724 | $0.762 | 201s |
| clojure | opus | none | 3/3 | 0.833 | 409,366 | $0.579 | 179s |
| clojure | sonnet | beads | 2/2 | 0.833 | 679,966 | $0.477 | 230s |
| clojure | sonnet | none | 2/3 | 0.556 | 665,636 | $0.575 | 310s |
| go | opus | beads | 3/3 | 0.985 | 346,215 | $0.491 | 117s |
| go | opus | none | 3/3 | 0.963 | 230,498 | $0.361 | 94s |
| go | sonnet | beads | 3/3 | **1.000** | 476,955 | $0.311 | 147s |
| go | sonnet | none | 3/3 | 0.956 | 435,373 | $0.303 | 123s |
| java | opus | beads | 3/3 | **1.000** | 325,112 | $0.552 | 150s |
| java | opus | none | 3/3 | **1.000** | 217,162 | $0.436 | 131s |
| java | sonnet | beads | 3/3 | **1.000** | 611,395 | $0.365 | 182s |
| java | sonnet | none | 3/3 | **1.000** | 494,115 | $0.326 | 152s |
| python | opus | beads | 3/3 | 0.672 | 280,359 | $0.373 | 79s |
| python | opus | none | 3/3 | 0.789 | 91,698 | $0.203 | 44s |
| python | sonnet | beads | 3/3 | 0.696 | 436,753 | $0.262 | 110s |
| python | sonnet | none | 3/3 | 0.637 | 332,390 | $0.226 | 74s |
| rust | opus | beads | 3/3 | 0.833 | 355,099 | $0.481 | 143s |
| rust | opus | none | 3/3 | 0.833 | 150,702 | $0.331 | 106s |
| rust | sonnet | beads | 2/3 | 0.556 | 643,793 | $0.414 | 208s |
| rust | sonnet | none | 3/3 | 0.833 | 395,257 | $0.355 | 194s |
| typescript | opus | beads | 3/3 | 0.733 | 454,220 | $0.512 | 219s |
| typescript | opus | none | 3/3 | 0.733 | 168,703 | $0.319 | 181s |
| typescript | sonnet | beads | 3/4 | 0.550 | 637,682 | $0.381 | 168s |
| typescript | sonnet | none | 2/3 | 0.489 | 835,319 | $0.531 | 281s |

**Headline:**
- **Java is the surprise winner** — perfect 1.000 quality across every (model, tooling) combination, and `java/sonnet/none` does it for $0.33/run.
- **Best value:** `go/sonnet/none` at $0.303 quality 0.956, or `java/sonnet/none` at $0.326 quality 1.000.
- **Worst value:** `clojure/opus/beads` at $0.762 quality 0.556 (paying the most for the worst output).
- **Beads helps only for Go.** Python, typescript, rust, java, clojure all score lower (or no different) with beads enabled — beads' overhead isn't recouped on this small task.

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
| **Phase 1: Playpen + Scoring** | 🟡 Partial | `LocalRunner` (claude CLI on host) is the supported path and has been exercised end-to-end against `bundled://rest-api-crud`. **`DockerRunner` is a skeleton — not exercised.** All 7 scorers from the plan are implemented (`code_quality`, `build_time`, `token_efficiency`, `test_coverage`, `defect_rate`, `maintainability`, `idiomatic`); the four added scorers are wired but not yet exercised against an experiment with replicates. Three bundled tasks ship (`rest-api-crud`, `cli-data-pipeline`, `react-dashboard`) but only `rest-api-crud` has been exercised end-to-end. Task source schemes `bundled://`, `local://`, `git://`, and `github://owner/repo[/path/to/spec]` work; the github shorthand makes it easy to pull task specs from public benchmarks like `github://brazil-bench/benchmark-template/brazilian-soccer-mcp-guide.md`. |
| **Phase 2: Promotion + Reporting** | 🟡 Code present, lightly exercised | Lifecycle state machine, promotion gates, changelog, multi-format export, `retort promote`, `retort report effects` exist and unit-test. Not yet run on a real promotion decision. |
| **Phase 3: Analysis** | 🟡 Code present, lightly exercised | ANOVA + residual diagnostics (statsmodels), Bayesian conjugate-NIG updating (scipy), Pareto frontier, `retort analyze`. Verified on synthetic data; not yet on a complete experiment-1 dataset with replicates. |
| **Phase 4: Polish** | 🔴 Code present, untested | D-optimal augmentation (OApackage), candidate intake, scheduler, pluggy plugin system, status dashboard. Almost none of this has been exercised against real workloads yet. |
| **Resume / archive** | ✅ Working | `retort run --resume` skips already-recorded `(config, replicate)` pairs; `--retry-failed` retries failed ones. Each run's `/tmp` workspace is copied to `<workspace>/runs/<cell>/rep<N>/` before teardown so artifacts survive interrupts and `/tmp` cleanup. Per-run DB commit means an interrupt loses at most one run. |

### Known gaps and bugs

- `DockerRunner` not validated — use `runner: local` in `workspace.yaml` for now
- Only `claude-code` is wired up as an agent
- New scorers (`test_coverage`, `defect_rate`, `maintainability`, `idiomatic`) are wired but not yet exercised against an experiment with replicates
- `idiomatic` is opt-in via the `responses:` list in `workspace.yaml` (each invocation makes a Claude haiku call, ~$0.001/run, cached per workspace)
- `retort intake` / D-optimal augmentation untested against a real candidate
- Bundled tasks `cli-data-pipeline` and `react-dashboard` exist but haven't been run end-to-end; brazil-bench integration available now as a `github://brazil-bench/benchmark-template/<spec>.md` task source — running it end-to-end is tracked as `re-cn5`

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
