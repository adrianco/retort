# Evaluation: agent=hermes-local_language=typescript_prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, agent=hermes-local (model=Qwen3-Coder-Next), prompt=neutral, framework=unknown
- **Status:** failed (deliverables written outside the workspace) — the archived run_dir contains **no source, README, or tests**. The agent wrote all files to the hardcoded external path `/Users/adriancockcroft/code/book-api/`. Functional assessment below is against that external code (read-only cross-reference); it is **not** part of the archive.
- **Requirements:** 12/12 implemented in the produced code, 0 partial, 0 missing — **but none delivered to the workspace** (see critical finding).
- **Tests:** ~69% pass rate (scores.json test_coverage=0.6917); 48 test cases exist, 0 skipped; agent stopped incomplete with failing validation tests.
- **Build:** pass at external path (defect_rate=1.0) — **not buildable from the archive** (no package.json/src in run_dir).
- **Lint:** code_quality=0.7333 (scores.json)
- **Architecture:** workspace empty — run-summary not applicable; code lives at external `/Users/adriancockcroft/code/book-api/`.
- **Findings:** 4 items in `findings.jsonl` (1 critical, 0 high, 1 medium, 1 low, 1 info)

## Requirements

Assessed against the code the agent actually produced (external `book-api/`, read-only). All are functionally present but **absent from the archived workspace**.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `controller.ts` createBook → `repo.create`; router POST /books |
| R2 | GET /books lists all | ✓ implemented | `controller.ts` getAllBooks → `repo.findAll`; router GET /books |
| R3 | GET /books ?author= filter | ✓ implemented | `database.ts` findAll uses `WHERE author LIKE ?`; test `should filter books by author` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `controller.ts` getBookById returns 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `controller.ts` updateBook → `repo.update`; partial-field update supported |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `controller.ts` deleteBook → `repo.delete`, 204/404 |
| R7 | Data in SQLite | ✓ implemented | `database.ts` uses `sqlite3` Database + CREATE TABLE books |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/204/500 across `controller.ts` |
| R9 | Validation: title+author required | ✓ implemented | `controller.ts`/`validation.ts` push 400 errors for missing title/author (also year/isbn — stricter, see E1) |
| R10 | GET /health | ✓ implemented | `controller.ts` router GET /health returns `{status:'ok'}` |
| R11 | README with setup/run | ✓ implemented (external only) | `book-api/README.md` present; **not in archive** |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 test files, 48 `it()` cases, 0 skipped; test_coverage=0.6917>0 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 0.6917   # ~69% of tests pass; build ran, some tests failing
defect_rate     = 1.0      # build + test executed successfully (at external path)
code_quality    = 0.7333
maintainability = 0.7677
idiomatic       = 0.65
token_efficiency= 1.0
```

Archive is not buildable — `run_dir` has no `package.json`, `tsconfig.json`, or `src/`.
Agent transcript (`_agent_stdout.log`) admits failing validation tests and ends by asking to continue; `.hermes_usage.json` reports `completed: false`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code in archive (source) | 0 |
| Lines of code at external path (source) | 413 (`server`+`controller`+`database`+`validation`) |
| Lines of code at external path (tests) | 738 |
| Files in archive (excl. logs/meta) | 0 source |
| Dependencies (external package.json) | 3 runtime, 10 dev |
| Tests total | 48 |
| Tests effective (passed+failed) | 48 (0 skipped) |
| Skip ratio | 0% |
| Est. tests passing | ~69% (test_coverage=0.6917) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [critical] Deliverables written outside the workspace — archive has no source/README/tests; code exists only at hardcoded `/Users/adriancockcroft/code/book-api/`. Run is not reproducible or buildable from its archive.
2. [medium] Not all tests pass; agent stopped mid-task with failing validation tests (test_coverage=0.6917, completed=false).
3. [low] `validateBookInput` middleware defined but never wired into the router; createBook duplicates validation inline.
4. [info] Validation stricter than spec — year and isbn treated as required though only title+author are mandated.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-22-qwennext80b/bookshop/runs/agent=hermes-local_language=typescript_prompt=neutral/rep3
cat scores.json _meta.json _agent_stdout.log
find . -type f            # only TASK.md, logs, meta, scores, stack.json — no source
# Cross-reference (read-only) where the agent actually wrote:
find /Users/adriancockcroft/code/book-api/src -type f
```
