# Experiment 2 — Cross-task prediction with brazil-bench

> **Status:** workspace defined and validated; not yet run. Designed to combine with experiment-1's data so the ANOVA generalizes across tasks rather than re-running everything.

## Why this experiment

Experiment 1 told us language dominates `code_quality` on a trivial CRUD task. Open question: **does that hold on a harder task, or is it an artifact of how simple `rest-api-crud` is?**

Naive answer: re-run experiment-1's full design on a harder task. That's expensive (brazil-bench takes ~5–10× longer per cell) and most of the new data would just confirm what experiment-1 already showed.

Smarter answer: **add `task` as a factor and combine the two datasets.** Experiment-1 covers all 16 lang×model×tool cells for `task=rest-api-crud`. Experiment-2 covers the same cells for `task=brazil-bench`. The combined ANOVA then asks "does language still dominate when we factor in task?" — and surfaces task-by-language interactions that would have been invisible in either experiment alone.

## Setup

| | |
|---|---|
| **Task** | [`brazil-bench/benchmark-template`](https://github.com/brazil-bench/benchmark-template) — Brazilian Soccer MCP server. CSV ingest, BDD tests, 16 canonical requirements (FR/QP/DC/TR). |
| **Factors** | `language` (4), `model` (2), `tooling` (2) — same as experiment-1 so the data combines |
| **Cells** | 4 × 2 × 2 = 16 (full design at this size; the fractional pyDOE3 generator doesn't reduce mixed-level designs below ~16 cells without dropping a factor) |
| **Replicates** | 1 (singleton screening; the existing experiment-1 reps anchor the variance estimate) |
| **Total runs** | **16** ≈ 2–3 hours |
| **Scorers** | All 7 |
| **Visibility** | public |

## Run it

```bash
# Inspect the design
retort design generate --phase screening --config experiment-2/workspace.yaml

# See what would execute
retort run --phase screening --config experiment-2/workspace.yaml --dry-run

# Execute (resumable if interrupted)
retort run --phase screening --config experiment-2/workspace.yaml
retort run --phase screening --config experiment-2/workspace.yaml --resume
```

## Combine with experiment-1 for cross-task ANOVA

After the run completes, build a combined CSV that adds a `task` column to each experiment's data, then run ANOVA:

```bash
# Export each experiment's runs+scores
retort export csv --db experiment-1/retort.db -o experiment-1/reports/runs.csv
retort export csv --db experiment-2/retort.db -o experiment-2/reports/runs.csv

# Tag each with its task and concat. Awk one-liner avoids new tooling:
{ awk 'NR==1{print "task,"$0; next}{print "rest-api-crud,"$0}' experiment-1/reports/runs.csv;
  awk 'NR>1{print "brazil-bench,"$0}' experiment-2/reports/runs.csv;
} > combined.csv

# Cross-task ANOVA: task is now a factor alongside the others
retort analyze \
    --data combined.csv \
    -r code_quality \
    -f language -f model -f tooling -f task \
    --interactions
```

If `task:language` shows a significant interaction (p < 0.10), the language ranking *changes* with task complexity — which is the practically interesting finding. If `task` is significant on its own but interactions aren't, the harder task just shifts everything up/down by a constant and the language ranking from experiment-1 is reusable.

## Predicting unrun cells

If you stop the experiment early (say, only 8 of 16 brazil-bench cells completed), the combined ANOVA still produces a fitted model — and that model gives predicted scores for the cells you didn't run. The standard error of those predictions widens with each unrun cell, so the recommendation is: run enough cells that the combined design is balanced enough to fit the main effects + the task interaction. With experiment-1's full coverage already there, even 6–8 brazil-bench cells should be enough to estimate `task:language` interactions.

```bash
# After a partial run, the same analyze command works — predictions
# are emitted in the residual diagnostics section.
retort analyze --data combined.csv -r code_quality \
    -f language -f model -f tooling -f task --interactions
```

## What we'd expect to learn

- If `task` has a large main effect: the absolute scores shift but rankings hold.
- If `task:language` shows interaction: some languages handle complexity better than others (hypothesis: `go` and `rust` widen their lead because their type systems catch more issues that simple linting misses on `rest-api-crud`).
- If `task:tooling` shows interaction: beads helps more (or hurts more) on the complex task — concrete evidence about when structured task tracking pays off.
- If neither interacts with `task`: experiment-1 generalizes; the screening pass on `rest-api-crud` is enough for screening across tasks of similar shape.

## Tracking

- `re-cn5` — task source loader (done) + this experiment scaffold (done)
- `re-ucc` — fractional factorial demo (this experiment, when run)
