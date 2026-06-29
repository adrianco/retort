# retort-metaharness

A DoE/ANOVA methodology layer that makes the **agentic-orchestration harness** a
first-class factor in Retort's grid. It does **not** reimplement Retort's design
generator, ANOVA engine, Pareto sorter, or the per-cell `playpen` runner — it
**composes** them, adding our factor model, the variance-attribution effects
table, and a "$0/instant failure = tooling bug" diagnosis pass.

```
factors.py   our factors as first-class Retort DoE factors (documented levels)
design.py    fractional-factorial screening + full-factorial confirmation
             + aliasing report      (wraps retort.design.generator/.aliasing)
runner.py    glue to the per-cell metaharness runner (model routing /
             agenticow memory / darwin genome toggled per factor levels)
             + a $0 LocalStubRunner for end-to-end pipeline smoke tests
analysis.py  Type-II ANOVA: % variance per factor   (wraps retort.analysis.anova)
diagnose.py  TOOLING_FALSE_FAIL vs GENUINE_MODEL_FAIL
report.py    effects table + accuracy-vs-cost Pareto + Wardley/maturity overlay
             (wraps retort.analysis.pareto, reuses classify_phase)
cli.py       retort-metaharness design | run | analyze | diagnose | report
```

## Factor model

| factor | levels |
|---|---|
| **model** | deepseek-v4-pro, glm-5.2, opus-4.8, gpt-5.2 |
| **harness_config** | base-ReAct, self-consistency-N, routed, +agenticow-memory, +darwin-evolved-genome |
| **scaffold** | none, plan-and-solve, reflexion |
| **language** | python, typescript, go, rust |
| **task** | rest-api-crud, cli-data-pipeline, brazil-bench (pinned `REQUIREMENTS.json`) |

`retort-metaharness factors` prints every level with its documentation, the
OpenRouter model id, and the runner flags it contributes.

## The headline upgrade: interactions, not OFAT

A fractional-factorial / orthogonal-array screen crosses *all* factors at once,
so the ANOVA can attribute variance to **model vs harness vs language vs scaffold
+ their interactions** — answering "of any lift from +agenticow-memory, how much
is the memory branching vs the raw model?". Aliasing/confounding is reported so
you know which effects are clear and which are confounded at the chosen fraction.

## End-to-end (real pipeline, $0 smoke)

```bash
retort-metaharness smoke -o smoke-out      # design->run->diagnose->ANOVA->report
```

The smoke uses `LocalStubRunner` (no LLM, $0) purely to prove the pipeline; its
metric values are a documented deterministic fixture, **not** a model benchmark.
The real grid swaps in the per-cell metaharness runner:

```bash
retort-metaharness design --model deepseek-v4-pro --model opus-4.8 \
    --harness base-ReAct --harness +agenticow-memory --harness routed \
    --scaffold none --scaffold reflexion \
    --language python --language go --task rest-api-crud \
    --fraction 0.5 -o design.csv

retort-metaharness run -d design.csv --replicates 3 \
    --runner metaharness --runner-cmd "python -m playpen.run" -o results.csv

retort-metaharness diagnose -r results.csv      # tooling vs genuine
retort-metaharness analyze  -r results.csv      # ANOVA effects table
retort-metaharness report   -r results.csv      # effects + Pareto + Wardley
```

OpenRouter is metered; the key is read from `/tmp/.orkey` (never committed). The
pinned `REQUIREMENTS.json` gold is used only for scoring (the conformance
spec-gate), never injected into the solve loop.

## Composition contract with the per-cell runner

`MetaHarnessRunner` shells out to the runner as
`<cmd> --cell-json cell.json --out result.json`, passing the factor levels +
derived flags (`model`, `route`, `memory`, `genome`, `self_consistency`,
`scaffold`, `language`, `task`) and reading back `{status, requirement_coverage,
code_quality, cost_per_task, latency_s, tokens, notes}`. Retort's existing
scorers + spec-gate produce those fields; this layer never re-scores.
