# Evaluation: effort=default_language=rust_model=claude-fable-5-1_prompt=none · rep 1

## Summary

- **Factors:** language=rust, model=claude-fable-5-1, effort=default, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective) — from `test_coverage=1.0`
- **Build:** pass (test_coverage=1.0 ⇒ build+tests succeeded; scores.json)
- **Lint:** pass — code_quality=0.83 (scores.json)
- **Architecture:** run-summary skill unavailable — see module notes below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/handlers.rs:create_book` → `src/db.rs:create`; tested `tests/api.rs:create_and_get_book` |
| R2 | GET /books lists all | ✓ implemented | `src/handlers.rs:list_books` → `src/db.rs:list`; tested `tests/api.rs:list_books_supports_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/db.rs:70` `WHERE ?1 IS NULL OR author = ?1 COLLATE NOCASE`; tested |
| R4 | GET /books/{id} single (404) | ✓ implemented | `src/handlers.rs:get_book` returns 404 on None; tested `delete_book_then_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/handlers.rs:update_book` → `src/db.rs:update`; tested `update_book_replaces_fields` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/handlers.rs:delete_book` → `src/db.rs:delete` (204); tested |
| R7 | SQLite/embedded persistence | ✓ implemented | `src/db.rs` rusqlite bundled, `books` table + migrate() |
| R8 | JSON + appropriate status codes | ✓ implemented | `src/error.rs` maps 404/422/400/409/500; 201 create, 204 delete |
| R9 | Validation: title+author required | ✓ implemented | `src/models.rs:validate`; tested `create_rejects_missing_required_fields` (see low finding: 422 vs 400) |
| R10 | GET /health | ✓ implemented | `src/handlers.rs:health` pings DB; tested `health_check_returns_ok` |
| R11 | README with setup/run | ✓ implemented | `README.md` (4.2KB, build/run/env/endpoints) |
| R12 | ≥3 tests | ✓ implemented | 16 tests (8 integration in `tests/api.rs`, 8 unit in `src/`) |

## Build & Test

Not re-run — stored scores used (per skill Step 2):

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.833  maintainability=0.796  idiomatic=0.8
=> build + all 16 tests passed; lint clean
```

Skip scan: `grep #[ignore]` → 0. Effective tests = 16.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (rs, incl. tests) | 778 |
| Files (excl. target/.git) | 19 |
| Dependencies (Cargo.toml) | 7 (axum, tokio, serde, serde_json, rusqlite; dev: tower, http-body-util) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Full list in `findings.jsonl`:

1. [low] R9 — validation rejects with 422 (UNPROCESSABLE_ENTITY), not the 400 named in the checklist's how_to_verify. Semantically defensible; requirement otherwise fully met.
2. [info] ISBN-10/13 format validation beyond spec (`src/models.rs:60`).
3. [info] Year range validation 0..=9999 beyond spec (`src/models.rs:52`).
4. [info] Author filter is case-insensitive (`src/db.rs:70`).

## Architecture (run-summary unavailable)

- `main.rs` — binds TcpListener, opens DB (`DATABASE_PATH`/`PORT` env), graceful shutdown.
- `lib.rs` — `app(Db)` router: `/health`, `/books` (GET/POST), `/books/{id}` (GET/PUT/DELETE).
- `handlers.rs` — thin axum handlers, extractor-rejection-aware.
- `db.rs` — `Db` = `Arc<Mutex<Connection>>`; migrate + CRUD + ping; unit-tested.
- `models.rs` — `Book`/`BookInput`/`ValidBook`, `validate()`; unit-tested.
- `error.rs` — `ApiError` enum → JSON + status codes; `From` impls for rusqlite/rejections.

## Reproduce

```bash
cd "effort=default_language=rust_model=claude-fable-5-1_prompt=none/rep1"
cat scores.json                 # stored build/test/lint scores (not re-run)
grep -rnE "#\[ignore\]" . --include="*.rs" | wc -l   # 0 skips
grep -rcE "#\[(tokio::)?test\]" src tests --include="*.rs"  # test counts
# optional full rebuild:  cargo test
```
