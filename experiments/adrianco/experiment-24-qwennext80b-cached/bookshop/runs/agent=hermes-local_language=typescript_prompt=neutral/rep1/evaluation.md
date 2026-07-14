# Evaluation: agent=hermes-local language=typescript prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, agent=hermes-local (Qwen3-Coder-Next), framework=unknown, prompt=neutral
- **Status:** failed (empty workspace — the agent produced no source code)
- **Requirements:** 0/12 implemented, 0 partial, 12 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — no test files exist
- **Build:** unavailable — nothing to build (no source)
- **Lint:** unavailable — no source
- **Architecture:** none — workspace is empty (run-summary skipped, nothing to summarize)
- **Findings:** 15 items in `findings.jsonl` (2 critical, 13 high)

## What happened

The agent's final message (`_agent_stdout.log`) confidently describes a complete
`book-api/` TypeScript project — `src/index.ts`, `controller.ts`,
`repository.ts`, two test files with "23 passing tests", `package.json`,
`tsconfig.json`, `README.md`, and a compiled `dist/`. **None of these files
exist.** The archive contains only `TASK.md`, `stack.json`, `_meta.json`,
`scores.json`, the two log files, and `.hermes_usage.json`.

The stdout log itself carries the smoking gun (lines 41–42):

```
⚠️ File-mutation verifier: 1 file(s) were NOT modified this turn ...
  • .../package.json — [write_file] Refusing to write to sensitive system path ...
```

The agent tried to write into the temp workspace via an absolute path that the
tool sandbox rejected as a "sensitive system path," so its writes never landed.
It then reported success anyway — a hallucinated deliverable. This is a total
failure: no code, no README, no tests.

`scores.json` (`test_coverage=0.7463`, `code_quality=0.7333`, …) is **stale**:
`retort.db` has no typescript hermes-local row at all (only `python`=completed
and `go`=crashed), so those numbers are cached leftovers in this
`*-cached` experiment dir and do not describe this empty archive. They were
disregarded for scoring.

## Requirements

All requirements are unmet because the workspace contains no source.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✗ missing | no source files in run_dir |
| R2 | GET /books list | ✗ missing | no source files in run_dir |
| R3 | GET /books ?author= filter | ✗ missing | no source files in run_dir |
| R4 | GET /books/{id} | ✗ missing | no source files in run_dir |
| R5 | PUT /books/{id} | ✗ missing | no source files in run_dir |
| R6 | DELETE /books/{id} | ✗ missing | no source files in run_dir |
| R7 | SQLite/embedded persistence | ✗ missing | no source files in run_dir |
| R8 | JSON + HTTP status codes | ✗ missing | no source files in run_dir |
| R9 | Input validation (title/author) | ✗ missing | no source files in run_dir |
| R10 | GET /health | ✗ missing | no source files in run_dir |
| R11 | README.md | ✗ missing | no README.md in run_dir |
| R12 | ≥3 tests | ✗ missing | no test files in run_dir |

## Build & Test

```text
build: n/a — no package.json / no source to compile
test:  n/a — no test files present
```

No toolchain was run because there is nothing to run it against. `scores.json`
was ignored (stale cache; no matching retort.db row).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 |
| Files (non-meta) | 0 |
| Files (total, incl. logs/meta) | 7 |
| Dependencies | 0 |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | n/a |
| Build duration | n/a |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Run produced no source code — empty workspace
2. [critical] Agent claimed success but wrote nothing (hallucinated deliverables)
3. [high] scores.json is stale/cached and does not reflect this archive
4. [high] R1 POST /books not implemented
5. [high] R10 GET /health not implemented

## Reproduce

```bash
cd experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=typescript_prompt=neutral/rep1
find . -type f | sort          # only TASK.md, stack.json, _meta.json, scores.json, logs
cat _agent_stdout.log          # claimed book-api/ tree + file-mutation verifier warning
sqlite3 -readonly ../../../retort.db \
  "SELECT status, run_config_json FROM experiment_runs WHERE json_extract(run_config_json,'\$.agent')='hermes-local';"
  # -> only python(completed), go(crashed); no typescript row -> scores.json is stale
```
