# Evaluation: typescript · hermes-local · Qwen3-Coder-Next-4bit (m80) · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok (delivers a complete, well-structured API) but **build fails** and **most tests do not execute**
- **Requirements:** 12/12 implemented in source, 0 partial, 0 missing — but 2 of 3 test suites are broken (see Findings)
- **Tests:** ~10 passed / ~28 fail-to-load / 0 skipped (10 effective — only `tests/database.test.ts` runs). `test_coverage=0.2645` (scores.json)
- **Build:** fail — `tsc` errors on `src/server.ts` (TS2349, express() not callable); agent-reported and unfixed
- **Lint:** unavailable (no lint run recorded; `code_quality=0.7333` from scores.json)
- **Architecture:** run-summary skill not available — layered layout described inline below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 2 high, 1 medium, 1 low)

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (constant denominator, 12 requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/routes/book.routes.ts:51`, `database.ts:createBook` (201) |
| R2 | GET /books lists all | ✓ implemented | `book.routes.ts:17`, `database.ts:getAllBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `book.routes.ts:19`, `database.ts:71` (`WHERE author = ?`) |
| R4 | GET /books/{id} single (404) | ✓ implemented | `book.routes.ts:29` (404 at :39) |
| R5 | PUT /books/{id} updates | ✓ implemented | `book.routes.ts:63`, `database.ts:updateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `book.routes.ts:87` (204/404) |
| R7 | SQLite / embedded DB | ✓ implemented | `database.ts:1` `sqlite3`, `book.routes.ts:6` `./books.db` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/204/500 across `book.routes.ts` |
| R9 | Validation: title & author required | ✓ implemented | `src/middleware/validation.ts:28-36` (400) |
| R10 | GET /health | ✓ implemented | `book.routes.ts:12` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, endpoints) — minor: lists nonexistent `src/models/` |
| R12 | ≥3 unit/integration tests that run | ✓ implemented | `tests/database.test.ts` (10 tests) runs; `test_coverage=0.2645>0`. NB two other suites fail to load — see Findings |

All 12 requirements are satisfied at the source level. The deductions are quality/execution defects (build + test wiring), not missing features.

## Build & Test

```text
npm run build   (tsc)
src/server.ts:4  error TS2349: This expression is not callable.
  Type 'typeof e' has no call signatures.   ← import * as express + express()
```
Agent's own `_agent_stdout.log` reports this error and lists "Fix the express import" as remaining work.

```text
jest --runInBand
tests/database.test.ts        ....... PASS (10 tests, in-memory sqlite)
tests/unit/validation.test.ts        FAIL — Cannot find module '../src/middleware/validation'
tests/integration/api.test.ts        FAIL — Cannot find module '../src/server'
scores.json: test_coverage=0.2645
```
Nested test files use `../src/...` where `../../src/...` is required (they sit in `tests/unit/` and `tests/integration/`). node_modules was not archived, so the toolchain was not re-run for this evaluation; assessment is from static analysis + the stored `scores.json`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+tests, .ts) | 929 |
| Files (excl. node_modules/dist/lockfile) | 20 |
| Dependencies (prod+dev) | 11 |
| Tests total (`it`/`test` blocks) | 38 |
| Tests effective (actually load/run) | 10 (database.test.ts only) |
| Skipped tests | 0 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] `build-fail` — server.ts `import * as express` + `express()` → TS2349; build/start fail (agent-reported, unfixed).
2. [high] `test-import-paths` — nested test files import `../src/...` instead of `../../src/...`; 28/38 tests never load.
3. [medium] `test-mock-singleton` — route module instantiates its DB at import; integration `jest.mock` cannot swap it, so API tests would read the real DB.
4. [low] `readme-structure` — README lists `src/models/book.model.ts`, which does not exist.

## Reproduce

```bash
cd "experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep2"
cat scores.json                 # test_coverage=0.2645, code_quality=0.7333, defect_rate=1.0
cat _agent_stdout.log           # agent reports the TS2349 express error, unfixed
# static: server.ts:1,4 express import; tests/unit + tests/integration use ../src (wrong depth)
```
