---
name: evaluate-run
description: Evaluate a single retort experiment run. Score the generated code against the task's TASK.md requirements, run its build and tests, compute metrics, and emit a structured evaluation report plus a machine-readable findings file.
type: anthropic-skill
version: "1.0"
---

# Evaluate Retort Run

## Overview

A retort run produces a workspace directory — generated source code for one factor-level combination — archived under `<experiment>/runs/<cell>/rep<N>/`. This skill evaluates that workspace against the task spec it was asked to implement, captures quantitative and qualitative findings, and writes results in a format comparable across runs.

This is the per-run counterpart to pourpoise's `evaluate-attempt`, adapted for retort's DoE structure: instead of ad-hoc attempts, each run is a point in a design matrix.

## Parameters

- **run_dir** (required): Path to the archived run workspace, e.g. `experiment-1/runs/language=rust_model=opus_tooling=beads/rep2/`
- **output_file** (optional, default: `{run_dir}/evaluation.md`): Where to write the human-readable report
- **findings_file** (optional, default: `{run_dir}/findings.jsonl`): Where to write structured findings (one JSON object per line) suitable for `file-run-issues`

## Inputs You Can Rely On

Each `run_dir` is laid out by retort's LocalRunner and contains:

| File | Purpose |
|------|---------|
| `TASK.md` | Task spec — the prompt the agent received. This is the "requirements" source of truth. |
| `stack.json` | `{"language": ..., "agent": ..., "framework": ...}` — the factor levels for this run |
| All generated source files | Exactly as the agent left them |
| Possibly `.beads/` | Only if `tooling=beads` was in effect — the agent used bd for tracking |
| Possibly build artifacts | `node_modules/`, `target/`, `__pycache__/`, etc. |

The retort database (`experiment-<N>/retort.db`) also holds this run's `ExperimentRun` + `RunResult` rows. You MAY query it read-only for cross-checking scores; you MUST NOT write to it.

## Steps

### 1. Verify the run workspace

```bash
test -d "{run_dir}" || { echo "run_dir missing"; exit 1; }
test -f "{run_dir}/TASK.md" || { echo "TASK.md missing — not a retort workspace"; exit 1; }
test -f "{run_dir}/stack.json" || { echo "stack.json missing"; exit 1; }
```

Constraints:
- You MUST NOT modify any file in `run_dir`. Run all commands read-only or in a temp copy.
- You MUST handle the case where the run was marked failed (suffix `-failed` on the directory). Evaluate what exists; note the failure up front.

### 2. Read the already-computed build/test/lint scores from `retort.db`

**Do NOT re-run the build, tests, or linter.** retort's scorers already ran them
for this run during scoring and stored the results — re-running the toolchain
(especially compiled/JVM languages) is the slowest part of evaluation and is
pure duplication. Read the stored scores instead.

**Fastest source — `{run_dir}/scores.json`.** When the eval runs inline as a
gate during `retort run`, the run isn't in `retort.db` yet, so the runner drops
the just-computed mechanical scores into `scores.json` in the archive. If it
exists, read it and skip the DB query:

```bash
[ -f "{run_dir}/scores.json" ] && cat "{run_dir}/scores.json"   # {"test_coverage": 1.0, "code_quality": 0.83, ...}
```

If `scores.json` is absent (e.g. retroactive `retort evaluate`), fall back to the
database.

The database is at `<experiment>/retort.db`. `run_dir` is `runs/<cell>/<rep>`,
so walk *up* until you find `retort.db` (don't hard-code a level count — the
nesting can vary). Match this run by the factors in `stack.json` plus the
replicate (the trailing `repN` of `run_dir`, also in `_meta.json`):

```bash
db=""; d="{run_dir}"
for _ in 1 2 3 4 5; do d="$(cd "$d/.." && pwd)"; [ -f "$d/retort.db" ] && { db="$d/retort.db"; break; }; done
lang=$(python3 -c "import json;print(json.load(open('{run_dir}/stack.json'))['language'])")
model=$(python3 -c "import json;print(json.load(open('{run_dir}/stack.json')).get('model',''))")
tooling=$(python3 -c "import json;print(json.load(open('{run_dir}/stack.json')).get('tooling',''))")
rep=$(basename "{run_dir}" | sed -E 's/rep([0-9]+).*/\1/')

# A resumed/retried cell can have BOTH a stale `failed` row (test_coverage=0)
# and the real `completed` row for the same (factors, replicate). Pull scores
# from the single most-recent matching run, preferring the archive's own state:
# a `-failed` run_dir -> the failed row, otherwise the completed row.
want_status=completed
case "{run_dir}" in *-failed) want_status=failed;; esac
sqlite3 -readonly "$db" "
  SELECT rr.metric_name, rr.value
  FROM run_results rr
  WHERE rr.run_id = (
      SELECT er.id FROM experiment_runs er
      WHERE json_extract(er.run_config_json,'\$.language')='$lang'
        AND json_extract(er.run_config_json,'\$.model')='$model'
        AND json_extract(er.run_config_json,'\$.tooling')='$tooling'
        AND er.replicate=$rep AND er.status='$want_status'
      ORDER BY er.finished_at DESC LIMIT 1)
    AND rr.metric_name IN ('test_coverage','code_quality','defect_rate',
                           'maintainability','idiomatic','token_efficiency');"
```

Interpret the stored scores (all 0–1) — these stand in for re-running:
- **`test_coverage`** — coverage / pass-rate. **1.0 ⇒ build + all tests passed; 0.0 ⇒ tests did not execute** (build or import failure — the test gate). Use this as the build+test signal.
- **`code_quality`** — lint/quality score. Use it for the Lint line.
- **`defect_rate`** — `1.0` ⇒ build+test succeeded.

Constraints:
- You MUST NOT re-run build/test/lint when these scores exist. Cite the score (e.g. "test_coverage=1.0 from retort.db") as evidence.
- **Fallback** — only if the DB or this run's row is absent (e.g. evaluating an un-scored archive): run the language's **test command once** (it builds too); skip the separate build and lint runs. Mark build/lint as derived. Use a 180s timeout; if a toolchain is missing, mark `unavailable`, not `failed`.

### 3. Extract requirements from TASK.md AND the agent's prompt

**First: prefer a pinned requirement list.** Per-run requirement extraction is
non-deterministic (the same task yields different counts on different runs,
which makes `requirement_coverage` non-comparable). So if the experiment ships a
fixed list, you MUST use it verbatim. Walk *up* from `run_dir` (as you did for
`retort.db`) to find `REQUIREMENTS.json`:

```bash
req=""; d="{run_dir}"
for _ in 1 2 3 4 5; do d="$(cd "$d/.." && pwd)"; [ -f "$d/REQUIREMENTS.json" ] && { req="$d/REQUIREMENTS.json"; break; }; done
```

If `REQUIREMENTS.json` exists, its `requirements[]` array IS the checklist —
use those exact `id`s and `requirement` texts, in that order, as the **complete
and only** list. Do NOT add, drop, merge, or re-number any. The denominator
(`total`) is fixed at `len(requirements)` for **every** run of this task. Skip
the extraction below entirely; go straight to step 4. (`how_to_verify` on each
entry tells you what evidence to look for.)

**Otherwise (no pinned list), extract requirements** as below.

The run must conform to the full prompt the agent was actually given. retort
assembles that prompt as: *"Read TASK.md … implement everything it asks for"* +
(a tooling instruction) + (only when a `prompt` factor was set) the contents of
`prompts/<level>.md`. So there are up to two requirement sources:

1. **`TASK.md`** — the task spec, always present. Parse into a checklist (`R1`, `R2`, …). Typical patterns:
   - Numbered lists (`1. Implement ...`), "must"/"should" bullets, code-fenced API signatures.
2. **The prompt-factor file** — *only if* `stack.json` has `prompt` set to something other than `none`/absent. Then read `prompts/<prompt>.md` from the experiment dir (where `workspace.yaml` lives — walk up from `run_dir` like you did for `retort.db`). Extract its additional, checkable instructions as prompt requirements (`P1`, `P2`, …) and verify the code/output followed them.

**Ignore `prompts.txt`** — it is a benchmark-template placeholder (it literally begins with `#ignore this file`), NOT the prompt retort gave the agent. Do not derive requirements from it.

Constraints:
- You MUST produce a deterministic list with stable IDs (`R<N>` for TASK.md, `P<N>` for prompt-factor instructions) so comparisons across runs align.
- You MUST NOT invent requirements not present in TASK.md or the prompt-factor file — these are the spec, not your expectations.
- You SHOULD group related bullets into a single requirement when the source is clearly a single ask.
- Most runs have no `prompt` factor, so the `P*` list is usually empty — that's fine; TASK.md is then the whole spec.

### 4. Assess each requirement and prompt instruction

This is the conformance gate: a run that doesn't implement the spec (and follow
the prompt) is a failure, so be accurate — cite evidence, don't guess.

For each `R<N>` (TASK.md) and each `P<N>` (prompt), classify as one of:
- `implemented` — code clearly satisfies it, tests exercise it
- `partial` — code attempts it but is incomplete or untested
- `missing` — no evidence in the codebase
- `cannot-verify` — you genuinely can't tell from the code (rare). Use sparingly with evidence.

**Tests are non-negotiable:** if `test_coverage == 0` (tests did not run), the run already FAILS the test gate — that is always a failure, full stop. Note it up front and don't dress it up as `cannot-verify`.

Base the assessment on:
- The generated source (read key files)
- The stored `test_coverage` from Step 2 (1.0 ⇒ build + all tests pass; 0.0 ⇒ tests did not execute, so treat unverified requirements as `cannot-verify`)
- The grepped test/skip counts from Step 5

Constraints:
- You MUST cite concrete evidence for each classification: file path, symbol name, or test name.
- You MUST NOT score a requirement as `implemented` solely because it has a stub function.
- You SHOULD note "enhancement beyond spec" separately — these aren't deductions but are worth surfacing.

### 5. Detect skipped / disabled tests

Skips inflate pass rates without verifying behavior. Count them:

```bash
# Python
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" 2>/dev/null | wc -l

# Go
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" 2>/dev/null | wc -l

# Rust
grep -rE "#\[ignore\]|#\[cfg\(ignore\)\]" . --include="*.rs" 2>/dev/null | wc -l

# TypeScript (jest/vitest)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts" --include="*.js" 2>/dev/null | wc -l
```

Constraints:
- You MUST report `effective_tests = passed + failed` (skipped excluded).
- You MUST flag a `skipped_test` finding for each skip, even if the skip looks "reasonable" — the signal matters for cross-run comparison.

### 6. Compute run metrics

```bash
# Lines of code (exclude build artifacts)
cloc . --exclude-dir=node_modules,target,__pycache__,.git,dist,build 2>/dev/null | tail -20

# File count
find . -type f \
  -not -path "*/node_modules/*" -not -path "*/target/*" \
  -not -path "*/__pycache__/*" -not -path "*/.git/*" \
  | wc -l

# Dependency count (language-appropriate)
case $lang in
  python)     wc -l requirements.txt pyproject.toml 2>/dev/null ;;
  typescript) node -e "const p=require('./package.json');console.log(Object.keys({...p.dependencies,...p.devDependencies}).length)" 2>/dev/null ;;
  go)         grep -c "^\s*\S" go.sum 2>/dev/null ;;
  rust)       grep -cE "^\S+ = " Cargo.toml 2>/dev/null ;;
esac
```

If `cloc` isn't available, fall back to a simple `wc -l` loop over source files for the language's extensions only. Never include `node_modules`, `target`, etc.

### 7. Invoke run-summary

Delegate architecture analysis to the `run-summary` skill:

```
summarize codebase {run_dir} to {run_dir}/summary/
```

This produces structured markdown under `{run_dir}/summary/` covering modules, interfaces, and flow. Reference it from the final report rather than duplicating its content.

### 8. Write findings.jsonl

One JSON object per line, one object per finding. Schema:

```json
{"id": "R3", "kind": "requirement_missing", "severity": "high", "title": "No pagination support on GET /books", "evidence": "src/app.py:42 returns full list unconditionally", "suggestion": "Add ?limit and ?offset query params"}
{"id": "test-skip-1", "kind": "skipped_test", "severity": "medium", "title": "test_concurrent_writes is skipped", "evidence": "tests/test_app.py:87 @pytest.mark.skip", "suggestion": "Implement the concurrency check or delete the test"}
{"id": "build-fail", "kind": "build_failure", "severity": "critical", "title": "cargo build fails with E0308", "evidence": "src/main.rs:23 — mismatched types", "suggestion": "Fix the type signature before this run can be scored"}
```

Allowed `kind` values:
- `requirement_missing`, `requirement_partial`
- `build_failure`, `test_failure`
- `skipped_test`, `disabled_test`
- `lint_warning`, `security_concern`
- `doc_missing`, `enhancement`

Allowed `severity`: `critical`, `high`, `medium`, `low`, `info`.

Constraints:
- You MUST produce valid JSON on every line (newline-delimited).
- You MUST NOT emit findings that duplicate each other; collapse similar items.
- Each finding MUST have non-empty `evidence` — the file + line or command + output snippet that backs the claim.

### 9. Write evaluation.md

Use the template in Output Format below. The human-readable report links to `findings.jsonl` and `summary/index.md` rather than inlining them.

## Output Format

```markdown
# Evaluation: {cell_name} · rep {replicate}

## Summary

- **Factors:** language={lang}, model={model}, tooling={tooling} (plus any extras)
- **Status:** ok | failed ({reason}) | cannot-verify ({reason})
- **Requirements:** {implemented}/{total} implemented, {partial} partial, {missing} missing
- **Tests:** {passed} passed / {failed} failed / {skipped} skipped ({effective} effective)
- **Build:** {pass|fail|unavailable} — {duration}s
- **Lint:** {pass|fail|unavailable} — {warning_count} warnings
- **Architecture:** see `summary/index.md`
- **Findings:** {n} items in `findings.jsonl` ({critical} critical, {high} high, ...)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | ... | ✓ implemented | `src/app.py:Book` |
| R2 | ... | ~ partial | `src/app.py:list_books` — no pagination |
| R3 | ... | ✗ missing | no search endpoint found |

## Build & Test

```text
{build command}
{first 40 lines of output, elided if long}
```

```text
{test command}
{test summary + failures}
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | {n} |
| Files | {n} |
| Dependencies | {n} |
| Tests total | {n} |
| Tests effective | {n} |
| Skip ratio | {pct}% |
| Build duration | {s}s |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] ...
2. [high] ...
...

## Reproduce

```bash
cd {run_dir}
{exact commands used above, in order}
```
```

## Interaction with retort

- The retort CLI invokes this skill after each successful run (see `cli.py:_evaluate_run`). You SHOULD assume the archive already exists when this skill is called.
- Evaluation failures MUST NOT abort the experiment — the skill exits with stderr written but always exit code 0 so the run loop continues.
- Results are cached per run — if `evaluation.md` already exists and is newer than all source files in `run_dir`, the skill MAY exit early (idempotent re-invocation).

## Constraints Summary

- You MUST NOT modify files in `run_dir` except under `summary/`, and MUST create `evaluation.md` and `findings.jsonl` inside `run_dir`.
- You MUST NOT write to `retort.db` or any file outside `run_dir`.
- You MUST finish in under 5 minutes wall-clock. If you can't, emit whatever you have and return.
- You MUST cite file:line evidence for every finding.
- You MUST keep the output deterministic enough that re-running against the same workspace produces the same requirement IDs and the same findings (order may differ).

## Troubleshooting

**Toolchain missing (e.g. `cargo: command not found`)**
- Mark build/test as `unavailable`.
- Add a finding `toolchain_missing` (severity: info) so cross-run comparison knows why this run wasn't verified.

**TASK.md looks generic / doesn't list discrete requirements**
- Extract one requirement per imperative sentence in the prompt.
- Emit a `doc_missing` info finding noting that the task spec is under-specified.

**`run-summary` skill fails**
- Continue without it. Note in evaluation.md under Architecture: "summary skill unavailable".
- Do not let summary failure prevent the evaluation report from being written.
