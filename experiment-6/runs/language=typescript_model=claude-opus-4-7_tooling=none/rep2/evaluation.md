# Evaluation: language=typescript_model=claude-opus-4-7_tooling=none · rep 2

## Summary

- **Factors:** language=typescript, model=claude-opus-4-7, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 18 tests, 0 skipped (18 effective) — test_coverage=0.924 from retort.db
- **Build:** pass — defect_rate=1.0 from retort.db
- **Lint:** code_quality=0.733 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:65-76` — POST route accepts all four fields, inserts via SQLite, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:78-89` — returns all rows ordered by id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:79-84` — filters with `WHERE author = ?` when query param present |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:91-101` — returns book or 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:103-126` — validates input, updates row, returns updated book |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:128-138` — deletes row, returns 204 or 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1-24` — uses `better-sqlite3`, creates `books` table with `CREATE TABLE IF NOT EXISTS` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All routes return JSON; uses 200, 201, 204, 400, 404, 500 |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:19-49` — `validateBook` rejects missing/empty title or author with 400 |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:61-63` — returns `{"status":"ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 103 lines covering setup, run, dev mode, test, endpoints, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 18 tests covering all CRUD operations, validation, and health check |

## Build & Test

```text
# Build/test scores read from retort.db (not re-run per skill constraint)
test_coverage = 0.924
code_quality  = 0.733
defect_rate   = 1.0   (build + tests succeeded)
idiomatic     = 0.780
maintainability = 0.754
token_efficiency = 1.0
```

```text
# Test suite: jest --runInBand (18 tests, 0 skipped)
# Tests cover: health check, CRUD operations, validation (missing title/author,
# empty title, invalid year, optional fields), 404/400 error cases, author filter
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 338 (TypeScript) |
| Files (excluding node_modules/dist) | 14 |
| Dependencies | 12 (2 runtime + 10 dev) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [info] test_coverage scored 0.924 (not 1.0) — tests ran successfully but metric below perfect
2. [info] code_quality scored 0.733 — below 0.8 threshold, possible lint/style issues

## Reproduce

```bash
cd experiment-6/runs/language=typescript_model=claude-opus-4-7_tooling=none/rep2
cat stack.json
cat scores.json  # if present; otherwise query retort.db
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts" --include="*.js" 2>/dev/null | grep -v node_modules | wc -l
find . -name "*.ts" -not -path "*/node_modules/*" -not -path "*/dist/*" | xargs wc -l
```
