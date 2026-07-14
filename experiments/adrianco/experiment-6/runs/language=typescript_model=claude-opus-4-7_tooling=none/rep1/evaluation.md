# Evaluation: language=typescript_model=claude-opus-4-7_tooling=none · rep 1

## Summary

- **Factors:** language=typescript, model=claude-opus-4-7, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 defined / 0 skipped (13 effective) — test_coverage=0.8941 from retort.db
- **Build:** pass — defect_rate=1.0 from retort.db
- **Lint:** code_quality=0.7333 from retort.db
- **Architecture:** summary skill not invoked
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:69-83` — INSERT with all four fields, returns 201 with created book |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:85-96` — SELECT * FROM books ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:87-91` — filters with WHERE author = ? when query param present |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:98-108` — returns book or 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:110-133` — partial update with merge, returns 200 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:136-146` — DELETE with 204 on success, 404 if missing |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1-24` — better-sqlite3, CREATE TABLE books, WAL mode |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 (create), 200 (read/update), 204 (delete), 400 (validation), 404 (not found), 500 (error) |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:22-29,31-38` — validateBook rejects missing/empty title and author with 400 |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:65-67` — returns `{"status":"ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup, Run, Test, Endpoints sections with examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 13 test cases covering all endpoints |

## Build & Test

```text
Stored scores from retort.db (build/test not re-run):
  test_coverage  = 0.8941
  code_quality   = 0.7333
  defect_rate    = 1.0
  maintainability = 0.6761
  idiomatic      = 0.3500
  token_efficiency = 1.0
```

```text
Test file: tests/books.test.ts (13 test cases, 0 skipped)
  GET /health — 1 test
  POST /books — 3 tests (create, reject missing title, reject missing author)
  GET /books — 2 tests (empty list, list + author filter)
  GET /books/:id — 2 tests (found, 404)
  PUT /books/:id — 3 tests (update, 404, reject empty title)
  DELETE /books/:id — 2 tests (delete + verify 404, 404 on missing)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 190 |
| Lines of code (tests) | 154 |
| Files (excl. node_modules/dist) | 14 |
| Dependencies | 12 (2 runtime + 10 dev) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Partial update support in PUT /books/{id} — enhancement beyond spec
2. [info] Comprehensive input type validation beyond spec — year, isbn, id type checks
3. [info] Global error-handling middleware — catches unhandled errors with 500 JSON

## Reproduce

```bash
cd experiment-6/runs/language=typescript_model=claude-opus-4-7_tooling=none/rep1
cat stack.json
cat TASK.md
# Scores were read from retort.db, not re-run
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='typescript' AND json_extract(er.run_config_json,'\$.model')='claude-opus-4-7' AND json_extract(er.run_config_json,'\$.tooling')='none' AND er.replicate=1 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -rE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' tests/ --include='*.ts' | wc -l
```
