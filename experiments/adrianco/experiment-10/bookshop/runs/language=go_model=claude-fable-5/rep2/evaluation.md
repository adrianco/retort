# Evaluation: language=go_model=claude-fable-5 · rep 2

## Summary

- **Factors:** language=go, model=claude-fable-5, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 top-level functions + 3 subtests = 10 effective test cases / 0 failed / 0 skipped (10 effective)
- **Build:** pass — test_coverage=0.734, defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json, 0 warnings
- **Architecture:** summary skill unavailable
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `handlers.go:85` handleCreate, `store.go:51` Create — accepts all 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:98` handleList, `store.go:63` List — returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `handlers.go:99` `r.URL.Query().Get("author")`, `store.go:68` `WHERE author = ?` |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `handlers.go:107` handleGet, `store.go:89` Get — returns 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:124` handleUpdate, `store.go:103` Update — returns 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:146` handleDelete, `store.go:121` Delete — returns 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:35` CREATE TABLE books |
| R8 | Returns JSON with appropriate HTTP status codes | ✓ implemented | `handlers.go:30` writeJSON sets Content-Type: application/json; uses 200/201/204/400/404/500/503 |
| R9 | Input validation: title and author required | ✓ implemented | `handlers.go:52-58` decodeBook validates non-blank title and author via TrimSpace |
| R10 | GET /health health-check endpoint | ✓ implemented | `handlers.go:77` handleHealth — pings DB, returns `{"status":"ok"}` or 503 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 96 lines covering setup, config, test, API docs, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `handlers_test.go` — 7 test functions + 3 subtests covering CRUD, validation, filtering, health |

## Build & Test

```text
Build and test scores from scores.json (not re-run per skill policy):
  test_coverage:    0.734
  code_quality:     1.0
  defect_rate:      1.0  (build + tests succeeded)
  maintainability:  0.892
  idiomatic:        0.89
  token_efficiency: 0.022
```

```text
Test functions in handlers_test.go:
  TestHealth                — GET /health returns 200 {"status":"ok"}
  TestCreateAndGetBook      — POST /books → 201, GET /books/1 → 200
  TestCreateValidation      — 3 subtests: missing title, missing author, blank title → 400
  TestListWithAuthorFilter  — seeds 3 books, lists all (3), filters by Alice (2)
  TestUpdateBook            — PUT /books/1 → 200, PUT /books/999 → 404
  TestDeleteBook            — DELETE /books/1 → 204, GET after → 404, double delete → 404
  TestGetInvalidID          — GET /books/abc → 400

Effective tests: 10 (7 top-level + 3 subtests), 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 326 (main.go:29, store.go:136, handlers.go:161) |
| Lines of code (incl. tests) | 512 |
| Files | 12 |
| Dependencies | 51 (go.sum entries) |
| Tests total | 10 (7 functions + 3 subtests) |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | N/A (scores from scores.json) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Code coverage at 73.4% — internal error paths (500/503 branches) untested

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=go_model=claude-fable-5/rep2
cat scores.json                          # pre-computed scores
cat REQUIREMENTS.json                    # (in parent: experiment-10/bookshop/)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skipped tests
grep -cE "^func Test" handlers_test.go   # test function count
find . -name "*.go" -exec wc -l {} +    # lines of code
```
