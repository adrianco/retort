# Evaluation: agent=codex model=gpt-5.6-terra language=typescript prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-5.6-terra, agent=codex, prompt=neutral, effort=default
- **Task type:** REPAIR (a prior attempt failed to build/test; this workspace is the fix)
- **Status:** ok — clean pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from stored `scores.json` (`test_coverage=1.0`, `defect_rate=1.0`; not re-run per skill)
- **Lint:** pass — `code_quality=0.73` from `scores.json`
- **Architecture:** inlined below (`run-summary` skill not registered in this environment)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:126-136` INSERT with all four fields, 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:83-89` SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:84-87` WHERE author = ? branch; test at `test/books.test.ts:85` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/app.ts:96-97` returns row or 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:105-123` UPDATE, 200 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:99-104` DELETE, 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/app.ts:2,62` `node:sqlite` DatabaseSync + CREATE TABLE |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `sendJson` helper; 201/200/204/400/404 throughout |
| R9 | Input validation: title & author required | ✓ implemented | `src/app.ts:128-129` reject with 400; test at `test/books.test.ts:98` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:79-81` returns `{status:'ok'}` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` Setup/Run/Endpoints sections |
| R12 | At least 3 tests | ✓ implemented | 3 `test(...)` blocks in `test/books.test.ts`, 0 skipped |

## Build & Test

Not re-run — stored scores used per evaluate-run skill (step 2):

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.7333
              maintainability=0.8166  idiomatic=0.89  token_efficiency=0.0159
```

`test_coverage=1.0` ⇒ build succeeded and all tests executed and passed. The tests
drive the real HTTP handler in-process against an in-memory SQLite DB
(`:memory:`), covering health, create/get, list+filter, validation, update, delete.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 155 (src) + 124 (test) = 279 |
| Files | 3 (app.ts, server.ts, books.test.ts) |
| Dependencies | 0 external (Node built-ins only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Architecture (inlined)

- `src/app.ts` — `createApp(options)` builds a `node:http` server bound to a
  `node:sqlite` `DatabaseSync`. All routing is a single request handler with regex
  matching on `/books/(\d+)`. Helpers: `sendJson`, `isNonEmptyString`,
  `validateOptionalFields`, `readJson`, `parseId`. Table created idempotently.
- `src/server.ts` — thin entrypoint; reads `PORT`/`DATABASE_PATH` env and calls
  `server.listen`.
- `test/books.test.ts` — uses `node:test`, fabricates request/response objects and
  emits `'request'` on the server, so no socket is opened. Clean separation of app
  factory from listener enables fast in-process tests.

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] N1 — Zero external dependencies; note `node:sqlite` is experimental (Node >=22.5)
2. [low] N2 — Redundant `typeof` guard alongside `Number.isInteger` (`src/app.ts:33`)
3. [info] N3 — PUT response built from validated input rather than re-read from DB

No critical/high/medium findings. This is a clean pass.

## Reproduce

```bash
cd experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=typescript_model=gpt-5.6-terra_prompt=neutral/rep1
cat scores.json                                   # stored build/test scores
grep -rE "\.skip\(|xit\(|it\.todo\(" test src     # 0 skips
grep -cE "^test\(" test/books.test.ts             # 3 tests
# to actually run: npm test   (requires Node >=22.6 for TS + node:sqlite)
```
