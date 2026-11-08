# Evaluation: rest-api-crud · agent=codex effort=low language=rust model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral, framework=axum
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — from `test_coverage=1.0` / `defect_rate=1.0` (scores.json; not re-run)
- **Lint:** pass — `code_quality=0.833` (scores.json)
- **Architecture:** single-crate axum service; `src/lib.rs` (router + handlers + SQLite state), `src/main.rs` (binary entrypoint), `tests/api.rs` (integration tests). (run-summary skill not invoked — kept within time budget.)
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/lib.rs:110 create` INSERTs all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:125 list` selects all, ordered by id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/lib.rs:130` `WHERE (?1 IS NULL OR author = ?1)`; `Filters.author` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/lib.rs:136 get_book` + `find_book` → 404 via `not_found()` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:143 update` UPDATE, 404 when count==0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:159 delete`, 404 when count==0 |
| R7 | Data stored in SQLite | ✓ implemented | `rusqlite` Connection; `AppState::new` CREATE TABLE books |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 create, 200 get/list, 404 missing, 400 invalid; `ApiError`/`ErrorBody` |
| R9 | Validation: title and author required | ✓ implemented | `src/lib.rs:66 validate` rejects blank title/author → 400 |
| R10 | GET /health health check | ✓ implemented | `src/lib.rs:107 health` returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build, run, env vars, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/api.rs` — 4 `#[tokio::test]` fns; `test_coverage=1.0` |

## Build & Test

Build/test not re-run — stored mechanical scores used per skill guidance.

```text
scores.json: test_coverage=1.0, defect_rate=1.0  => build + all tests passed
code_quality=0.833, maintainability=0.826, idiomatic=0.3, token_efficiency=0.040
```

```text
4 integration tests in tests/api.rs, 0 #[ignore], 0 skipped:
  create_get_update_delete, list_and_filter, validates_create_and_update, health_check
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 305 (lib 168, main 13, tests 124) |
| Files | 14 (incl. Cargo.lock, README) |
| Dependencies | 5 runtime + 1 dev (axum, tokio, serde, serde_json, rusqlite; tower) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 pinned requirements implemented with test coverage; build and tests pass; no skipped/disabled tests; lint clean.

## Reproduce

```bash
cd "experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=rust_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json            # stored mechanical scores (build/test/lint)
grep -rnE "#\[tokio::test\]|#\[test\]" --include="*.rs" .   # 4 tests
grep -rnE "#\[ignore\]" --include="*.rs" .                   # 0 skips
# optional: cargo test     # rebuilds + runs (slow; scores.json already reflects this)
```
