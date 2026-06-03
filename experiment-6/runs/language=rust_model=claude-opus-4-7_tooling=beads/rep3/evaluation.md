# Evaluation: language=rust_model=claude-opus-4-7_tooling=beads · rep 3

## Summary

- **Factors:** language=rust, model=claude-opus-4-7, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass (cargo test includes build) — 0.54s
- **Lint:** derived (no separate lint run; build succeeded with no warnings)
- **Architecture:** see `summary/index.md`
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/handlers.rs:18-57` — `create_book` accepts all four fields, inserts via sqlx, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/handlers.rs:59-77` — `list_books` queries all rows, returns 200 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/handlers.rs:63-74` — `ListQuery.author` filters; test `list_books_filters_by_author` verifies |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/handlers.rs:79-92` — `get_book` fetches by id, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/handlers.rs:94-148` — partial update with validation on empty title/author |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/handlers.rs:150-164` — returns 204 on success, 404 if not found |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.rs:1-33` — `sqlx::sqlite::SqlitePool`, `CREATE TABLE IF NOT EXISTS books` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 Created, 200 OK, 204 No Content, 400 Bad Request, 404 Not Found, 500 ISE via `src/error.rs` |
| R9 | Input validation: title and author required | ✓ implemented | `src/handlers.rs:22-35` — rejects empty/missing title/author with 400; test `create_book_missing_title_returns_400` verifies |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/handlers.rs:14-16` — returns `{"status":"ok"}` with 200; test `health_check_returns_ok` verifies |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 91 lines covering setup, run, test, endpoints, examples, project layout |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/api.rs` — 5 integration tests, all passing |

## Build & Test

```text
cargo test --manifest-path Cargo.toml
```

```text
running 5 tests
test health_check_returns_ok ... ok
test create_book_missing_title_returns_400 ... ok
test create_and_get_book ... ok
test update_and_delete_book ... ok
test list_books_filters_by_author ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 544 |
| Files | 17 |
| Dependencies | 10 runtime + 3 dev = 13 |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | 0.54s |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Scores read via cargo test fallback (retort.db locked)

## Reproduce

```bash
cd experiment-6/runs/language=rust_model=claude-opus-4-7_tooling=beads/rep3
cargo test
find . -type f -name "*.rs" -not -path "*/target/*" | xargs wc -l
grep -rE "#\[ignore\]" . --include="*.rs"
```
