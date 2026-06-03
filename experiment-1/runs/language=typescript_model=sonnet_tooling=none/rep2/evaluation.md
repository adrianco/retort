# Evaluation: language=typescript_model=sonnet_tooling=none · rep 2

## Summary

- **Factors:** language=typescript, model=sonnet, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — test_coverage=0.8939, defect_rate=1.0 from retort.db
- **Lint:** code_quality=0.733 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 0 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:15-39` — POST route accepts all four fields, inserts via prepared statement, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:42-56` — returns full collection as JSON array |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:46-50` — LIKE query on author param |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:59-74` — returns book or 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:77-115` — partial update with validation, returns 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:118-131` — deletes and returns 204, or 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1,18` — uses `node:sqlite` DatabaseSync; `src/index.ts:7` persists to `books.db` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | Routes return 200/201/204/400/404/500 with JSON bodies throughout `src/app.ts` |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:18-23` — rejects missing/empty title or author with 400 |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:10-12` — returns `{"status":"ok"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — covers setup, run (dev + production), API endpoints, and tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 12 integration tests via supertest covering all endpoints |

## Build & Test

```text
Build/test scores read from retort.db (not re-run per skill policy):
  test_coverage   = 0.8939
  code_quality    = 0.7333
  defect_rate     = 1.0     (build + tests succeeded)
  maintainability = 0.6093
  idiomatic       = 0.6800
  token_efficiency= 0.5000
```

```text
Test suite: tests/books.test.ts
  12 test cases across 6 describe blocks:
    GET /health (1), POST /books (3), GET /books (2),
    GET /books/:id (2), PUT /books/:id (2), DELETE /books/:id (2)
  0 skipped tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 185 (app.ts:141, db.ts:32, index.ts:12) |
| Lines of test code | 137 |
| Files | 9 |
| Dependencies | 9 (1 runtime + 8 dev) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (scores from DB) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] README references better-sqlite3 but code uses node:sqlite

## Reproduce

```bash
cd experiment-1/runs/language=typescript_model=sonnet_tooling=none/rep2
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT ..."
cat TASK.md
cat src/app.ts src/db.ts src/index.ts
cat tests/books.test.ts
grep -rE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' . --include='*.ts' | wc -l
```
