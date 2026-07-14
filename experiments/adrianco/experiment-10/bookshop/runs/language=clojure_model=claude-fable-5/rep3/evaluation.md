# Evaluation: language=clojure_model=claude-fable-5 · rep 3

## Summary

- **Factors:** language=clojure, model=claude-fable-5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective deftest suites, 14 testing blocks)
- **Build:** pass — test_coverage=1.0 from scores.json (build+all tests passed)
- **Lint:** code_quality=0.833 from scores.json
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book | ✓ implemented | `src/bookapi/handler.clj:40` POST route, `db.clj:40` create-book! |
| R2 | GET /books lists all books | ✓ implemented | `src/bookapi/handler.clj:47` GET route, `db.clj:29` list-books |
| R3 | GET /books ?author= filter | ✓ implemented | `src/bookapi/handler.clj:48` passes author param, `db.clj:33` WHERE clause |
| R4 | GET /books/{id} single book | ✓ implemented | `src/bookapi/handler.clj:50` GET :id route, 404 handling |
| R5 | PUT /books/{id} update | ✓ implemented | `src/bookapi/handler.clj:55` PUT route with validation, `db.clj:48` update-book! |
| R6 | DELETE /books/{id} delete | ✓ implemented | `src/bookapi/handler.clj:67` DELETE route, 204/404 responses |
| R7 | SQLite/embedded DB storage | ✓ implemented | `src/bookapi/db.clj:10-11` SQLite datasource, `deps.edn:8` sqlite-jdbc dep |
| R8 | JSON responses + HTTP status codes | ✓ implemented | `src/bookapi/handler.clj:77-80` wrap-json-body/response; 201/200/204/400/404 used |
| R9 | Input validation (title, author required) | ✓ implemented | `src/bookapi/handler.clj:10-24` validate-book, 400 on missing fields |
| R10 | GET /health endpoint | ✓ implemented | `src/bookapi/handler.clj:38` returns `{"status":"ok"}` |
| R11 | README.md with instructions | ✓ implemented | `README.md` — setup, run, test commands, API docs, examples |
| R12 | At least 3 tests | ✓ implemented | 6 deftest suites in `test/bookapi/handler_test.clj` |

## Build & Test

```text
Stored scores (scores.json) — build and test were NOT re-run:
  test_coverage:    1.0    (build + all tests passed)
  defect_rate:      1.0    (build+test succeeded)
  code_quality:     0.8333
  maintainability:  0.9543
  idiomatic:        0.8700
  token_efficiency: 0.0122
```

```text
Test suites (from source inspection):
  deftest health-check      — 1 testing block, verifies 200 + body
  deftest create-book       — 3 testing blocks (valid 201, missing fields 400, bad year 400)
  deftest list-books        — 2 testing blocks (list all, filter by author)
  deftest get-book-by-id    — 3 testing blocks (found 200, unknown 404, non-numeric 404)
  deftest update-book       — 3 testing blocks (update 200, validation 400, unknown 404)
  deftest delete-book       — 2 testing blocks (delete 204+verify gone, unknown 404)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 154 |
| Lines of code (with tests) | 268 |
| Files (total) | 11 |
| Source files (.clj) | 4 |
| Dependencies (runtime) | 8 |
| Tests total (deftest) | 6 |
| Tests effective | 6 |
| Testing blocks | 14 |
| Skip ratio | 0% |
| Build duration | n/a (scores from scores.json) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [info] Year validation allows negative integers — `handler.clj:23`
2. [info] ISBN format not validated — `handler.clj:29`

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=clojure_model=claude-fable-5/rep3
cat scores.json                                                     # stored build/test/lint scores
cat REQUIREMENTS.json                                                # from experiment-10/bookshop/
grep -rE ':pending|:skip|:kaocha/skip' test/ --include="*.clj"      # check for skipped tests
find . -name "*.clj" -o -name "*.edn" | xargs wc -l                # line counts
```
