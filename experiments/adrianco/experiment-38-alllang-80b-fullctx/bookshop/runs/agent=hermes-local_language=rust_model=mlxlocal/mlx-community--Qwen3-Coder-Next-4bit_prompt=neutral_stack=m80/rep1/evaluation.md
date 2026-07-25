# Evaluation: rust · hermes-local · Qwen3-Coder-Next-4bit (m80) · rep 1

## Summary

- **Factors:** language=rust, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (implied by `test_coverage=1.0`; not re-run)
- **Lint:** pass — `code_quality=0.833` from scores.json
- **Architecture:** run-summary skill unavailable in this session — see module notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✓ implemented | `src/routes.rs:47` create_book, INSERT ... RETURNING → 201 |
| R2 | GET /books list | ✓ implemented | `src/routes.rs:12` get_books SELECT * FROM books |
| R3 | GET /books ?author= filter | ✓ implemented | `src/routes.rs:18-27` filters on author; test `test_get_books_by_author_filter` |
| R4 | GET /books/{id} single | ✓ implemented | `src/routes.rs:32` get_book, 404 via `AppError::NotFound` (routes.rs:42) |
| R5 | PUT /books/{id} update | ✓ implemented | `src/routes.rs:71` update_book, existence check + UPDATE |
| R6 | DELETE /books/{id} | ✓ implemented | `src/routes.rs:253` delete_book, 204/404 on rows_affected |
| R7 | SQLite storage | ✓ implemented | `src/db.rs:10` sqlx SqlitePool, `sqlite://books.db` |
| R8 | JSON + status codes | ✓ implemented | 201/200/204/404/400 via `ResponseError` (server.rs:21) |
| R9 | Validate title/author required | ✓ implemented | `src/models.rs:29-43` validate_book_request |
| R10 | GET /health | ✓ implemented | `src/routes.rs:271` health → 200 JSON; test `test_health_endpoint` |
| R11 | README with setup/run | ✓ implemented | `README.md` (124 lines) |
| R12 | ≥3 tests | ✓ implemented | `tests/integration_tests.rs` — 7 tests, `test_coverage=1.0` |

## Build & Test

Not re-run — stored mechanical scores used per skill guidance.

```text
scores.json: test_coverage=1.0 (build + all tests pass), code_quality=0.833,
defect_rate=0.049, maintainability=0.698, idiomatic=0.35, token_efficiency=0.057
```

```text
tests/integration_tests.rs: 7 #[actix_web::test] cases, in-memory SQLite per test
0 #[ignore] / disabled tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src + tests) | 697 |
| Files (excl. target/) | 18 |
| Dependencies (Cargo.toml) | 9 |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Dead-code health handler in `server.rs:44` — routes.rs wires its own health()
2. [low] `update_book` uses a 15-branch if/else field-permutation ladder (`routes.rs:96-248`)
3. [info] Validation stricter than spec — isbn + non-negative year required on create (`models.rs:36-41`)

No missing or partial requirements; no build/test failures; no skipped tests.

## Reproduce

```bash
cd experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=rust_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1
cat scores.json
grep -rEn "#\[ignore\]" . --include="*.rs" | wc -l
grep -rEc "async fn test_" tests/*.rs
# Optional full rebuild: cargo test
```
