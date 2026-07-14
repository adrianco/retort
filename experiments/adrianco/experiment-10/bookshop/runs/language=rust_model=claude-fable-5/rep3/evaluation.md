# Evaluation: language=rust_model=claude-fable-5 · rep 3

## Summary

- **Factors:** language=rust, model=claude-fable-5, framework=unknown, agent=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0, defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book | ✓ implemented | `src/lib.rs:99` `create_book` accepts BookInput, inserts via rusqlite, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:120` `list_books` returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/lib.rs:134` filters with `WHERE author = ?1` |
| R4 | GET /books/{id} returns single book | ✓ implemented | `src/lib.rs:182` `get_book` returns book or 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:190` `update_book` with full replacement + 404 handling |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:215` `delete_book` returns 204 or 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/lib.rs:75` `new_db` opens rusqlite Connection; `Cargo.toml` depends on `rusqlite` with `bundled` feature |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create, 200 get/list/update, 204 delete, 400 validation, 404 not found |
| R9 | Input validation: title and author required | ✓ implemented | `src/lib.rs:51` `validate` rejects empty/blank title or author with 400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/lib.rs:95` returns `{"status": "ok"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents cargo run, cargo test, env vars, and API endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 integration tests in `tests/api.rs` — exceeds requirement |

## Build & Test

```text
Build and test scores from scores.json (retort scorers already executed):
  test_coverage:    1.0  (build + all tests passed)
  defect_rate:      1.0  (build + tests succeeded)
  code_quality:     0.8333
  maintainability:  0.7708
  idiomatic:        0.58
  token_efficiency: 0.2749
```

```text
Tests (from tests/api.rs):
  health_check_returns_ok           — verifies GET /health returns 200 + {"status":"ok"}
  create_and_get_book               — POST then GET by id, checks all fields
  create_rejects_missing_required   — 400 on missing title, 400 on blank author
  list_books_supports_author_filter — creates 3 books, verifies list and ?author= filter
  update_book_replaces_fields       — PUT updates fields, verifies via GET, 404 on missing
  delete_book_then_404              — DELETE returns 204, subsequent GET/DELETE return 404
  get_missing_book_returns_404      — GET non-existent id returns 404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 432 (16 main.rs + 224 lib.rs + 192 api.rs) |
| Files | 11 |
| Dependencies | 5 (+ 2 dev) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (scores from retort scorer) |

## Findings

Top 2 by severity (full list in `findings.jsonl`):

1. [low] Arc<Mutex<Connection>> blocks concurrent requests — `src/lib.rs:14`
2. [info] idiomatic score 0.58 — below average for Rust

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=rust_model=claude-fable-5/rep3
cat scores.json                          # stored build/test/lint scores
cat TASK.md                              # requirements
cat src/lib.rs                           # main application code
cat tests/api.rs                         # integration tests
grep -rE '#\[ignore\]' --include='*.rs'  # check for skipped tests
```
