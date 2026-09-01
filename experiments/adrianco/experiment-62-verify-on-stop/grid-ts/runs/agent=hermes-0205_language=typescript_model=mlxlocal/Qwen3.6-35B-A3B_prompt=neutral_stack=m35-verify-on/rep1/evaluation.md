# Evaluation: typescript · hermes-0205 · Qwen3.6-35B-A3B · m35-verify-on · rep 1

## Summary

- **Factors:** language=typescript, agent=hermes-0205, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35-verify-on
- **Status:** ok — full spec implemented, build + tests verified
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (matches `requirement_coverage=1.0` in retort.db)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — `defect_rate=1.0` from retort.db (build + test succeeded; agent verify-on-stop confirmed clean `tsc` + all 16 jest tests)
- **Lint:** n/a — `code_quality=0.717` from retort.db
- **Architecture:** single Express app module (`src/app.ts`) + server bootstrap (`src/server.ts`); `run-summary` skill not available in this session
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `src/app.ts:29-41` INSERT + 201 with full row |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:51-52` SELECT * FROM books |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:46-49` WHERE author = ? |
| R4 | GET /books/{id} single book, 404 if absent | ✓ implemented | `src/app.ts:55-63` get-by-id + 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:65-84` UPDATE, 404 + 400 guards |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:86-95` DELETE + 204 / 404 |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `better-sqlite3` in package.json; `src/server.ts:5-15` file-backed db + schema |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/404/400/204/500 across `src/app.ts` |
| R9 | Validation: title & author required | ✓ implemented | `src/app.ts:32-34` (POST) and `74-76` (PUT) → 400 |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:25-27` returns `{status:'ok'}` 200 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — setup, build, start, dev, test, full endpoint docs |
| R12 | >= 3 unit/integration tests | ✓ implemented | `tests/app.test.ts` — 16 tests, 0 skipped |

## Build & Test

Not re-run — stored scores used (per skill Step 2).

```text
retort.db: defect_rate=1.0  (build + test succeeded)
retort.db: requirement_coverage=1.0
_agent_stdout.log: "Build and tests verified — clean compile, all 16 tests passing"
```

Test breakdown (from `tests/app.test.ts`, confirmed by verify-on-stop log):
GET /health (1), POST /books (5), GET /books (3), GET /books/:id (2), PUT /books/:id (3), DELETE /books/:id (2) = 16.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 338 (app 106, server 24, tests 208) |
| Files | 3 source/test (+ config: package.json, tsconfig, jest.config) |
| Dependencies | 12 (2 runtime, 10 dev) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| test_coverage (retort.db) | 0.354 (coverage-ratio metric; not a pass/fail gate) |
| Duration | 365s / 27 turns (retort.db) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] server.ts mixes ES `import` and `require('./app')` for the same module — `src/server.ts:3` vs `src/server.ts:20`
2. [info] Test suite (16 tests) far exceeds the 3-test minimum (R12)

## Reproduce

```bash
cd "$(dirname "$0")"
# scores read from archive / retort.db, not re-run:
cat scores.json
# to verify locally:
npm install && npm run build && npm test
```
