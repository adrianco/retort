# Evaluation: language=go_model=claude-fable-5 · rep 3

## Summary

- **Factors:** language=go, model=claude-fable-5, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=0.74, defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json, 0 warnings
- **Architecture:** summary skill unavailable
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book | ✓ implemented | `handlers.go:68` handleCreateBook, `store.go:60` CreateBook; tested in TestCreateAndGetBook |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:82` handleListBooks, `store.go:77` ListBooks; tested in TestListBooksWithAuthorFilter |
| R3 | GET /books supports ?author= filter | ✓ implemented | `store.go:83` WHERE author=? clause; tested in TestListBooksWithAuthorFilter |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `handlers.go:91` handleGetBook, `store.go:104` GetBook with 404; tested in TestCreateAndGetBook |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:109` handleUpdateBook, `store.go:116` UpdateBook; tested in TestUpdateBook |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:132` handleDeleteBook, `store.go:136` DeleteBook; tested in TestDeleteBook |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:8` imports modernc.org/sqlite (pure Go driver), `store.go:39` CREATE TABLE schema |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `handlers.go:29` writeJSON sets Content-Type: application/json; 201/200/400/404/204 used correctly |
| R9 | Input validation: title and author required | ✓ implemented | `handlers.go:48-55` decodeBook validates; tested in TestCreateValidation (missing title, missing author, whitespace) |
| R10 | GET /health health-check endpoint | ✓ implemented | `handlers.go:64` handleHealth returns {"status":"ok"}; tested in TestHealth |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents Go requirements, setup, run, test, API reference with examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 test functions in `api_test.go`: TestHealth, TestCreateAndGetBook, TestCreateValidation, TestListBooksWithAuthorFilter, TestUpdateBook, TestDeleteBook, TestInvalidID |

## Build & Test

```text
Scores from scores.json (retort scorers already ran build/tests):
  test_coverage:    0.74
  code_quality:     1.0
  defect_rate:      1.0  (build + all tests passed)
  maintainability:  0.8922
  idiomatic:        0.94
  token_efficiency: 0.0224
```

```text
7 test functions, 0 skipped, 0 failed.
Tests run against in-memory SQLite (:memory:) via httptest — full HTTP stack integration tests.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go source only) | 521 |
| Files | 12 |
| Dependencies (go.sum entries) | 43 |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Source files | 4 (.go) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Test line coverage is 74%, not 100% — all tests pass but not all source lines are exercised

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=go_model=claude-fable-5/rep3
cat scores.json
cat stack.json
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -cE "^func Test" api_test.go
find . -name "*.go" | xargs wc -l
```
