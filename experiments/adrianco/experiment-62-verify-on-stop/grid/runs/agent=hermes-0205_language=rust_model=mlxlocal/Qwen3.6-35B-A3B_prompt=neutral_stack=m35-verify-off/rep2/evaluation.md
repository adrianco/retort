# Evaluation: Qwen3.6-35B-A3B · neutral · m35-verify-off · rep 2

_Second-opinion re-check of a prior evaluation that scored requirement_coverage=0.9167 and failed R7._

## Summary

- **Factors:** language=rust, agent=hermes-0205, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35-verify-off
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — clean, no warnings (`test_coverage=1.0`, `defect_rate=1.0` from scores.json)
- **Lint:** pass — 0 warnings (`code_quality=0.789` from scores.json)
- **Architecture:** run-summary skill not invoked (single-crate, two-file app; structure covered inline below)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 1 low)

## Second-opinion verdict on R7

The first evaluator failed R7 ("Data stored in SQLite") citing (a) in-memory not persistent, and (b) the per-connection-DB pool footgun.

**R7 is MET.** The app stores data in a genuine SQLite engine via `sqlx` — `SqlitePool` (`src/main.rs:9`), a real `books` table (`src/main.rs:84-97`), and real SQL in every handler. R7's `how_to_verify` distinguishes "SQLite/embedded DB" from "just in-memory state" (a `Vec`/`HashMap`); this is a real DB, so it qualifies. TASK.md never requires durability across restarts, so the in-memory variant is acceptable. **The first evaluator was wrong to fail R7.**

**The footgun is REAL and preserved as a high finding.** `SqlitePool::connect("sqlite::memory:")` (sqlx 0.8.6, default `max_connections=10`) gives each physical connection its own private in-memory database. The table is created on one connection (`src/main.rs:84`); a concurrent request may draw a fresh connection with no `books` table → `no such table` / lost data. The graded tests pass only because each uses sequential queries on one reused connection. This is a robustness defect, not a missing requirement.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/main.rs:104` create_book, route `:293`; INSERT `:117` |
| R2 | GET /books lists all | ✓ implemented | `src/main.rs:144` list_books, route `:294`; SELECT `:156` |
| R3 | ?author= filter | ✓ implemented | `src/main.rs:148-160` filters via `WHERE author = ?` |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `src/main.rs:174` get_book; `not_found()` on None `:191` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/main.rs:195` update_book; partial-update merge `:218-233` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/main.rs:261` delete_book; 404 if 0 rows `:276` |
| R7 | Stored in SQLite/embedded DB | ✓ implemented | sqlx `SqlitePool` `:80`, table `:84-97` — see verdict above |
| R8 | JSON + appropriate status codes | ✓ implemented | Json everywhere; 404 `:53`, 400 `:60`, 204 `:279`. Note: POST returns 200 not 201 (low finding) |
| R9 | Validation: title+author required | ✓ implemented | `src/main.rs:108-115` returns 400 if missing |
| R10 | GET /health | ✓ implemented | `src/main.rs:283` health_check, route `:298` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/run/usage/testing sections |
| R12 | ≥3 tests that run | ✓ implemented | 11 `#[tokio::test]` in `src/tests.rs`; `test_coverage=1.0` |

## Build & Test

Not re-run — stored mechanical scores used per skill:

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.789
=> build clean (no warnings), 11/11 tests pass, 0 skipped
```

Skip scan: `grep -rE "#\[ignore\]" src` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 649 (main.rs 309, tests.rs 340) |
| Files (src) | 2 |
| Dependencies (Cargo.toml) | 8 (5 runtime rows matched + dev-deps) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build | clean, no warnings |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] In-memory SQLite pool serves a separate empty DB per connection under concurrency (`src/main.rs:80`)
2. [medium] Tests exercise raw SQL, not the HTTP handlers (`src/tests.rs`)
3. [low] POST /books returns 200 instead of 201 Created (`src/main.rs:104-142`)

## Reproduce

```bash
cd <run_dir>
cat scores.json                                              # stored mechanical scores
grep -rE "#\[tokio::test\]|#\[test\]" src --include="*.rs" | wc -l   # 11
grep -rE "#\[ignore\]" src --include="*.rs" | wc -l          # 0
```
