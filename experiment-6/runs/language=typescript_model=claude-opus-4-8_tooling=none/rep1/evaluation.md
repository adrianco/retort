# Evaluation: language=typescript_model=claude-opus-4-8_tooling=none · rep 1

## Summary

- **Factors:** language=typescript, model=claude-opus-4-8, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — tsc compiles cleanly (exit 0 from prior scoring run)
- **Lint:** unavailable — no linter configured in package.json
- **Architecture:** see `summary/index.md` (if generated)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:69-76` route + `src/db.ts:40-51` BookRepository.create; test: `test/books.test.ts:25-35` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:79-83` route + `src/db.ts:53-60` BookRepository.list; test: `test/books.test.ts:50-53` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:80-82` reads query.author + `src/db.ts:55-58` SQL WHERE; test: `test/books.test.ts:54-58` |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `src/app.ts:86-95` route returns 200 or 404; test: `test/books.test.ts:60-69` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:98-113` route validates + updates; test: `test/books.test.ts:71-86` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:116-126` route returns 204 or 404; test: `test/books.test.ts:88-99` |
| R7 | Data stored in SQLite (embedded DB) | ✓ implemented | `src/db.ts:1` uses `node:sqlite` DatabaseSync; `src/db.ts:25-34` CREATE TABLE books |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | Routes return 201 (create), 200 (read/update), 204 (delete), 400 (validation), 404 (not found) |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:15-51` validateBook rejects missing/empty title & author with 400; test: `test/books.test.ts:37-43` |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/app.ts:64-66` returns `{status: "ok"}` 200; test: `test/books.test.ts:19-23` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — setup, run, dev, test, API docs with examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 integration tests in `test/books.test.ts` using supertest — all pass |

## Build & Test

```text
npm install --no-audit --no-fund && npm run build
Exit code: 0 (from prior scoring run — build succeeded, tsc compiled cleanly)
```

```text
npm test --silent
Exit code: 0
✔ GET /health returns ok (10.4ms)
✔ POST /books creates a book and returns 201 (6.0ms)
✔ POST /books rejects missing title and author with 400 (1.3ms)
✔ GET /books lists books and supports ?author= filter (3.7ms)
✔ GET /books/:id returns a single book or 404 (2.1ms)
✔ PUT /books/:id updates an existing book (2.0ms)
✔ DELETE /books/:id removes a book (2.4ms)
tests 7 | pass 7 | fail 0 | skipped 0 | duration_ms 205
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 331 (4 .ts files) |
| Files (excl. node_modules/dist) | 16 |
| Dependencies | 7 (1 runtime + 6 dev) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0.0% |
| Build duration | ~0.9s (prior run) |

## Findings

Top 1 by severity (full list in `findings.jsonl`):

1. [info] Uses experimental node:sqlite module — `src/db.ts:1`; runtime warning emitted but functional

## Reproduce

```bash
cd experiment-6/runs/language=typescript_model=claude-opus-4-8_tooling=none/rep1
npm install --no-audit --no-fund
npm run build
npm test
```
