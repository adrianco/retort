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

Full data is in [`experiment-1/reports/`](experiment-1/reports/) — ANOVA, per-stack maturity, full CSV, and a static-HTML web report (sortable, with per-stack drill-downs). Below is the headline.

**Setup:** 4 languages (python, typescript, go, rust) × 2 models (opus, sonnet) × 2 tooling (none, beads) × 3 replicates = 48 runs against the bundled `rest-api-crud` task. **46 completed, 3 failed.** Total cost ≈ $20.

**ANOVA on `code_quality`:** R² = 0.80, language is highly significant (p < 5e-14); model and tooling are not significant on their own.

**Top stack by maturity:** `go / sonnet / beads` — maturity 1.000 (3/3 completed, perfect agreement, code_quality 1.000). Generate the maturity report yourself with `retort maturity --db experiment-1/retort.db`.

**Failed cells:** `typescript / sonnet / beads` (1 of 3), `rust / sonnet / beads` (2 of 3) — likely the 15-minute timeout on slower toolchains, not a true language-stack issue.

The original n=1 table below (from the first pass before replicates landed) is kept for reference.

### Original n=1 table (pre-replicates)

> Single runs on a small task (REST API CRUD). Treat as directional only — superseded by the replicate-aware results above.

**Task:** Build a REST API with CRUD operations for a book collection (Flask/Express/net-http + SQLite)
**Factors:** Language (python, typescript, go) x Model (opus, sonnet) x Tooling (none, beads)
**Agent:** Claude Code in all runs

| Language | Model | Tooling | Quality | Tokens | Cost | Time | Status |
|----------|-------|---------|---------|--------|------|------|--------|
| python | opus | none | 0.79 | 154,864 | $0.21 | 129s | ok |
| python | opus | beads | 0.62 | 261,251 | $0.29 | 86s | ok |
| python | sonnet | none | 0.67 | 431,978 | $0.30 | 108s | ok |
| python | sonnet | beads | 0.62 | 386,816 | $0.26 | 106s | ok |
| typescript | opus | none | 0.73 | 245,081 | $0.30 | 109s | ok |
| typescript | opus | beads | 0.73 | 407,961 | $0.43 | 231s | ok |
| typescript | sonnet | none | 0.73 | 936,583 | $0.59 | 273s | ok |
| typescript | sonnet | beads | — | 730,588 | $0.43 | 249s | FAIL |
| go | opus | none | 0.89 | 187,950 | $0.30 | 119s | ok |
| go | opus | beads | 0.96 | 322,783 | $0.40 | 163s | ok |
| go | sonnet | none | 0.96 | 275,497 | $0.25 | 126s | ok |
| go | sonnet | beads | **1.00** | 571,800 | $0.35 | 163s | ok |

**Observations (n=1, directional only — superseded by replicate-aware ANOVA above):**
- **Go scored highest** across all combinations (0.89–1.00)
- **Beads helped Go** but **hurt Python** — replicate runs confirmed: the only sub-0.8-maturity stacks in the full experiment are `python/{opus,sonnet}/beads`
- **TypeScript + sonnet + beads** failed in the original pass; rerunning with replicates surfaced timeout-related rust failures too

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
