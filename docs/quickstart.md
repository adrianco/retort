# Quickstart

Get a Retort experiment running in 10 minutes.

## Prerequisites

> See the [README](../README.md#prerequisites) for the full table. In short:

- **Python 3.11+** with a C/C++ toolchain + cmake (for the `OApackage` extension)
- **`claude` CLI**, authenticated — required by `LocalRunner`
- **`bd` (beads) CLI** — required only if your workspace uses `tooling: beads`
- **Per-language toolchains** for every language you list as a factor (e.g. `node`+`npm` for typescript, `go` for go, `rustup` for rust)
- ~~Docker~~ — `DockerRunner` is a skeleton; use `runner: local` in `workspace.yaml`. Docker is only needed if you plan to develop the Docker path.
- `pip install -e ".[dev,test]"` from a clone of https://github.com/adrianco/retort

## 1. Initialize a workspace

```bash
retort init my-eval
cd my-eval
```

This creates a directory with `workspace.yaml` (config template) and `retort.db` (results database).

## 2. Edit workspace.yaml

Start small. A minimal screening experiment:

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
  runner: local            # 'local' is supported; 'docker' is a skeleton
  replicates: 3
  timeout_minutes: 30

design:
  screening_resolution: 3
  significance_threshold: 0.10

promotion:
  screening_to_trial: { p_value: 0.10 }
  trial_to_production: { posterior_confidence: 0.80 }
```

## 3. Generate the screening design matrix

```bash
retort design generate --phase screening --config workspace.yaml -o design.csv
```

This produces a fractional factorial design — far fewer runs than a full factorial, while still estimating all main effects.

## 4. Preview the experiment

```bash
retort run --phase screening --config workspace.yaml --dry-run
```

Review the run plan before committing resources.

## 5. Execute the experiment

```bash
retort run --phase screening --config workspace.yaml
```

Each run provisions a Docker container, prompts the AI agent with the task spec, scores the output, and stores results in `retort.db`.

## 6. Analyze results

```bash
retort analyze --data results.csv -r code_quality -r token_efficiency --significance 0.10
```

This runs ANOVA for each response metric and reports which factors have statistically significant effects.

## 7. Promote survivors

```bash
retort promote my-stack --from screening --to trial \
    --evidence '{"p_value": 0.05}' --config workspace.yaml
```

Stacks that pass the screening gate advance to the trial phase for deeper characterization.

## 8. View reports

```bash
retort report effects --db retort.db --matrix-id 1 --metric code_quality
retort report dashboard --db retort.db
retort report wardley --db retort.db
```

## Next steps

- Read [Concepts](concepts.md) for the statistical foundations
- Read [Configuration](configuration.md) for the full YAML reference
- Read [Extending](extending.md) to add custom scorers, runners, or tasks
