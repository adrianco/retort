# Evaluation: language=typescript_model=opus_tooling=beads · rep 3

## Summary

- **Factors:** language=typescript, model=opus, tooling=beads
- **Status:** failed (tests — test_coverage=0.0862 from retort.db; prior eval confirmed exit code 1)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 0 passed / 1 suite failed / 0 skipped (7 test cases defined but suite did not execute)
- **Build:** pass — defect_rate=1.0 from retort.db
- **Lint:** code_quality=0.7333 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/app.ts:20-36` — INSERT with all four fields, returns 201; test at `tests/books.test.ts:18` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:38-49` — SELECT * FROM books, returns 200; test at `tests/books.test.ts:41` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:40-44` — WHERE author = ? when query param present; test at `tests/books.test.ts:51` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/app.ts:51-61` — returns book or 404; test at `tests/books.test.ts:57` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:63-92` — partial UPDATE with 404 if absent; test at `tests/books.test.ts:70` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:94-104` — DELETE with 204/404; test at `tests/books.test.ts:83` |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:1` — uses better-sqlite3; `src/server.ts:7` defaults to `books.db` file |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 (create), 200 (read/update), 204 (delete), 400 (validation), 404 (not found) |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:22-27` — rejects missing/empty title or author with 400; test at `tests/books.test.ts:33` |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:16-18` — returns `{"status":"ok"}` with 200; test at `tests/books.test.ts:11` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — documents install, build, start, dev, test, and all endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 7 integration tests using supertest (but suite failed to execute) |

## Build & Test

```text
Stored scores from retort.db (build/test not re-run):
  test_coverage    = 0.0862
  code_quality     = 0.7333
  defect_rate      = 1.0
  maintainability  = 0.6865
  idiomatic        = 0.77
  token_efficiency = 0.5
```

```text
Prior evaluation test run:
  Command: npm test --silent
  Exit code: 1
  Results: 0 passed, 1 suite failed, 0 skipped
  Likely cause: better-sqlite3 native module build failure (node-gyp)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 232 (TS/JS) |
| Files | 16 |
| Dependencies | 12 (2 runtime, 10 dev) |
| Tests total | 7 |
| Tests effective | 0 (suite failed to execute) |
| Skip ratio | 0% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] Test suite failed (exit code 1) — test_coverage=0.0862; npm test returned 1 suite failure
2. [info] Jest coverage not configured — no collectCoverage in jest.config.js

## Reproduce

```bash
cd experiment-1/runs/language=typescript_model=opus_tooling=beads/rep3
cat stack.json
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='typescript' AND json_extract(er.run_config_json,'$.model')='opus' AND json_extract(er.run_config_json,'$.tooling')='beads' AND er.replicate=3 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -rE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' . --include='*.ts' --include='*.js'
```
