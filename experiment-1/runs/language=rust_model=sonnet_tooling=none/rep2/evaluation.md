# Evaluation: language=rust_model=sonnet_tooling=none · rep 2

## Summary

- **Factors:** language=rust, model=sonnet, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=0.8333 from retort.db (4 quality observations noted)
- **Architecture:** summary skill unavailable
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 3 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/main.rs:45` `create_book` handler accepts all four fields, persists via INSERT |
| R2 | GET /books lists all books | ✓ implemented | `src/main.rs:84` `list_books` returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/main.rs:90` checks `query.author`, uses SQL LIKE for substring match |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `src/main.rs:127` `get_book` queries by id, returns 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/main.rs:153` `update_book` merges partial updates, preserves unchanged fields |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/main.rs:220` `delete_book` removes row, returns 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/main.rs:250` `Connection::open("books.db")`, rusqlite with bundled feature |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 Created, 200 OK, 204 No Content, 400 Bad Request, 404 Not Found throughout |
| R9 | Input validation: title and author required | ✓ implemented | `src/main.rs:49-62` validates presence and non-empty for both fields, returns 400 |
| R10 | GET /health endpoint | ✓ implemented | `src/main.rs:41` returns `{"status": "ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents build, run, test commands, and all API endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 tests in `src/main.rs:287-482` covering CRUD, validation, filtering, 404 |

## Build & Test

```text
(Stored scores from retort.db — build/test not re-run)
test_coverage = 1.0  (build succeeded, all tests passed)
code_quality  = 0.8333
defect_rate   = 1.0
```

Tests present (all in `src/main.rs` mod tests):
1. `test_health_check` — verifies /health returns 200 + {"status":"ok"}
2. `test_create_and_get_book` — POST then GET by ID, verifies fields
3. `test_create_book_validation` — missing title → 400, empty author → 400
4. `test_list_and_filter_books` — seeds 2 books, lists all, filters by author
5. `test_update_book` — partial update preserves unchanged fields
6. `test_delete_book` — DELETE returns 204, subsequent GET returns 404
7. `test_not_found` — GET nonexistent ID returns 404

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 482 |
| Files | 5 |
| Dependencies | 6 (actix-web, rusqlite, serde, serde_json, uuid, tokio) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [medium] Pervasive .unwrap() on database operations risks panics — `src/main.rs:71,93,109,204`
2. [low] Silent error suppression via filter_map(|r| r.ok()) — `src/main.rs:104,120`
3. [low] All code in a single 482-line file — `src/main.rs`
4. [low] Sync Mutex for DB access in async context — `src/main.rs:4,38`

## Reproduce

```bash
cd experiment-1/runs/language=rust_model=sonnet_tooling=none/rep2
cat stack.json
cat TASK.md
# Scores retrieved from retort.db (test_coverage=1.0, code_quality=0.833)
grep -rE "#\[ignore\]" --include="*.rs" .
grep -c "#\[actix_web::test\]" src/main.rs
wc -l src/main.rs
```
