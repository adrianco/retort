# Evaluation: language=elixir_model=claude-opus-4-7 · rep 3

## Summary

- **Factors:** language=elixir, model=claude-opus-4-7
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass — test_coverage=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** summary skill unavailable
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a book | ✓ implemented | `lib/book_api/router.ex:27` — post route; `lib/book_api/book.ex:6-13` — schema with title/author/year/isbn; `test/book_api/router_test.exs:14` — test |
| R2 | GET /books lists all books | ✓ implemented | `lib/book_api/router.ex:14` — get route; `lib/book_api/books.ex:7-8` — `list_books/1`; `test/book_api/router_test.exs:47` — test |
| R3 | GET /books ?author= filter | ✓ implemented | `lib/book_api/router.ex:15` — extracts author param; `lib/book_api/books.ex:11-13` — where clause; `test/book_api/router_test.exs:60` — test |
| R4 | GET /books/{id} single book | ✓ implemented | `lib/book_api/router.ex:20` — get by id; 404 on nil; `test/book_api/router_test.exs:74` — test |
| R5 | PUT /books/{id} update | ✓ implemented | `lib/book_api/router.ex:37` — put route with 404 + validation; `test/book_api/router_test.exs:96` — test |
| R6 | DELETE /books/{id} | ✓ implemented | `lib/book_api/router.ex:50` — delete route, 204 response; `test/book_api/router_test.exs:117` — test |
| R7 | SQLite storage | ✓ implemented | `lib/book_api/repo.ex:3` — `Ecto.Adapters.SQLite3`; `mix.exs:32` — `ecto_sqlite3` dep |
| R8 | JSON + correct HTTP status codes | ✓ implemented | `lib/book_api/router.ex:65-68` — `send_json/3` sets content-type; uses 200/201/204/404/422 |
| R9 | Input validation (title, author required) | ✓ implemented | `lib/book_api/book.ex:15-21` — `validate_required([:title, :author])`; `test/book_api/router_test.exs:31` — rejection test |
| R10 | GET /health endpoint | ✓ implemented | `lib/book_api/router.ex:10-12` — returns `{"status":"ok"}`; `test/book_api/router_test.exs:5` — test |
| R11 | README.md with instructions | ✓ implemented | `README.md` — setup, run, test, and endpoint docs |
| R12 | At least 3 tests | ✓ implemented | 14 tests in `test/book_api/router_test.exs`; test_coverage=1.0 |

## Build & Test

```text
Build/test scores from scores.json (retort scorers already ran the toolchain):
  test_coverage: 1.0  (build + all tests passed)
  code_quality:  1.0
  idiomatic:     0.88
  defect_rate:   0.0
```

```text
14 tests in test/book_api/router_test.exs
  - GET /health: 1 test
  - POST /books: 3 tests (valid, missing fields, blank title)
  - GET /books: 2 tests (list all, filter by author)
  - GET /books/:id: 3 tests (found, 404, invalid id)
  - PUT /books/:id: 3 tests (update, 404, invalid)
  - DELETE /books/:id: 2 tests (delete, 404)
All passing (test_coverage=1.0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 451 (Elixir/Exs) |
| Files | 23 |
| Dependencies | 5 (plug, bandit, jason, ecto_sql, ecto_sqlite3) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | stored (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Validation returns 422 instead of 400 — `router.ex:32` sends 422 for changeset errors; spec mentions 400. 422 is arguably more correct for semantic validation.
2. [info] Author index added on books table — beyond spec, optimises the ?author= filter
3. [info] Ecto SQL sandbox for test isolation — best practice, transactional test cleanup
4. [info] Configurable port via PORT env var — beyond spec, deployment flexibility

## Reproduce

```bash
cd experiment-8/runs/language=elixir_model=claude-opus-4-7/rep3
cat scores.json                          # stored build/test/quality scores
cat stack.json                           # factor levels
cat TASK.md                              # task spec
find . -name "*.ex" -o -name "*.exs" | grep -v deps | grep -v _build  # source files
grep -c "test " test/book_api/router_test.exs  # test count
```
