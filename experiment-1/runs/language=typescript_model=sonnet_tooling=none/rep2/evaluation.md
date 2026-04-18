# Evaluation: language=typescript_model=sonnet_tooling=none · rep 2

## Summary

- **Factors:** language=typescript, model=sonnet, tooling=none
- **Status:** ok
- **Requirements:** 13/13 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — 2s
- **Lint:** unavailable — N/A
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|---|
| R1 | POST /books — Create a new book | ✓ implemented | `src/app.ts:15-40`, test `POST /books.creates a book and returns 201` |
| R2 | GET /books — List all books with author filter | ✓ implemented | `src/app.ts:43-56`, test `GET /books.filters by author` |
| R3 | GET /books/{id} — Get a single book by ID | ✓ implemented | `src/app.ts:59-74`, test `GET /books/:id.returns a single book` |
| R4 | PUT /books/{id} — Update a book | ✓ implemented | `src/app.ts:77-115`, test `PUT /books/:id.updates a book` |
| R5 | DELETE /books/{id} — Delete a book | ✓ implemented | `src/app.ts:118-131`, test `DELETE /books/:id.deletes a book and returns 204` |
| R6 | Use the specified language and framework | ✓ implemented | TypeScript + Express confirmed in package.json |
| R7 | Store data in SQLite | ✓ implemented | `src/db.ts:1-32` uses `DatabaseSync` from node:sqlite |
| R8 | Return JSON responses with HTTP status codes | ✓ implemented | All endpoints use proper status codes (201, 400, 404, 204) |
| R9 | Input validation (title and author required) | ✓ implemented | `src/app.ts:18-23` validates both fields with empty string checks |
| R10 | Health check endpoint GET /health | ✓ implemented | `src/app.ts:10-12`, test `GET /health.returns 200 with status ok` |
| R11 | Working source code | ✓ implemented | Source code builds and passes all tests |
| R12 | README.md with setup and run instructions | ✓ implemented | README.md provided with clear setup and run commands |
| R13 | At least 3 unit/integration tests | ✓ implemented | 12 comprehensive tests covering all endpoints |

## Build & Test

```text
npm run build
> book-collection-api@1.0.0 build
> tsc
[Build succeeded with no output]
```

```text
npm test
> book-collection-api@1.0.0 test
> jest --forceExit

PASS tests/books.test.ts
  GET /health
    ✓ returns 200 with status ok (106 ms)
  POST /books
    ✓ creates a book and returns 201 (17 ms)
    ✓ returns 400 when title is missing (5 ms)
    ✓ returns 400 when author is missing (4 ms)
  GET /books
    ✓ returns all books (9 ms)
    ✓ filters by author (12 ms)
  GET /books/:id
    ✓ returns a single book (5 ms)
    ✓ returns 404 for unknown id (2 ms)
  PUT /books/:id
    ✓ updates a book (6 ms)
    ✓ returns 404 for unknown id (2 ms)
  DELETE /books/:id
    ✓ deletes a book and returns 204 (6 ms)
    ✓ returns 404 when book does not exist (3 ms)

Test Suites: 1 passed, 1 total
Tests:       12 passed, 12 total
Snapshots:   0 total
Time:        3.895 s
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 156 |
| Files (excluding build artifacts) | 10 |
| Dependencies | 9 |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | 2s |

## Findings

Full list in `findings.jsonl`:

- [info] Stack metadata incomplete — agent and framework marked as unknown
- [info] Experimental SQLite feature — Node.js warns that node:sqlite is experimental

## Reproduce

```bash
cd experiment-1/runs/language=typescript_model=sonnet_tooling=none/rep2
npm install --no-audit --no-fund
npm run build
npm test
```
