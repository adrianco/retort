# Retort

**Platform Evolution Engine** — Distill the best from the combinatorial mess.

Retort applies statistical Design of Experiments (DoE) to systematically evaluate AI-assisted development tooling stacks. It generates fractional factorial designs across languages, coding agents, and frameworks, executes experiments in isolated playpens, scores the results, and promotes or retires stacks based on measured confidence.

## Early Results: Experiment 1

> **Caveat:** These are single runs on a small task (REST API CRUD). No replicates — treat as directional, not statistically significant. The purpose is to validate that the pipeline works end-to-end with real agent execution.

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

**Observations (n=1, directional only):**
- **Go scored highest** across all combinations (0.89–1.00), likely due to `go vet` catching real issues and Go's simpler project structure
- **Go + sonnet + beads** achieved a perfect 1.00 quality score
- **Beads helped Go** but **hurt Python** — may be a language-ecosystem effect (Go's explicit style benefits from structured task tracking)
- **Sonnet used more tokens** than Opus across all languages, especially TypeScript (936K vs 245K)
- **TypeScript + sonnet + beads** was the only failure — the combination exceeded useful context
- **Total experiment cost: $3.97** for 12 runs (4.9M tokens)

These results will be refined with replicates and more complex tasks (brazil-bench template).

## Installation

Requires Python 3.11+.

```bash
pip install -e ".[dev,test]"
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
  runner: docker
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

| Phase | Status | Scope |
|-------|--------|-------|
| **Phase 0: Skeleton** | COMPLETE | Project structure, config schema, design generation, storage layer, `retort init`, `retort design generate` |
| **Phase 1: Playpen + Scoring** | COMPLETE | DockerRunner, scoring framework (3 built-in scorers), bundled task specs, `retort run` |
| **Phase 2: Promotion + Reporting** | COMPLETE | Lifecycle state machine, promotion gates, changelog, effects computation, multi-format export, `retort promote`, `retort report effects` |
| **Phase 3: Analysis** | COMPLETE | ANOVA with residual diagnostics (statsmodels), Bayesian updating with conjugate NIG priors (scipy), Pareto frontier ranking, `retort analyze` |
| **Phase 4: Polish** | COMPLETE | D-optimal augmentation, candidate intake, scheduler (budget & queue), pluggy-based plugin system, status dashboard, CLI refinements |

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

MIT
