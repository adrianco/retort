# Retort Skills

Claude-invocable skills that automate the per-run evaluation + cross-run comparison pipeline. Adapted from [brazil-bench/pourpoise](https://github.com/brazil-bench/pourpoise/tree/main/skills), retained in retort so the workflow travels with the code.

## Pipeline

```
retort run
    │
    ▼ (for each successful cell × rep)
[evaluate-run]  ──►  evaluation.md  +  findings.jsonl  +  summary/
    │                                    │
    │                                    ▼
    │                              [file-run-issues]  ──►  beads (+ optional GitHub)
    ▼
[compare-runs]  ──►  reports/comparison.md
    │
    ▼
retort report web   ──►  reports/web/index.html  + per-run HTML drill-downs
```

## Skills

| Skill | Purpose | Invoked by |
|-------|---------|------------|
| [evaluate-run](evaluate-run/SKILL.md) | Score one run's generated code against its TASK.md, run build/tests, emit structured report + findings | `retort run` after each success; manual |
| [run-summary](run-summary/SKILL.md) | Fast architecture summary of one generated project — modules, interfaces, flow | `evaluate-run` |
| [compare-runs](compare-runs/SKILL.md) | Aggregate evaluated runs along factor dimensions, surface qualitative divergence | `retort report compare`; manual |
| [file-run-issues](file-run-issues/SKILL.md) | Turn a run's findings.jsonl into tracked issues (beads by default, GitHub optional) | `evaluate-run` post-hook; manual |

## Invocation

Skills are prompts — they direct Claude (via the `claude` CLI) to perform the task. You invoke a skill by pointing Claude at its SKILL.md:

```bash
# Evaluate a single run
claude -p "Follow the evaluate-run skill at rig/skills/evaluate-run/SKILL.md for run_dir=experiment-1/runs/language=rust_model=opus_tooling=none/rep1/"

# Compare all runs in an experiment
claude -p "Follow the compare-runs skill at rig/skills/compare-runs/SKILL.md for experiment_dir=experiment-1/"
```

Retort automates these invocations after each run completes (see `workspace.yaml` `evaluation:` block). Manual invocation is always available for ad-hoc analysis.

## Differences from pourpoise

- **No leaderboard**: retort runs are points in a DoE design, not competing attempts. `compare-runs` surfaces factor effects and qualitative divergence, not ranked placement.
- **Smaller codebases**: `run-summary` is a scoped-down `codebase-summary` — seconds, not minutes, targeted at one-task generated projects.
- **beads-first issue tracking**: `file-run-issues` defaults to the `re` beads project, not GitHub. Retort's experimental noise would overwhelm the GitHub tracker.
- **Per-run caching**: every skill is idempotent — re-running against the same workspace yields the same output, with dedup against prior filed issues.

## Status

Skills are defined but the CLI integration (`retort run` auto-invocation, `retort report compare`, `retort report web`) is work-in-progress. See beads `re-*` (tag: `auto-evaluation`) for tracking.
