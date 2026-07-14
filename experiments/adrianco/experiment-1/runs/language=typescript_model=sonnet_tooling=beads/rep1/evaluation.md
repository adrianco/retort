# Evaluation: language=typescript_model=sonnet_tooling=beads · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — test_coverage=0.931, defect_rate=1.0 from retort.db
- **Lint:** pass — code_quality=0.733 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:15-32` — POST route accepts all four fields, persists via SQLite, returns 201; tested `src/app.test.ts:21-33` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:35-46` — returns all books ordered by id; tested `src/app.test.ts:52-59` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:38-41` — LIKE query on author param; tested `src/app.test.ts:61-69` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:49-55` — returns book or 404; tested `src/app.test.ts:73-87` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:58-89` — partial update with validation, returns 404 if absent; tested `src/app.test.ts:89-105` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:92-100` — deletes and returns 204, 404 if absent; tested `src/app.test.ts:107-123` |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1-31` — uses better-sqlite3, CREATE TABLE IF NOT EXISTS with proper schema |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `src/app.ts` throughout — 201 create, 200 read/update, 204 delete, 400 validation, 404 not found, 500 error handler |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:18-23` (POST), `src/app.ts:69-74` (PUT) — rejects empty/missing with 400; tested `src/app.test.ts:36-48` |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:10-12` — returns `{status: 'ok'}`; tested `src/app.test.ts:12-17` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — documents install, dev/prod run, endpoints table, curl examples, test command |
| R12 | At least 3 unit/integration tests | ✓ implemented | `src/app.test.ts` — 12 integration tests using supertest with in-memory SQLite |

## Build & Test

```text
Stored scores from retort.db (build/test not re-run per skill protocol):
  test_coverage  = 0.931  (build + tests passed)
  defect_rate    = 1.0    (build+test succeeded)
  code_quality   = 0.733
  maintainability = 0.649
  idiomatic      = 0.720
  token_efficiency = 0.500
```

```text
Test framework: Jest with ts-jest preset
Test file: src/app.test.ts
Test count: 12 (0 skipped)
Test strategy: supertest against in-memory SQLite (:memory:)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 151 (app.ts: 110, db.ts: 31, index.ts: 10) |
| Lines of code (incl. tests) | 274 |
| Files | 14 |
| Dependencies | 12 (2 prod, 10 dev) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (stored scores) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] jest.config.js uses deprecated ts-jest globals config
2. [low] LIKE filter uses wildcard-wrapped user input without escaping LIKE metacharacters

## Reproduce

```bash
cd experiment-1/runs/language=typescript_model=sonnet_tooling=beads/rep1
# Scores were read from retort.db — to re-run tests manually:
npm install
npm test
```
