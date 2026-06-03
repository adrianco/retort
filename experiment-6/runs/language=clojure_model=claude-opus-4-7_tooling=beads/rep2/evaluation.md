# Evaluation: language=clojure_model=claude-opus-4-7_tooling=beads · rep 2

## Summary

- **Factors:** language=clojure, model=claude-opus-4-7, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — test_coverage=1.0 from retort.db (build+tests succeeded)
- **Lint:** code_quality=0.833 from retort.db
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/books/handler.clj:31-38` create-book-handler; `src/books/db.clj:40-48` create-book; tested in `create-and-fetch-book` |
| R2 | GET /books lists all books | ✓ implemented | `src/books/handler.clj:40-43` list-books-handler; `src/books/db.clj:50-55` list-books; tested in `list-and-filter-books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/books/handler.clj:42` extracts "author" query-param; `src/books/db.clj:53` WHERE author = ?; tested at `handler_test.clj:68` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/books/handler.clj:46-51` get-book-handler with 404; `src/books/db.clj:57-58` get-by-id; tested in `create-and-fetch-book` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/books/handler.clj:53-64` update-book-handler with validation+404; `src/books/db.clj:60-71` update-book; tested in `update-and-delete-book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/books/handler.clj:66-70` delete-book-handler returns 204; `src/books/db.clj:73-76` delete-book; tested in `update-and-delete-book` |
| R7 | Data stored in SQLite | ✓ implemented | `src/books/db.clj:6-7` dbtype "sqlite"; `deps.edn` org.xerial/sqlite-jdbc dependency |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `src/books/handler.clj:9-13` json-response helper; `handler.clj:86-88` wrap-json-body/wrap-json-response middleware; codes: 201, 200, 204, 400, 404 |
| R9 | Input validation: title and author required | ✓ implemented | `src/books/handler.clj:18-29` validate-book checks nil/blank; tested in `validation-errors` deftest |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/books/handler.clj:73-74` health-handler returns {:status "ok"}; route at line 78; tested in `health-endpoint` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents Java 11+ prereq, `clojure -M:run`, `clojure -M:test`, endpoints table, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 5 deftest blocks in `test/books/handler_test.clj`: health-endpoint, create-and-fetch-book, list-and-filter-books, update-and-delete-book, validation-errors; test_coverage=1.0 |

## Build & Test

```text
Build+test result from retort.db (not re-run):
  test_coverage  = 1.0   (build + all tests passed)
  code_quality   = 0.833
  defect_rate    = 1.0   (build+test succeeded)
  maintainability= 0.943
  idiomatic      = 0.88
```

```text
Test command: clojure -M:test
5 deftest blocks, 0 skipped, 0 failures (per test_coverage=1.0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 176 |
| Lines of code (tests) | 103 |
| Files (excluding tooling/cache) | 13 |
| Dependencies (main) | 8 |
| Dependencies (test) | 2 |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (stored score) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Year type validation beyond spec — `src/books/handler.clj:26-27`

## Reproduce

```bash
cd experiment-6/runs/language=clojure_model=claude-opus-4-7_tooling=beads/rep2
cat scores.json 2>/dev/null || echo "scores.json absent — use retort.db"
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='clojure' AND json_extract(er.run_config_json,'$.model')='claude-opus-4-7' AND json_extract(er.run_config_json,'$.tooling')='beads' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
cat REQUIREMENTS.json
clojure -M:test
```
