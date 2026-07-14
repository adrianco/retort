# Evaluation: language=erlang_model=claude-opus-4-8 · rep 3

## Summary

- **Factors:** language=erlang, model=claude-opus-4-8, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — test_coverage=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json, 0 warnings
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/book_handler.erl:21-35` handles POST, `book_store:create/1`; tested by `book_api_SUITE:create_book/1` |
| R2 | GET /books lists all books | ✓ implemented | `src/book_handler.erl:37-42` calls `book_store:list/0`; tested by `book_api_SUITE:list_books/1` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/book_handler.erl:38-41` uses `cowboy_req:match_qs` for author, calls `book_store:list_by_author/1`; tested by `book_api_SUITE:list_filter_by_author/1` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/book_handler.erl:46-52` with 404 on not_found; tested by `book_api_SUITE:get_book/1` and `get_missing_book_returns_404/1` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/book_handler.erl:54-72` merges fields via `book_store:update/2`; tested by `book_api_SUITE:update_book/1` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/book_handler.erl:74-80` returns 204 on success, 404 on not_found; tested by `book_api_SUITE:delete_book/1` |
| R7 | Data stored in SQLite (or embedded DB equivalent) | ✓ implemented | Uses Mnesia (Erlang's built-in embedded DB) — `src/book_store.erl` throughout |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `src/book_handler.erl:168-171` sets `application/json`, uses 201/200/204/400/404/405; `src/health_handler.erl:9` also JSON |
| R9 | Input validation: title and author required | ✓ implemented | `src/book_handler.erl:88-132` validates presence + non-empty string; tested by `book_api_SUITE:create_requires_title_and_author/1` |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/health_handler.erl` returns `{"status":"ok"}` with 200; tested by `book_api_SUITE:health_check/1` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 120 lines covering setup, run, API docs, examples, tests, project layout |
| R12 | At least 3 unit/integration tests | ✓ implemented | 10 Common Test cases in `test/book_api_SUITE.erl` — full end-to-end HTTP integration tests |

## Build & Test

```text
Build/test scores read from scores.json (not re-run):
  test_coverage: 1.0  (build + all tests passed)
  code_quality:  1.0
  defect_rate:   0.0
  idiomatic:     0.7
```

```text
Test suite: test/book_api_SUITE.erl
  10 test cases defined in all/0:
    health_check, create_book, create_requires_title_and_author,
    create_rejects_invalid_json, list_books, list_filter_by_author,
    get_book, get_missing_book_returns_404, update_book, delete_book
  0 skipped tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 384 |
| Lines of code (incl. tests) | 544 |
| Files | 16 |
| Dependencies | 3 (cowboy + 2 transitive in rebar.lock) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (scores from scores.json) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Mnesia configured with ram_copies only — data does not survive restarts (`src/book_store.erl:21`)

## Reproduce

```bash
cd experiment-8/runs/language=erlang_model=claude-opus-4-8/rep3
cat scores.json
cat stack.json
# Tests (requires Erlang/OTP 27+ and rebar3):
# rebar3 ct
```
