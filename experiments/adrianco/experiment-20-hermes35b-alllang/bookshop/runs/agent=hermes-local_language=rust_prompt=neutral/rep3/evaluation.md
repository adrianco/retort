# Evaluation: agent=hermes-local language=rust prompt=neutral · rep 3

## Summary

- **Factors:** language=rust, agent=hermes-local, framework=unknown (actix-web), prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — from test_coverage=1.0
- **Build:** pass — via retort scorer (test_coverage=1.0 ⇒ build + all tests passed)
- **Lint:** pass — code_quality=0.8333 from scores.json; agent reports "clean, no warnings"
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.rs:185 create_book` → `Db::insert` (main.rs:70), route main.rs:463 |
| R2 | GET /books lists all books | ✓ implemented | `main.rs:221 list_books` → `Db::list` (main.rs:102) |
| R3 | GET /books ?author= filter | ✓ implemented | `main.rs:225` reads `author` query param → `Db::list(Some(a))` WHERE author=?1 |
| R4 | GET /books/{id} single book | ✓ implemented | `main.rs:234 get_book` returns book or `404` (main.rs:238) |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.rs:247 update_book` → `Db::update` (main.rs:131), 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.rs:290 delete_book` → `Db::delete`, `204` on success |
| R7 | Data stored in SQLite | ✓ implemented | rusqlite `Connection`, `books` table (main.rs:54-68); Cargo.toml rusqlite bundled |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204 across handlers; all `.json(...)` bodies |
| R9 | Validation: title & author required | ✓ implemented | `main.rs:189-201` reject blank/missing title or author with `400` |
| R10 | GET /health endpoint | ✓ implemented | `main.rs:181 health` → `{"status":"ok"}`, route main.rs:461 |
| R11 | README with setup/run instructions | ✓ implemented | README.md — build, run, test, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 10 `#[test]` functions (main.rs:324-447), test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (retort scorer already ran the toolchain — not re-run per evaluate-run skill):

```text
test_coverage = 1.0    ⇒ cargo build + cargo test: all 10 tests pass
code_quality  = 0.8333
defect_rate   = 0.8526
maintainability = 0.6601
idiomatic     = 0.63
```

Tests (all against the `Db` layer): create/find, update, delete, delete-nonexistent, update-nonexistent, list-empty, list-filter, clone-shares-connection, serialization, error-serialization. No `#[ignore]` markers.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src/main.rs) | 471 |
| Files (source) | 1 (src/main.rs) + README.md + Cargo.toml |
| Dependencies | 5 (actix-web, rusqlite, serde, serde_json, actix-rt) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top findings (full list in `findings.jsonl`) — none reach high severity:

1. [low] update_book/delete_book use `.unwrap()` on a DB lookup — panics instead of returning 500 (`main.rs:254`, `main.rs:293`).
2. [low] Single global `Arc<Mutex<Connection>>` serializes all DB access (`main.rs:42`).
3. [low] Tests cover the `Db` layer only; HTTP handlers, routing, status codes, and validation are not exercised end-to-end.

## Reproduce

```bash
cd experiment-20-hermes35b-alllang/bookshop/runs/agent=hermes-local_language=rust_prompt=neutral/rep3
cat scores.json          # test_coverage=1.0 ⇒ build + tests pass (do not re-run)
cargo test               # optional: 10 tests, all pass
cargo run                # serves on http://127.0.0.1:8080
```
