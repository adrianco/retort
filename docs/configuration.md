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
| `local_inference_cost` | none | Cost model for local/offline models — see below |

### local_inference_cost

Enables the `_cost_usd` metric for runs where the agent doesn't report API spend (local models such as llama, mistral, etc.). Cost is computed from wall-clock run duration using electricity and amortized hardware costs.

```yaml
playpen:
  local_inference_cost:
    cost_per_kwh: 0.20           # USD per kWh — check your electricity bill
    power_watts: 210             # GPU/system draw during inference
    hardware_cost_usd: 550       # Purchase price in USD
    amortization_months: 36      # Expected useful life
    utilization_fraction: 0.25   # Fraction of time hardware runs inference
```

| Field | Description |
|-------|-------------|
| `cost_per_kwh` | Electricity rate in USD/kWh |
| `power_watts` | GPU or system power draw during inference (watts) |
| `hardware_cost_usd` | Hardware purchase price in USD |
| `amortization_months` | Amortization period (months); longer = lower per-run cost |
| `utilization_fraction` | Fraction of amortization window the hardware is actively running inference (0–1) |

**Cost formula:**

```
electricity_per_s = (power_watts / 1000) × cost_per_kwh / 3600
hardware_per_s    = hardware_cost_usd / (amortization_months × 30 × 24 × 3600 × utilization_fraction)
run_cost          = (electricity_per_s + hardware_per_s) × duration_seconds
cost_per_token    = run_cost / total_tokens
```

**Example — AMD Radeon RX 9700 XT at $0.20/kWh vs. cloud pricing:**

With the settings above (210 W, $550, 36 months, 25% utilization):
- Electricity: ~$0.0000117/s
- Hardware amortization: ~$0.0000236/s
- **Effective rate: ~$0.035/s ≈ $0.085/M tokens at 2 tok/s**

Compare to Haiku 4.5 at $0.25/$1.25 per million input/output tokens — local hardware breaks even around 5–10 tokens/s depending on the mix.

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
