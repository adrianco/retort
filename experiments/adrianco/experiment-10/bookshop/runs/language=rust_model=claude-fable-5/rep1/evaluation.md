# Evaluation: language=rust_model=claude-fable-5 · rep 1

## Summary

- **Factors:** language=rust, model=claude-fable-5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — test_coverage=1.0 from scores.json (build+tests passed)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-----|
| R1 | POST /books creates a new book | ✓ implemented | `src/lib.rs:103-115` — `create_book` accepts BookInput, inserts via SQLite, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:117-138` — `list_books` queries all rows |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/lib.rs:122-134` — filters by `author` query param; tested at `tests/api.rs:108-113` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/lib.rs:140-146` — `get_book` via `get_book_by_id`; returns 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:148-163` — `update_book` modifies existing book; 404 if not found |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:165-175` — `delete_book` removes row; returns 204 or 404 |
| R7 | Data stored in SQLite | ✓ implemented | `Cargo.toml` depends on `rusqlite` (bundled); `src/lib.rs:191-199` opens file-based DB |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create (`lib.rs:114`), 200 get/list/update, 204 delete (`lib.rs:174`), 400 validation (`lib.rs:46`), 404 not found (`lib.rs:48`) |
| R9 | Input validation: title and author required | ✓ implemented | `src/lib.rs:61-75` — `validate()` checks both fields present and non-empty; tested at `tests/api.rs:66-84` |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/lib.rs:99-101` — returns `{"status": "ok"}`; route at `lib.rs:203`; tested at `tests/api.rs:37-42` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — documents Rust/Cargo requirement, `cargo run`, `cargo test`, API reference with examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 tests in `tests/api.rs`: health_check, create_and_get_book, validation_rejects_missing_fields, list_books_with_author_filter, update_book, delete_book |

## Build & Test

```text
Build and test scores from scores.json (retort scorers already ran the toolchain):
  test_coverage:    1.0  (build + all tests passed)
  defect_rate:      1.0  (build+test succeeded)
  code_quality:     0.8333
  maintainability:  0.7902
  idiomatic:        0.75
  token_efficiency: 0.2458
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 394 (lib.rs: 210, main.rs: 14, tests/api.rs: 170) |
| Files | 11 |
| Dependencies | 4 (axum, tokio, serde, rusqlite) + 2 dev (tower, http-body-util) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | N/A (scores from scorer cache) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Token efficiency is low (0.246) — agent used more tokens per line than average
2. [info] Idiomatic score 0.75 — minor Rust style gaps (unwrap on Mutex::lock)

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=rust_model=claude-fable-5/rep1
cat scores.json
cat stack.json
grep -rE "#\[ignore\]|#\[cfg\(ignore\)\]" . --include="*.rs"
wc -l src/lib.rs src/main.rs tests/api.rs
grep -cE "^\S+ = " Cargo.toml
```
