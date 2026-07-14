# Evaluation: language=rust_model=opus_tooling=none · rep 2

## Summary

- **Factors:** language=rust, model=opus, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — test_coverage=1.0, defect_rate=1.0 from retort.db
- **Lint:** pass — code_quality=0.833 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `src/lib.rs:84` create_book handler, accepts BookInput (title, author, year, isbn), returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:106` list_books handler, returns Vec<Book> |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/lib.rs:111` checks params.get("author"), filters SQL query |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/lib.rs:141` get_book handler, returns 404 if not found |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:158` update_book handler, returns 404 if not found |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:183` delete_book handler, returns 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `src/lib.rs:45-57` uses rusqlite (bundled), CREATE TABLE books; main.rs:6 uses :memory: mode |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | Uses axum Json() throughout; 201 create, 200 get/list, 204 delete, 404 not found, 400 validation |
| R9 | Input validation: title and author required | ✓ implemented | `src/lib.rs:72-82` validate() rejects empty title/author with 400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/lib.rs:68-70` returns 200 {"status": "ok"} |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` covers cargo build, cargo run, cargo test, endpoint list |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/integration.rs` has 4 tests: health_ok, create_and_get_book, create_missing_title_is_400, list_filter_by_author_and_delete |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage = 1.0 (build + all tests passed)
  defect_rate   = 1.0 (build+test succeeded)
  code_quality  = 0.833
```

```text
Tests (from source analysis):
  4 test functions in tests/integration.rs
  0 skipped / ignored
  All passed (test_coverage = 1.0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 344 (192 lib.rs + 139 integration.rs + 13 main.rs) |
| Files | 7 |
| Dependencies | 7 runtime + 2 dev |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Maintainability | 0.803 |
| Idiomatic | 0.680 |
| Token efficiency | 0.500 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] SQLite uses in-memory mode, not persistent file — `src/main.rs:6`

## Reproduce

```bash
cd experiment-1/runs/language=rust_model=opus_tooling=none/rep2
cat stack.json
cat scores.json  # or query retort.db
# Build/test already scored by retort; test_coverage=1.0
grep -rE "#[ignore]" --include="*.rs" .  # skipped tests
```
