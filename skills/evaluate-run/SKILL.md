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

### 2. Detect language + toolchain

Read `stack.json` for the language factor. The evaluation commands differ by language:

| Language | Build | Test | Lint |
|----------|-------|------|------|
| python | `python -m py_compile **/*.py` or `pip install -e .` | `pytest -q` | `ruff check .` if available |
| typescript | `npm install --no-audit --no-fund && npm run build` (or `tsc --noEmit`) | `npm test --silent` | `npm run lint` if defined |
| go | `go build ./...` | `go test ./...` | `go vet ./...` |
| rust | `cargo build --quiet` | `cargo test --quiet` | `cargo clippy -- -D warnings` |

Constraints:
- You MUST run each command with a timeout (suggest 120s build, 180s test, 60s lint).
- You MUST capture exit codes, stdout, and stderr — the evaluation report includes the actual output.
- You MUST NOT install global toolchains. If a required toolchain is missing, note it and mark that check as `unavailable`, not `failed`.

### 3. Extract requirements from TASK.md

TASK.md contains the prompt the agent was given. Parse it into a checklist. Typical patterns:
- Numbered lists (`1. Implement ...`, `2. Write tests for ...`)
- Bullet lists of "must" / "should" items
- Code-fenced API signatures or example requests

Constraints:
- You MUST produce a deterministic requirement list with short stable IDs (`R1`, `R2`, ...) so comparisons across runs align.
- You MUST NOT invent requirements not present in TASK.md — this is the spec, not your expectations.
- You SHOULD group related bullets into a single requirement when the source is clearly a single ask.

### 4. Assess each requirement

For each `R<N>`, classify as one of:
- `implemented` — code clearly satisfies it, tests exercise it
- `partial` — code attempts it but is incomplete or untested
- `missing` — no evidence in the codebase
- `cannot-verify` — toolchain unavailable or tests couldn't run

Base the assessment on:
- The generated source (read key files)
- The test output from Step 2
- Any build errors that block verification

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
