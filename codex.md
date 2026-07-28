# Codex Harness

Retort drives Codex through the `codex` local harness. It runs `codex exec` once
per Retort cell inside that cell's isolated playpen, with `--sandbox
workspace-write`, `--ephemeral`, and JSONL output enabled. The agent can modify
only the generated workspace. Retort archives the workspace and raw agent logs,
then scores it exactly as it does other local harnesses.

## Prerequisites

- `codex` must be installed, authenticated, and on `PATH`.
- The chosen model must be available to that Codex account.
- Install the toolchain for every language included in the experiment.

Codex subscription usage does not provide a per-run USD amount to the CLI. Retort
records tokens from Codex's final cumulative `token_count` event and leaves cost
blank rather than estimating an API charge.

## Configuration

Register Codex under `playpen.local_agents`, then select it with the normal
`agent` factor. A profile model is optional: omitting it makes Codex use its own
configured default, while specifying it makes the measurement reproducible.

```yaml
factors:
  language:
    levels: [python, go]
  agent:
    levels: [codex, codex-default]
  framework:
    levels: [fastapi, stdlib]

playpen:
  runner: local
  local_agents:
    codex:
      harness: codex
      model: gpt-5.6-terra
    codex-default:
      harness: codex
```

Codex can also judge a completed run. Reuse a profile or configure it inline:

```yaml
evaluation:
  enabled: true
  judge:
    harness: codex
    model: gpt-5.6-terra
```

Each evaluation attempt is archived under `<run_dir>/_judge/` as numbered
stdout, stderr, and JSON metadata files. Spec-gate second opinions are retained
as separate attempts.

## Smoke Experiment

[`experiments/schoch/experiment-50-codex-smoke/workspace.yaml`](experiments/schoch/experiment-50-codex-smoke/workspace.yaml)
defines one private Python/FastAPI REST API run with one replicate. Validate the
plan before spending a Codex turn, then run and inspect it:

```bash
retort run --phase screening \
  --config experiments/schoch/experiment-50-codex-smoke/workspace.yaml \
  --design experiments/schoch/experiment-50-codex-smoke/design.csv --dry-run

retort run --phase screening \
  --config experiments/schoch/experiment-50-codex-smoke/workspace.yaml \
  --design experiments/schoch/experiment-50-codex-smoke/design.csv

retort monitor experiments/schoch/experiment-50-codex-smoke
retort diagnose experiments/schoch/experiment-50-codex-smoke
```

Do not treat this one-cell smoke run as a harness comparison. Add at least one
other harness plus replicates before drawing conclusions about a harness effect.
