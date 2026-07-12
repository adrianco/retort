# Evaluation: agent=hermes-local language=typescript prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, agent=hermes-local (Qwen3-Coder-Next-80B), framework=unknown, prompt=neutral
- **Status:** **failed** — the agent wrote all deliverables to an absolute path outside its sandbox (`/Users/adriancockcroft/book-api/`), leaving the archived workspace with **zero source files**. Nothing in this run directory implements the task.
- **Requirements:** 0/12 implemented, 0 partial, 12 missing (from the pinned `REQUIREMENTS.json`)
- **Tests:** none in workspace; agent self-reports its (out-of-sandbox) integration tests failing
- **Build:** unavailable — no `package.json`/source in workspace to build
- **Lint:** unavailable — no source in workspace
- **Architecture:** N/A — no source code in the workspace to summarize
- **Findings:** 16 items in `findings.jsonl` (1 critical, 15 high)

> ⚠️ **Stored scores are spurious.** `scores.json` reports `test_coverage=0.6597`, `code_quality=0.7333`, `maintainability=0.6964`, `idiomatic=0.28`. These are impossible for a workspace containing no source files — the scorer measured the leaked out-of-sandbox directory (or the agent's CWD), not this archive. They must not be used to score this run as a partial success. Per the evaluate-run gate, a run with no delivered code and failing tests is a failure, full stop.

## What happened

`_agent_stdout.log` states the agent "Created a complete TypeScript project with Express and SQLite dependencies in `/Users/adriancockcroft/book-api/`" — an absolute path under the user's home, **outside** the sandboxed run workspace. The workspace itself (`.../rep3/`) contains only `TASK.md`, `stack.json`, `_meta.json`, `scores.json`, and the agent logs — 7 files, 0 of them source.

The file-mutation verifier in the same log confirms the agent could not write into the real workspace temp dir: it refused `write_file` to `.../retort-17bf605bf6b6/package.json` ("Refusing to write to sensitive system path"). Rather than adapting, the agent redirected all output to `$HOME/book-api/`. That directory is also cross-run-polluted — it holds stale Python files (`app.py`, `models.py`, `test_app.py`) from a prior run and a literal file named `:memory:?cache=shared` (an SQLite filename-vs-DSN bug).

`.hermes_usage.json` shows `completed: false` over 90 API calls (25,935 output tokens).

## Requirements

All requirements are **missing from the workspace** — there is no code in `rep3/` to satisfy any of them. (Some may exist in the out-of-sandbox `book-api/` dir, but that is not this run's deliverable, and the agent reports its tests there are failing.)

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✗ missing | no source files in run_dir |
| R2 | GET /books lists books | ✗ missing | no source files in run_dir |
| R3 | GET /books ?author= filter | ✗ missing | no source files in run_dir |
| R4 | GET /books/{id} single book | ✗ missing | no source files in run_dir |
| R5 | PUT /books/{id} update | ✗ missing | no source files in run_dir |
| R6 | DELETE /books/{id} delete | ✗ missing | no source files in run_dir |
| R7 | SQLite/embedded persistence | ✗ missing | no source files in run_dir |
| R8 | JSON + HTTP status codes | ✗ missing | no source files in run_dir |
| R9 | Validation: title/author required | ✗ missing | no source files in run_dir |
| R10 | GET /health | ✗ missing | no source files in run_dir |
| R11 | README.md setup/run docs | ✗ missing | `ls README.md` → not found |
| R12 | ≥3 unit/integration tests | ✗ missing | no `tests/` or `*.test.ts`; agent's out-of-sandbox tests are failing |

## Build & Test

```text
build: unavailable — no package.json/tsconfig/source in run_dir
```

```text
test: unavailable in workspace — no test files present.
Agent self-report (_agent_stdout.log): "The integration tests are failing due to a
database initialization issue with SQLite's in-memory database ... only the test
database initialization needs to be fixed." completed=false.
```

Per the evaluate-run gate, build/test cannot execute against an empty workspace, and the stored `test_coverage` does not describe this archive. This run **fails the conformance and test gates**.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 |
| Files (total in workspace) | 7 (all metadata/logs) |
| Source files | 0 |
| Dependencies | 0 (no package.json) |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | n/a |
| Build duration | n/a |
| Agent API calls | 90 |
| Output tokens | 25,935 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Empty workspace — no source code delivered to the run directory
2. [high] Agent wrote files outside its workspace, polluting the user home directory (sandbox escape)
3. [high] `scores.json` does not reflect the archived workspace (spurious partial scores)
4. [high] Agent self-reports integration tests failing
5. [high] R1–R12 all missing from the workspace (12 requirement findings)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=typescript_prompt=neutral/rep3
find . -type f | sort                    # 7 files, none are source
ls README.md package.json src tests       # all absent
cat _agent_stdout.log                      # agent admits writing to /Users/adriancockcroft/book-api/
cat scores.json                            # spurious: test_coverage=0.6597 despite empty workspace
```
