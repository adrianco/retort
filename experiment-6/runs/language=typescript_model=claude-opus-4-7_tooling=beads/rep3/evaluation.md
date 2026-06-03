# Evaluation: language=typescript_model=claude-opus-4-7_tooling=beads · rep 3

## Summary

- **Factors:** language=typescript, model=claude-opus-4-7, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — test_coverage=0.9157 from retort.db (defect_rate=1.0)
- **Lint:** code_quality=0.7333 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:20-27` POST route; `src/db.ts:36-47` create method; `tests/books.test.ts:21-32` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:29-32` GET route; `src/db.ts:49-56` list method; `tests/books.test.ts:59-67` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:30` reads `req.query.author`; `src/db.ts:50-55` SQL WHERE clause; `tests/books.test.ts:68-72` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:34-44` with 404 handling; `src/db.ts:58-62` getById; `tests/books.test.ts:76-89` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:46-60` with validation and 404; `src/db.ts:64-72` update; `tests/books.test.ts:92-119` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:62-72` with 404; `src/db.ts:74-78` delete; `tests/books.test.ts:123-138` |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1` imports `better-sqlite3`; `src/db.ts:18-31` creates SQLite table with schema |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create (`app.ts:26`), 200 read/update, 204 delete (`app.ts:71`), 400 validation (`app.ts:23`), 404 not found |
| R9 | Input validation: title and author required | ✓ implemented | `src/validation.ts:19-24` checks both fields; `tests/books.test.ts:34-48` tests missing title and author |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:16-18` returns `{status:'ok'}`; `tests/books.test.ts:12-16` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` covers setup (`npm install`), run (`npm start`/`npm run dev`), test (`npm test`), endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | 13 test cases in `tests/books.test.ts` covering all endpoints, validation, and error paths |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage  = 0.9157  (tests executed and passed)
  defect_rate    = 1.0     (build + test succeeded)
  code_quality   = 0.7333  (lint/quality score)
  idiomatic      = 0.87
  maintainability = 0.6735
  token_efficiency = 1.0
```

```text
Test framework: Jest (via ts-jest)
Test command: jest --runInBand
13 test cases across 6 describe blocks:
  GET /health (1 test)
  POST /books (4 tests — create, missing title, missing author, non-integer year)
  GET /books (1 test — list all + author filter)
  GET /books/:id (2 tests — found, 404)
  PUT /books/:id (3 tests — update, 404, invalid body)
  DELETE /books/:id (2 tests — delete + re-fetch 404, 404 unknown)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 229 (src: 229, tests: 138, config: 8) |
| Files | 18 |
| Dependencies | 12 (2 runtime + 10 dev) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | scored by retort (not re-run) |

## Findings

No findings. All 12 requirements are fully implemented with tests.

## Reproduce

```bash
cd experiment-6/runs/language=typescript_model=claude-opus-4-7_tooling=beads/rep3
cat stack.json
cat TASK.md
# Scores were read from retort.db, not re-run
# To verify manually:
# npm install && npm test
```
