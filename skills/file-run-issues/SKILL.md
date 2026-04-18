---
name: file-run-issues
description: Aggregate a retort run's findings.jsonl into a machine-readable assessment.json summary with severity counts, penalty score, requirement coverage, and top findings.
type: anthropic-skill
version: "2.0"
---

# File Run Issues

## Overview

`evaluate-run` produces a `findings.jsonl` per run — one JSON object per observation. This skill aggregates those findings into `assessment.json`, a compact machine-readable summary used by `FindingsScorer` and downstream reporting. It does **not** create beads issues or GitHub issues.

## Parameters

- **run_dir** (required): Same path `evaluate-run` used, e.g. `experiment-1/runs/language=rust_model=opus_tooling=beads/rep2/`
- **min_severity** (optional, default: `info`): Skip findings below this severity when computing counts. Options: `critical`, `high`, `medium`, `low`, `info`
- **dry_run** (optional, default: `false`): Print the assessment JSON without writing assessment.json

## Steps

### 1. Load findings

```bash
test -f {run_dir}/findings.jsonl || { echo "no findings.jsonl — run evaluate-run first"; exit 1; }
```

Read the file line-by-line. Each line is one finding with at minimum these fields:

```json
{"id": "R3", "kind": "requirement_missing", "severity": "high", "title": "...", "evidence": "...", "suggestion": "..."}
```

### 2. Filter by severity

Drop findings whose `severity` is below `min_severity`. The severity ordering from highest to lowest is: `critical`, `high`, `medium`, `low`, `info`.

### 3. Count severities

Count how many findings fall into each severity bucket:

```json
{"critical": 0, "high": 2, "medium": 5, "low": 3, "info": 1}
```

### 4. Compute penalty_score

```
start = 1.0
subtract: critical * 0.25 + high * 0.10 + medium * 0.03 + low * 0.01
clamp result to [0.0, 1.0]
```

A run with no findings scores 1.0. A run with one critical finding scores 0.75. A run with four critical findings scores 0.0 (clamped).

### 5. Collect top findings

Select the top 5 findings by severity (critical first, then high, medium, low, info). Within the same severity level, preserve the original order from findings.jsonl. Include all fields from the original finding object.

### 6. Compute requirement_coverage

Count findings with `kind` in `requirement_missing` or `requirement_partial` — these represent requirements the agent did not fully implement. Estimate total requirements from `R<N>` IDs present in findings plus any implemented ones (inferred from `evaluation.md` if available, otherwise estimate from the highest R-number seen).

```
requirement_coverage = implemented_count / total_requirements
```

If total requirements cannot be determined, set `requirement_coverage` to `null`.

### 7. Read model from stack.json

```bash
cat {run_dir}/stack.json | jq -r '.model // .agent // "unknown"'
```

If `stack.json` is absent or has no model/agent field, use `"unknown"`.

### 8. Write assessment.json

Write atomically (via `.tmp` rename):

```json
{
  "severity_counts": {"critical": 0, "high": 2, "medium": 5, "low": 3, "info": 1},
  "penalty_score": 0.67,
  "top_findings": [...],
  "requirement_coverage": 0.75,
  "model": "haiku",
  "evaluated_at": "2026-04-18T21:00:00Z"
}
```

Constraints:
- You MUST write atomically — write to `{run_dir}/assessment.json.tmp` then rename to `{run_dir}/assessment.json`.
- `evaluated_at` MUST be an ISO 8601 UTC timestamp.
- `penalty_score` MUST be rounded to 4 decimal places.
- `requirement_coverage` MAY be `null` if total requirements cannot be determined.

### 9. Emit a summary

Print a terminal-readable summary:

```
Assessment written to {run_dir}/assessment.json
  Severity counts: critical=0 high=2 medium=5 low=3 info=1
  Penalty score:   0.6700  (1.0 = clean, 0.0 = critical failures)
  Req coverage:    75.0%
  Model:           haiku
  Top finding:     [high] No pagination support on GET /books
```

If `--dry-run` was specified, print the JSON to stdout and skip the file write.

## Constraints Summary

- You MUST NOT create beads issues, GitHub issues, or any external tracker records.
- You MUST write assessment.json atomically.
- You MUST be safe to re-run repeatedly — re-running overwrites assessment.json with fresh aggregation.
- You MUST respect `--dry-run` by only printing what would be written.
- You MUST finish quickly — this is aggregation only, no LLM calls, no network calls.

## Interaction with retort

- `FindingsScorer` in `src/retort/scoring/scorers/findings.py` reads `{run_dir}/assessment.json` and returns `penalty_score` directly.
- The retort CLI MAY invoke this skill automatically after `evaluate-run` completes.
- If `assessment.json` is absent, `FindingsScorer` returns 0.5 (neutral) rather than failing.

## Troubleshooting

**findings.jsonl is empty**
- Write assessment.json with all-zero severity counts, penalty_score 1.0, empty top_findings.

**stack.json is missing**
- Use `model: "unknown"`. Do not abort.

**assessment.json.tmp rename fails (permissions)**
- Fall back to direct write. Log a warning.
