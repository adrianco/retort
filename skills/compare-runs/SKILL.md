---
name: compare-runs
description: Compare evaluated runs in a retort experiment along factor dimensions. Surfaces effects of each factor, aggregates across replicates, and highlights cells that diverge qualitatively — complementing (not replacing) retort's ANOVA analysis.
type: anthropic-skill
version: "1.0"
---

# Compare Runs

## Overview

Retort is a Design of Experiments engine — every run sits at a point in the factor space, and replicates exist to measure noise. Unlike pourpoise's `compare-attempts` (which maintains a ranked leaderboard of ad-hoc submissions), comparing retort runs is about **factor effects and qualitative divergence**, not "who won".

This skill is the qualitative counterpart to `retort analyze` / `retort report effects`. The ANOVA tells you *whether* a factor is significant. This skill tells you *what* changed in the generated code as you varied it.

## Parameters

- **experiment_dir** (required): e.g. `experiment-1/`. Must contain `retort.db` and a `runs/` directory of per-run archives, each already evaluated by `evaluate-run` (i.e. each `rep<N>/` has an `evaluation.md` and `findings.jsonl`).
- **output_file** (optional, default: `{experiment_dir}/reports/comparison.md`): Where to write the comparison report.
- **group_by** (optional, default: all factors): Comma-separated factors whose effect you want to isolate. The other factors are aggregated over.
- **include_failed** (optional, default: true): Whether to include failed runs in the comparison (they're still informative — failure itself is a finding).

## Steps

### 1. Discover evaluated runs

```bash
find {experiment_dir}/runs -name evaluation.md -not -path "*/salvaged-*/*" | sort
```

Parse each path to extract the cell (from the parent directory name, e.g. `language=rust_model=opus_tooling=beads`) and replicate (from the `rep<N>` or `rep<N>-failed` segment).

Constraints:
- You MUST skip runs under `salvaged-*/` — those are manually-archived artifacts from before auto-archival existed, and their layout is not regular.
- You MUST handle both `rep<N>/` (success) and `rep<N>-failed/` (failure) directory names.
- You SHOULD warn but not fail if some cells have no evaluation (evaluator hadn't run yet).

### 2. Load findings and metrics

For each evaluated run, load:
- Factors (from the cell directory name or the run's `stack.json`)
- Summary metrics (from `evaluation.md` header: requirements pass count, test counts, build status)
- Findings (from `findings.jsonl`) — categorize by `kind` and `severity`
- Architecture signal (from `summary/index.md`: the "Shape" one-liner)

Constraints:
- You MUST NOT re-evaluate. If `evaluation.md` is stale relative to the source, add a `stale` tag but use what's there.
- You MUST preserve replicates separately — do not average them into the cell yet.

### 3. Aggregate per cell

Group runs by cell (same factor combination across replicates):

| Cell | Replicates | Req pass (mean ± sd) | Test pass (mean ± sd) | Build failures | Distinct "shapes" |
|------|------------|----------------------|------------------------|----------------|--------------------|
| lang=python,model=opus,tooling=none | 3/3 | 8.7±0.6 / 10 | 12.3±0.5 / 12 | 0 | 1 (all Flask+SQLite) |
| lang=python,model=opus,tooling=beads | 2/3 | 6.0±1.4 / 10 | 10.0±1.0 / 12 | 1 | 2 (Flask vs FastAPI) |
| ... | ... | ... | ... | ... | ... |

Constraints:
- You MUST show mean ± sample standard deviation, not just mean. Variance across replicates is a first-class signal.
- "Distinct shapes" counts unique architecture summaries across replicates — a cell where the agent chose a different framework each time is a signal worth surfacing.
- Cells with only one replicate: drop the `±sd` and mark as `n=1`.

### 4. Surface factor effects

For each factor in `group_by`, hold the others roughly fixed and report the effect:

```markdown
## Effect of `tooling` (none vs beads)

Aggregating over language and model:

| Tooling | Mean req pass | Mean token cost | Mean build time | Build fail rate |
|---------|---------------|-----------------|-----------------|-----------------|
| none    | 8.1 / 10      | 289K tokens     | 124s            | 1/18 (6%)       |
| beads   | 7.2 / 10      | 441K tokens     | 156s            | 2/18 (11%)      |

Direction: beads costs ~52% more tokens and scored 11% lower on requirements.
This matches the p < 0.10 effect reported by `retort analyze`.

Qualitative: with `tooling: beads`, agents spent ~30% of their turns
on bd bookkeeping (visible in run transcripts). This accounts for the
token overhead.
```

Constraints:
- You MUST NOT claim statistical significance yourself — cite `retort analyze` or note "directional only".
- You MUST cross-reference the structured effect size reported by `retort report effects` when available at `{experiment_dir}/reports/analysis/*.md`.
- Qualitative claims MUST cite specific run IDs or findings (`see rep3 of lang=python,model=opus,tooling=beads`).

### 5. Identify qualitative divergence

Find cells where runs within a replicate group diverged in a way pure metrics miss:

```markdown
## Qualitative divergence

### lang=typescript, model=sonnet, tooling=beads — 3 replicates, 3 different shapes

| Rep | Framework | Storage | Notes |
|-----|-----------|---------|-------|
| 1 | Express + better-sqlite3 | SQLite | Built, tests failed on migration |
| 2 | Fastify + Prisma | Postgres (!) | Didn't build — assumed a Postgres container |
| 3 | Raw http + in-memory | Map object | Simplest, passed all requirements |

Within-cell variance is high: sonnet+TS+beads doesn't converge on a single
architecture. Consider whether this cell needs more replicates or whether
the task spec is under-constrained.
```

Constraints:
- You MUST highlight cells where replicates disagree on framework/library/storage, not just scores.
- You SHOULD identify at most 5 "most divergent" cells — past that it becomes noise.
- You MUST NOT label divergence as a failure — sometimes it's the signal the experiment was built to find.

### 6. Surface shared issues

Aggregate findings across all runs. A finding kind that shows up in >50% of runs is a property of the task or the model, not of the individual run.

```markdown
## Shared issues (appearing in ≥50% of runs)

| Finding | Runs affected | Severity |
|---------|---------------|----------|
| `skipped_test` | 28/37 | medium |
| `requirement_missing: R5 (pagination)` | 22/37 | high |
| `lint_warning: unused import` | 19/37 | low |

R5 (pagination) is either genuinely hard for agents OR the task spec
didn't emphasize it enough. Worth considering for a task-spec revision.
```

### 7. Write the report

Use the Output Format below. The report MUST link to individual `evaluation.md` files so readers can drill in.

## Output Format

```markdown
# Comparison: {experiment_dir_name}

Generated {timestamp} from {n} evaluated runs across {m} cells.

## Coverage

- Cells with ≥1 evaluation: {n}/{total}
- Runs evaluated: {n}/{total}
- Failed runs: {n}
- Missing evaluations: {list any}

## Per-cell summary

| Cell | n | Req pass | Test pass | Build fails | Shape diversity | Link |
|------|---|----------|-----------|-------------|-----------------|------|
| ... | 3 | 8.7±0.6 | 12.3±0.5 | 0 | 1 | [evals](runs/...) |

## Factor effects

### `{factor}`
...

## Qualitative divergence

...

## Shared issues

...

## Links

- ANOVA / effect sizes: `reports/analysis/`
- Per-run evaluations: `runs/<cell>/rep<N>/evaluation.md`
- Raw findings: `runs/<cell>/rep<N>/findings.jsonl`
```

## Constraints Summary

- You MUST read evaluation reports, not re-evaluate. This skill is purely aggregation.
- You MUST NOT produce a single "winner" ranking. Retort is about factor effects, not tournaments.
- You MUST preserve replicate-level detail at least down to the per-cell table.
- You MUST cite specific runs by their archive path when surfacing qualitative claims.
- You MUST cross-reference `retort analyze` output when making causal claims about factors.
- Output MUST be markdown that renders in GitHub's viewer.

## Troubleshooting

**No evaluations yet**
- Exit 0 with a single-line report: `No evaluated runs yet. Run evaluate-run on each rep<N>/ first.`
- Do not attempt to evaluate as a side effect — that's the user's / CLI's decision.

**Evaluations with different schema versions**
- Read what you can from each, note the schema mismatch in the "Coverage" section.
- Do not silently drop older evaluations — surface the problem.

**`retort analyze` reports don't exist**
- Proceed without them. Note in "Factor effects" that statistical backing is absent and the direction is qualitative-only.
