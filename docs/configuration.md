# Configuration Reference

Retort workspaces are configured via `workspace.yaml`. This document covers every section and option.

## factors

Define the experimental factors and their levels.

```yaml
factors:
  language:
    levels: [python, typescript, rust, go]
  agent:
    levels: [claude-code, cursor, copilot, aider]
  framework:
    levels: [fastapi, nextjs, axum, stdlib]
```

Each factor must have at least 2 levels. Factor names become column headers in the design matrix CSV.

## responses

List the metric names to collect for each run.

```yaml
responses:
  - code_quality
  - token_efficiency
  - build_time
  - test_coverage
  - defect_rate
  - maintainability
  - idiomatic            # opt-in: per-run claude haiku call (~$0.001/run)
```

These names must match the scorer plugins available (built-in or custom). See [Extending](extending.md) for custom scorers.

## tasks

Define what the AI agents will build in each experiment run.

```yaml
tasks:
  - source: bundled://rest-api-crud                                            # Ships with Retort
  - source: bundled://cli-data-pipeline
  - source: bundled://react-dashboard
  - source: git://github.com/org/repo                                          # Clone from git
  - source: github://brazil-bench/benchmark-template                           # Github shorthand
  - source: github://brazil-bench/benchmark-template/spec.md                   # Specific spec file
  - source: local://./my-custom-task                                           # Local directory
```

Each task source must contain a `task.yaml` (functional spec) and `validate.py` (automated pass/fail checks). See the `tasks/` directory for bundled examples.

When a `github://` URI includes a spec path (e.g. `github://brazil-bench/benchmark-template/spec.md`), the **whole cloned repo** travels with the task and is copied into each playpen workspace alongside `TASK.md`. This is required for benchmarks like brazil-bench whose spec references data files (`data/*.csv`) and supporting docs in the same repo.

## playpen

Configure the isolated execution environment.

```yaml
playpen:
  runner: local               # "local" (supported) or "docker" (skeleton)
  replicates: 3               # Runs per design point (minimum: 1)
  timeout_minutes: 30         # Max time per run
  cost_limit_usd: 500.00      # Budget cap per screening phase
```

| Field | Default | Description |
|-------|---------|-------------|
| `runner` | `local` | `local` shells out to the agent CLI on the host; `docker` exists but is a skeleton |
| `replicates` | `3` | Number of times to repeat each design point. Higher = less noise, more cost |
| `timeout_minutes` | `30` | Kill a run after this many minutes |
| `cost_limit_usd` | none | Optional budget cap. Runs stop when limit is reached |

## design

Control the design matrix generation.

```yaml
design:
  screening_resolution: 3           # Resolution III for screening
  characterization_resolution: 4    # Resolution IV for characterization
  significance_threshold: 0.10      # p-value cutoff
```

| Field | Default | Description |
|-------|---------|-------------|
| `screening_resolution` | `3` | Resolution III aliases 3-factor interactions but estimates all main effects |
| `characterization_resolution` | `4` | Resolution IV also estimates two-factor interactions |
| `significance_threshold` | `0.10` | p-value below this = significant effect |

## promotion

Configure the gates between lifecycle phases.

```yaml
promotion:
  screening_to_trial:
    p_value: 0.10                    # Main effect significant at this level
  trial_to_production:
    posterior_confidence: 0.80       # 80% Bayesian confidence of competitiveness
  production_to_retired:
    dominated_confidence: 0.95       # 95% confidence of being dominated
```

All thresholds are configurable. Tighter thresholds = fewer false promotions but more runs needed.

## Full example

See `examples/workspace.yaml` for a complete configuration with all sections.

## Environment variables

| Variable | Description |
|----------|-------------|
| `RETORT_CONFIG` | Default config file path (overrides `workspace.yaml`) |
| `RETORT_DB` | Default database path (overrides `retort.db`) |
| `DOCKER_HOST` | Docker daemon for playpen containers |
