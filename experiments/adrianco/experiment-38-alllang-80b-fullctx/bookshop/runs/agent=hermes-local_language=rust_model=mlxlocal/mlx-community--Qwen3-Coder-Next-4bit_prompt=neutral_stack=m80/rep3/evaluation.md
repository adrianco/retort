# Evaluation: rust · hermes-local · Qwen3-Coder-Next-4bit (m80) · rep 3

> **SECOND OPINION** — re-check of a prior evaluation that scored requirement_coverage=0.8333 and flagged R4 as not met. Verdict: the first evaluator was **CORRECT** about R4 (500 instead of 404). Re-scored over the full pinned 12-requirement checklist → **11/12 (0.9167)**; the prior 0.8333 under-counted (only R4 is genuinely affected).

## Summary

- **Factors:** language=rust, agent=hermes-local, model=mlxlocal/Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial (R4), 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — test_coverage=1.0 (scores.json)
- **Build:** pass — test_coverage=1.0 ⇒ build+tests succeeded (scores.json)
- **Lint:** pass — code_quality=0.83 (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (1 high, 1 medium)

## Second-opinion verdict on prior claim

**R4 — GET /books/{id} returns 500 instead of 404 for a missing book: CONFIRMED (first evaluator was right).**

Trace:
- `get_book` handler (`src/api.rs:26-33`) calls `data.get_book_by_id(id).await?`.
- `get_book_by_id` (`src/repository.rs:66-74`) uses `.fetch_one(&self.pool)`. On a missing row this returns `sqlx::Error::RowNotFound`.
- `?` converts it via `AppError::Database(#[from] sqlx::Error)` (`src/lib.rs:8-9`).
- `ResponseError::status_code` maps `AppError::Database(_)` → `INTERNAL_SERVER_ERROR` (`src/lib.rs:18-19`).

There is no `RowNotFound → NotFound` remapping. The pinned R4 explicitly requires "404 if absent", so the requirement is only partially met (route works for existing ids; wrong status for missing). Notably `delete_book` (`src/repository.rs:99-108`) *does* handle this correctly via `rows_affected` → `AppError::NotFound`, confirming the pattern was available and simply not applied to get-by-id.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/api.rs:35-45`, `src/repository.rs:33-48` (INSERT ... RETURNING) |
| R2 | GET /books lists all | ✓ implemented | `src/api.rs:18-24`, `src/repository.rs:58-62` |
| R3 | GET /books ?author= filter | ✓ implemented | `QueryParams.author` (`src/api.rs:9-12`); `WHERE author = ?` (`src/repository.rs:51-57`) |
| R4 | GET /books/{id} single book (404 if absent) | ~ partial | route returns book (`src/api.rs:26-33`) but missing id → 500 not 404 (`src/repository.rs:66-74`, `src/lib.rs:18-19`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/api.rs:47-72`, `src/repository.rs:76-97` (missing-id → 500 noted as medium finding) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/api.rs:74-81`, `src/repository.rs:99-108` (rows_affected → 404) |
| R7 | Data in SQLite | ✓ implemented | `SqlitePool` + `sqlite://data.db` (`src/main.rs:6`, `src/repository.rs:10-11`) |
| R8 | JSON responses, appropriate codes | ✓ implemented | 201/200/204/400/404 across handlers; `error_response` JSON (`src/lib.rs:25-29`). (get-by-id 500 captured under R4) |
| R9 | Validation: title & author required | ✓ implemented | `#[validate(length(min=1))]` + `req.validate()` (`src/lib.rs:41-50`, `src/api.rs:39-41`) |
| R10 | GET /health | ✓ implemented | `health()` (`src/api.rs:14-16`), route registered (`src/main.rs:17`) |
| R11 | README with setup/run | ✓ implemented | `README.md` (build/run/API usage) |
| R12 | ≥3 tests | ✓ implemented | 5 `#[tokio::test]` in `src/repository.rs:121-229`; test_coverage=1.0 |

**requirement_coverage = 11/12 = 0.9167**

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 1.0   → build + all tests passed
code_quality  = 0.8333
defect_rate   = 0.6712
idiomatic     = 0.87
```

5 tests in `src/repository.rs`, 0 skipped (`grep #[ignore]` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 418 |
| Files | 16 |
| Dependencies | 9 (Cargo.toml) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [high] R4 — GET /books/{id} returns 500 instead of 404 for a missing book (`src/repository.rs:66-74`)
2. [medium] R5-side — PUT /books/{id} on a missing book also returns 500 instead of 404 (`src/repository.rs:76-97`)

## Reproduce

```bash
cd experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=rust_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep3
cat scores.json
grep -n "fetch_one" src/repository.rs        # get_book_by_id, update_book
grep -n "Database" src/lib.rs                 # 500 mapping
grep -n "rows_affected\|NotFound" src/repository.rs   # delete_book does 404
```
