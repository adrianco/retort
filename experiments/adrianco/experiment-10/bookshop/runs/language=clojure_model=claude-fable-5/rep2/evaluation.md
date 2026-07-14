# Evaluation: language=clojure_model=claude-fable-5 · rep 2

## Summary

- **Factors:** language=clojure, model=claude-fable-5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — test_coverage=1.0 from scores.json
- **Lint:** pass — code_quality=0.8333 from scores.json (minor style issues)
- **Architecture:** see `summary/index.md`
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `src/bookapi/handler.clj:63-66` POST route calls `db/create-book!` with title, author, year, isbn |
| R2 | GET /books lists all books | ✓ implemented | `src/bookapi/handler.clj:68-69` GET route calls `db/list-books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/bookapi/handler.clj:68` destructures `[author]`; `src/bookapi/db.clj:29-32` filters by author |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/bookapi/handler.clj:71-73` returns book or 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/bookapi/handler.clj:76-83` validates and updates via `db/update-book!` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/bookapi/handler.clj:85-88` returns 204 on success, 404 if missing |
| R7 | Data stored in SQLite | ✓ implemented | `src/bookapi/db.clj:9` dbtype "sqlite"; `deps.edn` includes `org.xerial/sqlite-jdbc` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `src/bookapi/handler.clj:9-12` json-response helper; uses 200, 201, 204, 400, 404 |
| R9 | Input validation: title and author required | ✓ implemented | `src/bookapi/handler.clj:21-41` validation-error checks title/author are non-empty strings |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/bookapi/handler.clj:60-61` returns `{"status": "ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents setup (JDK 11+, Clojure CLI), run (`clojure -M:run`), test, and API |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test/bookapi/handler_test.clj` has 8 deftest blocks covering health, CRUD, validation, filter, 404s |

## Build & Test

```text
Build/test scores read from scores.json (retort scorers already ran them):
  test_coverage:    1.0  (build + all tests passed)
  defect_rate:      1.0  (no defects)
  code_quality:     0.8333
  maintainability:  0.9484
  idiomatic:        0.85
  token_efficiency: 0.0118
```

```text
Tests (8 deftest blocks, 0 skipped):
  health-check
  create-and-get-book
  validation-errors
  list-books-with-author-filter
  update-book
  delete-book
  get-missing-book
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 149 |
| Lines of code (tests) | 119 |
| Lines of code (total) | 268 |
| Files | 12 |
| Dependencies | 9 (7 main + 2 test) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (scores from scores.json) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] code_quality score 0.833 indicates minor lint issues

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=clojure_model=claude-fable-5/rep2
cat scores.json
cat TASK.md
cat stack.json
find . -name "*.clj" | xargs wc -l
grep -c "deftest" test/bookapi/handler_test.clj
```
