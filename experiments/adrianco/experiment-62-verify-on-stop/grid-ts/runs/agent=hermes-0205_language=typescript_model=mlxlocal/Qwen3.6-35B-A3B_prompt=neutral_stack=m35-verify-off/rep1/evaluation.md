# Evaluation: agent=hermes-0205 · model=mlxlocal/Qwen3.6-35B-A3B · stack=m35-verify-off · rep 1

## Summary

- **Factors:** language=typescript, agent=hermes-0205, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35-verify-off
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 23 passed / 0 failed / 0 skipped (23 effective)
- **Build:** pass (defect_rate=1.0 from scores.json — build + tests succeeded)
- **Lint:** pass — code_quality=0.717 from scores.json
- **Architecture:** two-layer Express app — `src/index.ts` (routes/validation) over `src/database.ts` (better-sqlite3 CRUD). run-summary skill not invoked (unavailable); structure documented inline here.
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/index.ts:23`; `database.ts:createBook`; test `tests/index.test.ts:45` |
| R2 | GET /books lists all | ✓ implemented | `src/index.ts:63`; `database.ts:getAllBooks`; test :141 |
| R3 | GET /books ?author= filter | ✓ implemented | `src/index.ts:64,73`; `database.ts:45-48`; test :148 |
| R4 | GET /books/{id} by id (404 if absent) | ✓ implemented | `src/index.ts:78-98`; test :175,:182 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/index.ts:101`; `database.ts:updateBook` (partial update supported); test :217,:233 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/index.ts:164`; `database.ts:deleteBook`; test :270,:275 |
| R7 | SQLite / embedded DB | ✓ implemented | `src/database.ts:1,9` better-sqlite3, persistent `books.db` file |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/400/204 throughout `src/index.ts` |
| R9 | Validation: title & author required | ✓ implemented | `src/index.ts:27-39`; test :62,:70,:78,:86 |
| R10 | GET /health | ✓ implemented | `src/index.ts:18`; test :36 |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, setup, run, dev, testing sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 23 tests in `tests/index.test.ts`, all passing |

## Build & Test

Build/test not re-run — stored scores used (per skill Step 2).

```text
scores.json: defect_rate=1.0 → build + tests succeeded
             test_coverage=0.354  code_quality=0.717  maintainability=0.808  idiomatic=0.70
jest --coverage: 23 tests passing, 0 skipped
```

Note: `jest.config.js` excludes `src/index.ts` from `collectCoverageFrom`, so `coverage/lcov.info`
instruments only `src/database.ts` (47/48 lines = 97.9%). The route handlers are exercised through
supertest but not instrumented, which is why the retort `test_coverage` metric sits at 0.354 despite
a passing, well-covered suite. See finding COV1.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 319 (src) + 285 (tests) |
| Files (excl node_modules/coverage) | 19 |
| Dependencies | 12 |
| Tests total | 23 |
| Tests effective | 23 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] COV1 — `src/index.ts` (all route handlers) excluded from coverage collection via `jest.config.js:9`, so the API layer is untracked and retort `test_coverage` reads 0.354.
2. [info] R7-note — SQLite persistence adds WAL mode and a UNIQUE isbn constraint (enhancement beyond spec).
3. [info] R8-note — Extra validation (year range, positive-integer id) beyond required title/author checks.

## Reproduce

```bash
cd "experiments/adrianco/experiment-62-verify-on-stop/grid-ts/runs/agent=hermes-0205_language=typescript_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35-verify-off/rep1"
cat scores.json                      # stored mechanical scores (build/test/lint)
cat stack.json _meta.json            # factor levels + run status
grep -cE "^\s*test\(" tests/index.test.ts   # 23 tests
grep -E "^(SF|LF|LH):" coverage/lcov.info   # coverage instruments only database.ts
```
