# Retort — Platform Evolution Engine

> *Distill the best from the combinatorial mess*

## Plan for the Mayor

## Vision

Retort is an **installable, open-source Python project** that any organization can use to systematically evaluate and evolve their AI-assisted development tooling stacks. It applies statistical Design of Experiments to the combinatorial problem of languages × coding agents × frameworks × application types, continuously testing candidates in isolated playpens and promoting/retiring stacks based on measured confidence.

---

## 1. Project Structure

```
retort/
├── pyproject.toml                  # PEP 621, hatch build backend
├── README.md
├── LICENSE
├── .devcontainer/
│   ├── devcontainer.json           # Codespaces config: Python, Docker-in-Docker, extensions
│   ├── Dockerfile                  # Dev container image with all deps pre-installed
│   └── post-create.sh              # pip install -e ".[dev]", pre-pull playpen base images
├── docs/
│   ├── quickstart.md               # 10-minute setup guide
│   ├── concepts.md                 # DoE primer for the target audience
│   ├── configuration.md            # Factor/response/task YAML reference
│   └── extending.md                # Writing custom runners, scorers, tasks
│
├── src/
│   └── retort/
│       ├── __init__.py
│       ├── cli.py                  # `retort` CLI entry point (click or typer)
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── schema.py           # Pydantic models for all YAML config
│       │   └── loader.py           # Validates + loads workspace config
│       │
│       ├── design/
│       │   ├── __init__.py
│       │   ├── factors.py          # Factor registry — categorical/ordinal levels
│       │   ├── generator.py        # Fractional factorial, D-optimal augmentation
│       │   ├── aliasing.py         # Confounding/aliasing inspector
│       │   └── augmentor.py        # Adds new factor levels to existing design
│       │
│       ├── playpen/
│       │   ├── __init__.py
│       │   ├── runner.py           # Abstract base: provision → prompt → execute → teardown
│       │   ├── docker_runner.py    # Default: Docker container isolation
│       │   ├── cloud_runner.py     # Optional: AWS/GCP ephemeral VMs
│       │   └── prompt_builder.py   # Constructs agent prompts from task spec + stack config
│       │
│       ├── scoring/
│       │   ├── __init__.py
│       │   ├── collector.py        # Orchestrates scorer plugins per run
│       │   ├── scorers/
│       │   │   ├── __init__.py
│       │   │   ├── code_quality.py     # Lint pass rate, complexity, type coverage
│       │   │   ├── token_efficiency.py # Tokens per unit of functionality
│       │   │   ├── build_time.py       # Wall clock to first green CI
│       │   │   ├── test_coverage.py    # Generated test coverage
│       │   │   ├── defect_rate.py      # Post-generation validation failures
│       │   │   ├── maintainability.py  # Cross-agent modification success
│       │   │   └── idiomatic.py        # LLM-as-judge convention adherence
│       │   └── registry.py         # Plugin discovery for custom scorers
│       │
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── anova.py            # Main effects + interaction significance
│       │   ├── bayesian.py         # Conjugate prior updating on effect sizes
│       │   ├── pareto.py           # Multi-objective Pareto frontier
│       │   └── residuals.py        # Model adequacy checks
│       │
│       ├── promotion/
│       │   ├── __init__.py
│       │   ├── lifecycle.py        # State machine: candidate→screening→trial→production→retired
│       │   ├── gates.py            # Configurable confidence thresholds per transition
│       │   └── changelog.py        # Immutable audit log of all transitions
│       │
│       ├── scheduler/
│       │   ├── __init__.py
│       │   ├── queue.py            # Priority queue of pending experiment runs
│       │   ├── intake.py           # Watches for new candidates, triggers augmentation
│       │   └── budget.py           # Cost tracking and spend limits per phase
│       │
│       ├── reporting/
│       │   ├── __init__.py
│       │   ├── effects.py          # Main effect + interaction plots
│       │   ├── pareto_plot.py      # Multi-objective frontier visualization
│       │   ├── wardley.py          # Stack evolution stage overlay
│       │   ├── aliasing_report.py  # Current confounding + suggested de-aliasing runs
│       │   └── export.py           # JSON/CSV/HTML report generation
│       │
│       └── storage/
│           ├── __init__.py
│           ├── models.py           # SQLAlchemy/SQLite models for runs, results, transitions
│           └── migrations/         # Alembic migrations
│
├── tasks/                          # Bundled example test applications
│   ├── README.md                   # How to write a task spec
│   ├── rest-api-crud/
│   │   ├── task.yaml               # Functional spec, validation suite, expected endpoints
│   │   └── validate.py             # Automated pass/fail checks
│   ├── cli-data-pipeline/
│   │   ├── task.yaml
│   │   └── validate.py
│   └── react-dashboard/
│       ├── task.yaml
│       └── validate.py
│
├── examples/
│   ├── workspace.yaml              # Example workspace config with factors + responses
│   └── brazil-bench.yaml           # Config showing brazil-bench as a task source
│
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_factors.py
    │   ├── test_generator.py
    │   ├── test_anova.py
    │   ├── test_bayesian.py
    │   ├── test_pareto.py
    │   ├── test_lifecycle.py
    │   └── test_gates.py
    └── integration/
        ├── test_design_to_run.py   # Design matrix → playpen run → score vector
        └── test_full_lifecycle.py  # Candidate intake through promotion
```

---

## 2. Installation & Usage

### Primary environment: GitHub Codespaces

Retort is built and run in GitHub Codespaces. The `.devcontainer/` config provides a reproducible environment with Python, Docker-in-Docker (for playpen containers), and all dependencies pre-installed.

```bash
# Open the repo in Codespaces (via GitHub UI or CLI)
gh codespace create --repo retort/retort

# Everything is ready — the post-create script has already run:
#   pip install -e ".[dev]"
#   pulled base playpen images
```

The devcontainer uses the `docker-in-docker` Codespaces feature so playpen containers run inside the Codespace itself. For larger experiment runs that exceed Codespace resource limits, the `CloudRunner` can dispatch to external VMs while the orchestration stays in Codespaces.

### Local install (alternative)

```bash
git clone https://github.com/retort/retort.git
cd retort
pip install -e ".[dev]"
```

### PyPI install (after Phase 4)

```bash
pip install retort
```

### Initialize a workspace

```bash
retort init my-eval
cd my-eval
# edit workspace.yaml to define your factors, responses, and task sources
```

### workspace.yaml — the user's configuration

```yaml
factors:
  language:
    levels: [python, typescript, rust, go]
  agent:
    levels: [claude-code, cursor, copilot, aider]
  framework:
    levels: [fastapi, nextjs, axum, stdlib]
  app_type:
    levels: [rest-api, cli-tool, react-frontend, data-pipeline]
  orchestration:
    levels: [single-agent, swarm, hive-mind]
  constraint_style:
    levels: [rfc-2119, bdd, unconstrained]

responses:
  - code_quality
  - token_efficiency
  - build_time
  - test_coverage
  - defect_rate
  - maintainability
  - idiomatic_score

tasks:
  - source: bundled://rest-api-crud
  - source: bundled://cli-data-pipeline
  - source: git://github.com/brazil-bench/template-repo
  - source: local://./my-custom-task

playpen:
  runner: docker                   # or "cloud"
  replicates: 3                    # runs per design point
  timeout_minutes: 30
  cost_limit_usd: 500.00           # per screening phase

design:
  screening_resolution: 3
  characterization_resolution: 4
  significance_threshold: 0.10

promotion:
  screening_to_trial: { p_value: 0.10 }
  trial_to_production: { posterior_confidence: 0.80 }
  production_to_retired: { dominated_confidence: 0.95 }
```

### CLI commands

```bash
# Generate the screening design matrix
retort design generate --phase screening

# Execute all runs in the design matrix
retort run --phase screening

# Analyze results
retort analyze --phase screening

# View which factors survived screening
retort report effects

# Promote survivors and generate characterization design
retort promote --from screening --to trial
retort design generate --phase trial

# Ingest a new candidate (e.g., a new agent just shipped)
retort intake --factor agent --level "new-agent-v1"

# Full status dashboard
retort report dashboard
```

---

## 3. Python Dependencies

| Package | Purpose |
|---------|---------|
| `pyDOE3` | Fractional factorial design generation, Plackett-Burman |
| `OApackage` | Orthogonal arrays for mixed-level designs, D-optimal augmentation |
| `scipy` | ANOVA (f_oneway), statistical tests |
| `statsmodels` | Linear models with categorical factors, interaction terms |
| `numpy` / `pandas` | Data manipulation, design matrices |
| `arviz` + `pymc` | Bayesian updating, posterior confidence intervals |
| `plotly` or `matplotlib` | Effect plots, Pareto frontiers, Wardley overlays |
| `pydantic` | Config validation (workspace.yaml schema) |
| `sqlalchemy` + `alembic` | Run/result storage, schema migrations |
| `click` or `typer` | CLI |
| `docker` (Python SDK) | Playpen container management |
| `pyyaml` | Config loading |
| `pluggy` | Plugin system for custom scorers and runners |

---

## 4. Fractional Factorial Design

### Why fractional factorial?

With 6 factors at ~5 levels each, a full factorial is ~15,000 runs. A Resolution IV fractional factorial aliases three-factor interactions but cleanly estimates all main effects and two-factor interactions — which is what matters for deciding "does Language × Agent interaction dominate, or is Framework the main effect?"

### Design strategy

1. **Screening phase** — Resolution III design (e.g., D-optimal or orthogonal array L_25) to identify which factors have significant main effects. Discard factors with negligible effect.
2. **Characterization phase** — Resolution IV or V design for surviving factors to estimate two-factor interactions.
3. **Optimization phase** — Bayesian optimization on the reduced factor space to find the Pareto frontier of best stacks per app type.

### Handling new candidates

When a new level appears, `retort intake` triggers D-optimal augmentation — adding rows to the existing design matrix without re-running old experiments. The new candidate enters at the screening phase and progresses through the same gates.

---

## 5. The Playpen — Isolated Execution

### Runner protocol

```python
class PlaypenRunner(Protocol):
    def provision(self, stack: StackConfig) -> Environment: ...
    def execute(self, env: Environment, task: TaskSpec, agent: AgentConfig) -> RunArtifacts: ...
    def teardown(self, env: Environment) -> None: ...
```

Ships with `DockerRunner` (default, uses docker-in-docker within Codespaces) and `CloudRunner` (AWS/GCP, for runs that exceed Codespace resources). Organizations implement their own by subclassing.

### Task sources

- **Bundled** — 3 graduated tasks ship with Retort (CRUD API, CLI pipeline, React dashboard)
- **Git** — Fork any repo (e.g., brazil-bench template) as a task source
- **Local** — Point to a directory with a `task.yaml` and `validate.py`
- **Community** — Retort defines a task spec format; anyone can publish tasks

---

## 6. Analysis & Decision Rules

### Statistical model

For each response variable y:

```
y = μ + Σ αᵢ(factor_i) + Σ βᵢⱼ(factor_i × factor_j) + ε
```

`statsmodels` OLS with categorical encoding handles the ANOVA. `pymc` handles Bayesian updating with conjugate priors, accumulating confidence without requiring fixed sample sizes.

### Promotion gates (all configurable)

| Transition | Default Condition |
|------------|-----------|
| Candidate → Screening | Automatic on intake |
| Screening → Trial | Main effect p-value < 0.10 on ≥1 response |
| Trial → Production | 80% posterior probability of Pareto-non-dominated |
| Production → Retired | 95% posterior probability of Pareto-dominated |

---

## 7. Candidate Lifecycle

```
             ┌─────────────┐
             │  CANDIDATE   │  New combination appears
             └──────┬───────┘
                    │ D-optimal augmentation adds to design matrix
                    ▼
             ┌─────────────┐
             │  SCREENING   │  Resolution III — main effects only
             └──────┬───────┘
                    │ Significant main effect? (configurable p threshold)
                    ▼
             ┌─────────────┐
             │  TRIAL       │  Resolution IV/V — interactions estimated
             └──────┬───────┘
                    │ Pareto-competitive? Posterior confidence > threshold?
                    ▼
             ┌─────────────┐
             │  PRODUCTION  │  Recommended stack for its app-type niche
             └──────┬───────┘
                    │ Dominated on all metrics by a newer stack?
                    ▼
             ┌─────────────┐
             │  RETIRED     │  Kept in archive for reproducibility
             └──────────────┘
```

All transitions are recorded in an immutable changelog with timestamps, evidence, and design matrix state.

---

## 8. Extensibility

Organizations customize Retort through four plugin interfaces (via `pluggy`):

| Extension | Interface | Example |
|-----------|-----------|---------|
| **Runners** | `PlaypenRunner` protocol | K8s runner, Firecracker microVM runner |
| **Scorers** | `Scorer` protocol | Security audit scorer, internal style guide checker |
| **Task sources** | `TaskSource` protocol | Pull tasks from internal repo, Jira ticket specs |
| **Reporters** | `Reporter` protocol | Slack notifications, Confluence page updates |

---

## 9. Implementation Sequence

### Phase 0: Skeleton (weeks 1–2)
- Initialize repo with `pyproject.toml`, src layout, CLI skeleton
- Set up `.devcontainer/` with Python 3.12+, docker-in-docker, and `post-create.sh`
- Verify Codespaces launches cleanly with `retort --help` working on first open
- Implement `config/schema.py` + `config/loader.py` (Pydantic models for workspace.yaml)
- Implement `design/factors.py` + `design/generator.py` (pyDOE3 integration)
- Implement `storage/models.py` (SQLite via SQLAlchemy)
- Ship `retort init` and `retort design generate`
- Unit tests for design generation and factor registry

### Phase 1: Playpen + Scoring (weeks 3–4)
- Implement `DockerRunner` with provision/execute/teardown
- Implement bundled scorers (code_quality, token_efficiency, build_time)
- Build 3 bundled task specs with validation suites
- Ship `retort run` command
- Integration test: design matrix → playpen run → score vector in SQLite

### Phase 2: Analysis + Promotion (weeks 5–7)
- Implement `analysis/anova.py` (statsmodels) and `analysis/bayesian.py` (pymc)
- Implement `analysis/pareto.py` for multi-objective ranking
- Implement `promotion/lifecycle.py` state machine + `promotion/gates.py`
- Ship `retort analyze`, `retort promote`, `retort report effects`
- Integration test: full candidate lifecycle from intake through promotion

### Phase 3: Continuous Operation (weeks 8–10)
- Implement `scheduler/intake.py` — watch for new candidates, trigger augmentation
- Implement `design/augmentor.py` — D-optimal augmentation via OApackage
- Implement `scheduler/budget.py` — cost tracking and limits
- Ship `retort intake` and `retort report dashboard`
- Implement pluggy-based plugin system for custom scorers/runners

### Phase 4: Polish (weeks 11–12)
- Wardley map overlay reporting
- HTML export for shareable reports
- Aliasing diagnostics
- Documentation: quickstart, concepts, configuration reference, extending guide
- Package and publish to PyPI

---

## 10. Relationship to Other Projects

### brazil-bench
brazil-bench is an early exploration of the same problem space. Retort does not extend it. The brazil-bench template repo can be **forked and referenced as one of many task sources** via `source: git://github.com/brazil-bench/template-repo` in workspace.yaml.

### Pourpoise
Pourpoise is a potential future orchestration layer. Retort operates standalone with no dependency on Pourpoise. If Pourpoise matures, Retort could integrate as a "purpose" — but that's a later concern.

---

## 11. Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Non-determinism in LLM outputs adds noise | Configurable replicates per design point (default ≥3); model variance explicitly |
| Agent pricing makes large designs expensive | Screening aggressively prunes factor space; `budget.py` enforces spend limits |
| New candidates arrive faster than experiments complete | D-optimal augmentation; configurable minimum dwell time per phase |
| Metric gaming (agent optimizes for measured metrics) | Adversarial validation tasks + cross-agent maintainability scorer |
| Higher-order factor interactions | `residuals.py` monitors model adequacy; upgrade resolution if patterns remain |
| Organization has custom infra | Runner is a protocol — implement whatever isolation you need |
| Codespaces resource limits for parallel runs | Use CloudRunner to dispatch heavy runs externally; keep orchestration in Codespaces |
