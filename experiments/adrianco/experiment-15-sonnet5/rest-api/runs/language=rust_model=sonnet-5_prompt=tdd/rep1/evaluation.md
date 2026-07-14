# Evaluation: language=rust · model=sonnet-5 · prompt=tdd · rep 1

## Summary

- **Factors:** language=rust, model=sonnet-5, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from `test_coverage=1.0` in `scores.json`
- **Build:** pass — from `test_coverage=1.0` / `defect_rate=1.0` (scores not re-run per skill)
- **Lint:** pass — `code_quality=0.83` in `scores.json`; agent log reports clippy clean
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.rs:19 create_book`, `db.rs:20 insert_book`, `books_test.rs:30` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.rs:39 list_books`, `db.rs:45`, `books_test.rs:88` |
| R3 | GET /books ?author= filter | ✓ implemented | `db.rs:47-54 WHERE author LIKE`, `books_test.rs:118` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `handlers.rs:54 get_book`, `books_test.rs:150,177` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.rs:75 update_book`, `db.rs:74`, `books_test.rs:194` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.rs:101 delete_book`, `db.rs:97`, `books_test.rs:304` |
| R7 | Data stored in SQLite | ✓ implemented | `db.rs:7 CREATE TABLE books` (rusqlite bundled), `main.rs:7 open("books.db")` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204 across `handlers.rs`; JSON bodies via `axum::Json` |
| R9 | Validation: title & author required | ✓ implemented | `models.rs:24 validate()`, `books_test.rs:63,272,359` |
| R10 | GET /health | ✓ implemented | `handlers.rs:15 health`, `lib.rs:14`, `health_test.rs:7` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, test, API reference, layout) |
| R12 | ≥ 3 tests | ✓ implemented | 13 tests (12 in `books_test.rs`, 1 in `health_test.rs`); `test_coverage=1.0` |

**Prompt factor (tdd):** The agent log (`_agent_stdout.log`) reports a strict red/green/refactor cycle per endpoint. The final artifact is consistent with test-first development (comprehensive per-endpoint tests, minimal implementation), but the process itself is not reconstructible from the archive — recorded as an info finding, not a defect.

## Build & Test

Per the evaluate-run skill, mechanical scores are read from `scores.json`, not re-run:

```text
scores.json: test_coverage=1.0, defect_rate=1.0, code_quality=0.833,
             maintainability=0.927, idiomatic=0.57, token_efficiency=0.039
```

```text
cargo test  (not re-run; test_coverage=1.0 ⇒ build + all tests passed)
Agent log: "Everything builds cleanly, clippy is clean, release build succeeds,
            and all 13 tests pass."
grep #[ignore] . --include=*.rs  →  0   (no disabled tests)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 309 (`src/*.rs`) |
| Lines of code (tests) | 408 (`tests/*.rs`) |
| Files (excl. target/) | 18 |
| Dependencies | 7 (5 runtime: axum, tokio, serde, serde_json, rusqlite; 2 dev: tower, http-body-util) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | not re-run (read from scores) |

## Findings

Top findings (full list in `findings.jsonl`) — all low/info, none gate the run:

1. [low] Raw SQLite error strings returned to clients in 500 responses (`handlers.rs`)
2. [low] `journal_mode=MEMORY` weakens durability of the persistent `books.db` (`db.rs:5` + `main.rs:7`)
3. [info] All requests serialize through a single `Arc<Mutex<Connection>>` (no pool)
4. [info] TDD process reported in agent log but not verifiable from the final artifact

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=rust_model=sonnet-5_prompt=tdd/rep1
cat scores.json                                     # mechanical scores (do not re-run)
grep -rnE "#\[ignore\]" . --include="*.rs" | wc -l  # skipped-test count → 0
grep -rcE "#\[tokio::test\]" tests/*.rs             # test count → 12 + 1 = 13
# Optional full re-run (slow; skill says rely on scores.json instead):
# cargo test
```
