# Evaluation: language=rust_model=sonnet_tooling=none · rep 1

## Summary

- **Factors:** language=rust, model=sonnet, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=0.8333 from retort.db
- **Architecture:** summary skill not invoked (single-file project)
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-----|
| R1 | POST /books creates a new book | ✓ implemented | `src/main.rs:68-108` — `create_book` handler accepts title, author, year, isbn; inserts into SQLite; returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/main.rs:110-136` — `list_books` handler queries all rows |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/main.rs:116-123` — `WHERE author LIKE ?1` with `ListQuery.author` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/main.rs:138-158` — `get_book` handler with 404 on missing |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/main.rs:161-223` — `update_book` with partial update, 404 on missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/main.rs:225-241` — `delete_book` with 404 on missing |
| R7 | Data stored in SQLite | ✓ implemented | `Cargo.toml:6` — `rusqlite` with `bundled`; `src/main.rs:269` — `Connection::open("books.db")` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All handlers return `Json<serde_json::Value>` with 201/200/404/422 |
| R9 | Input validation: title and author required | ✓ implemented | `src/main.rs:72-89` — validates title/author presence and non-emptiness; returns 422 |
| R10 | GET /health endpoint | ✓ implemented | `src/main.rs:64-66` — returns `{"status": "ok"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — build, run, test instructions + full API documentation |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 tests in `src/main.rs:284-544` — exceeds minimum |

## Build & Test

```text
Build + test: test_coverage=1.0 from retort.db (not re-run)
Lint: code_quality=0.8333 from retort.db
defect_rate=1.0 (build+test succeeded)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 544 (main.rs) |
| Files | 3 (main.rs, Cargo.toml, README.md) |
| Dependencies | 8 (6 runtime + 2 dev) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (scores from DB) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Validation returns 422 instead of 400 — `src/main.rs:76,86`; both are acceptable for validation errors

## Reproduce

```bash
cd experiment-1/runs/language=rust_model=sonnet_tooling=none/rep1
cat stack.json
cat scores.json  # or query retort.db
grep -rE "#[ignore]" --include="*.rs" . | wc -l
wc -l src/main.rs Cargo.toml
```
