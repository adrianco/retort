# Evaluation: language=clojure_model=claude-fable-5 · rep 1

## Summary

- **Factors:** language=clojure, model=claude-fable-5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective, 30 assertions)
- **Build:** pass — test_coverage=1.0, defect_rate=1.0 from scores.json
- **Lint:** code_quality=0.8333 from scores.json
- **Architecture:** summary skill unavailable
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book | ✓ implemented | `src/bookapi/handler.clj:48-52` create-book, `src/bookapi/db.clj:41-47` create-book! |
| R2 | GET /books lists all books | ✓ implemented | `src/bookapi/handler.clj:54-55` list-books, `src/bookapi/db.clj:30-39` list-books |
| R3 | GET /books ?author= filter | ✓ implemented | `src/bookapi/handler.clj:55` passes author param, `src/bookapi/db.clj:33-35` WHERE author = ? |
| R4 | GET /books/{id} returns single book | ✓ implemented | `src/bookapi/handler.clj:57-59` get-book, `src/bookapi/db.clj:25-28` get-book |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/bookapi/handler.clj:62-72` update-book, `src/bookapi/db.clj:49-57` update-book! |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/bookapi/handler.clj:74-77` delete-book, `src/bookapi/db.clj:59-64` delete-book! |
| R7 | SQLite embedded DB | ✓ implemented | `src/bookapi/db.clj:12` `{:dbtype "sqlite"}`, `src/bookapi/db.clj:17-23` CREATE TABLE |
| R8 | JSON responses with HTTP status codes | ✓ implemented | `src/bookapi/handler.clj:90-92` wrap-json-body/wrap-json-response; 201/200/400/404/204 used |
| R9 | Input validation: title and author required | ✓ implemented | `src/bookapi/handler.clj:20-43` validate-book checks non-blank title and author |
| R10 | GET /health endpoint | ✓ implemented | `src/bookapi/handler.clj:83` returns `{:status "ok"}` with 200 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — covers requirements, run, test, API docs, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test/bookapi/handler_test.clj` — 8 deftest functions, 30 assertions |

## Build & Test

```text
Build/test scores read from scores.json (not re-run):
  test_coverage:   1.0    (build + all tests passed)
  defect_rate:     1.0    (build+test succeeded)
  code_quality:    0.8333
  maintainability: 0.9456
  idiomatic:       0.88
  token_efficiency: 0.0105
```

```text
Test runner: cognitect.test-runner via clojure -M:test
8 deftest functions, 30 assertions, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 170 |
| Lines of code (tests) | 122 |
| Lines of code (total incl. config) | 309 |
| Files | 11 |
| Dependencies | 8 |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |

## Findings

No findings. All 12 requirements implemented, all tests pass, no skipped tests.

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=clojure_model=claude-fable-5/rep1
cat scores.json
cat TASK.md
cat stack.json
grep -c "deftest" test/bookapi/handler_test.clj
grep -rE "deftest.*:skip|:pending" test/ --include="*.clj" 2>/dev/null | wc -l
find . -name "*.clj" -o -name "*.edn" | xargs wc -l
find . -type f -not -path "*/.git/*" -not -path "*/target/*" | wc -l
```
