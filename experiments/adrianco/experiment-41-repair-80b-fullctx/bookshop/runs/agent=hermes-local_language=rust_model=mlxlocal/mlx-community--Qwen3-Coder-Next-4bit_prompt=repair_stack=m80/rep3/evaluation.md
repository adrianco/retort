# Evaluation: rust · hermes-local · mlxlocal/Qwen3-Coder-Next-4bit · prompt=repair · stack=m80 · rep 3

> **SECOND OPINION** — re-check of a prior evaluation that scored `requirement_coverage=0.8333`
> and claimed **R4** (GET /books/{id} 500-instead-of-404) was NOT met.
> **Verdict: the first evaluator was CORRECT.** R4's "404 if absent" is genuinely broken. Score stands.

## Summary

- **Factors:** language=rust, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=repair, stack=m80
- **Status:** ok (builds + all tests pass) — but this is a **REPAIR run that made no repair**
- **Repair agent never ran:** `_agent_stdout.log` = `API call failed after 3 retries: Connection error.`; `.hermes_usage.json` → `failed:true, completed:false, api_calls:1`. Source files are dated **Jul 17 03:0x** (the previous failing attempt) while the run executed **Jul 22 17:23** — the code is **byte-identical** to the attempt FEEDBACK.md flagged. Nothing was fixed.
- **Requirements:** 10/12 implemented, 2 partial (R4, R8), 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (`test_coverage=1.0` ⇒ build + tests ran)
- **Lint:** `code_quality=0.8333` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 2 high)

## Second-opinion verdict on the R4 claim

**CONFIRMED — R4's 404-on-missing behavior is genuinely broken.** I traced the full path in the code:

1. `GET /books/{id}` handler `get_book` (`src/api.rs:31`) calls `data.get_book_by_id(id).await?`.
2. `get_book_by_id` (`src/repository.rs:66-74`) uses `.fetch_one(&self.pool).await?` (`src/repository.rs:71`). In sqlx, `fetch_one` on a query matching **no rows** returns `Err(sqlx::Error::RowNotFound)`.
3. The `?` at `src/repository.rs:72` converts that `sqlx::Error` into `AppError` via `#[from] sqlx::Error` on the **`AppError::Database`** variant (`src/lib.rs:9`) — so a missing row becomes `AppError::Database(RowNotFound)`, **not** `AppError::NotFound`.
4. `status_code()` (`src/lib.rs:17-23`) maps `AppError::Database(_)` → `INTERNAL_SERVER_ERROR` (**500**) at `src/lib.rs:19`.

The `AppError::NotFound` → 404 mapping exists (`src/lib.rs:12-13,21`) but `get_book_by_id` **never uses it** — it is only used by `delete_book` (`src/repository.rs:105-107`). So a `GET /books/{id}` for an absent id returns **500, not 404**. This is exactly the defect FEEDBACK.md called out, and — because the repair agent never executed — it was **not fixed**. The first evaluator's evidence (repository.rs:71 / lib.rs:9 / lib.rs:19) is accurate.

The same root defect also affects `PUT /books/{id}` on a missing id (`update_book` at `src/repository.rs:76-97` likewise uses `fetch_one`), which returns 500 too. R5 does not require 404-on-missing, so R5 stands, but this is a second instance of the wrong status code and is why R8 ("appropriate HTTP status codes") is also partial.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/api.rs:35` create_book; `src/repository.rs:33-48` INSERT…RETURNING all 4 fields; test `test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `src/api.rs:18`; `src/repository.rs:59` SELECT all; test `test_get_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/api.rs:10` QueryParams.author; `src/repository.rs:52-53` WHERE author=?; `test_get_books` asserts filtered len==1 |
| R4 | GET /books/{id} single book (404 if absent) | ~ partial | Happy path works (`src/api.rs:26-33`) but missing id → **500 not 404**: `src/repository.rs:71` fetch_one→RowNotFound → `src/lib.rs:9` #[from] Database → `src/lib.rs:19` 500 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/api.rs:47`; `src/repository.rs:76-97`; test `test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/api.rs:74`; `src/repository.rs:99-109` returns `AppError::NotFound`(404) on 0 rows; test `test_delete_book` |
| R7 | SQLite / embedded DB | ✓ implemented | `sqlx::SqlitePool` `src/repository.rs:2,11`; schema `src/repository.rs:16-30` |
| R8 | JSON responses w/ appropriate status codes | ~ partial | JSON everywhere; correct 201/200/204/400/404-on-delete. But missing-resource GET/PUT return **500 where 404 is appropriate** (`src/api.rs:31,70` → `src/lib.rs:19`) |
| R9 | Validation: title & author required | ✓ implemented | `src/lib.rs:43-46` `#[validate(length(min=1))]`; `src/api.rs:39` req.validate()→400 |
| R10 | GET /health | ✓ implemented | `src/api.rs:14-16` health(); route registered `src/main.rs:17` |
| R11 | README with setup/run | ✓ implemented | `README.md` documents build/run/endpoints |
| R12 | ≥3 tests | ✓ implemented | 5 `#[tokio::test]` in `src/repository.rs:121-229`; `test_coverage=1.0` |

**implemented = 10, partial = 2 (R4, R8), missing = 0 → requirement_coverage = 10/12 = 0.8333.**

## Build & Test

Read from `scores.json` (not re-run, per skill Step 2):

```text
test_coverage   = 1.0    (build + all tests passed)
code_quality    = 0.8333
defect_rate     = 0.6712
idiomatic       = 0.87
token_efficiency= 0.5
maintainability = 0.5337
```

5 `#[tokio::test]` tests, 0 skipped/ignored (`grep -rE '#\[ignore\]' src/` → 0). Note: none of the tests exercise the missing-book HTTP path, which is why the 500-vs-404 defect passes CI yet fails the spec.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src/*.rs) | 418 |
| Files (excl. target/, summary/) | 17 |
| Dependencies (Cargo.toml) | 5 |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [high] R4 — GET /books/{id} returns 500 instead of 404 for a missing book (repair never applied the fix)
2. [high] R8 — inappropriate 500 status code for a missing resource on GET/PUT-by-id

## Reproduce

```bash
cd experiments/adrianco/experiment-41-repair-80b-fullctx/bookshop/runs/agent=hermes-local_language=rust_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=repair_stack=m80/rep3
cat _agent_stdout.log .hermes_usage.json        # repair agent failed to run
stat -f "%Sm %N" src/*.rs _agent_stdout.log     # src (Jul 17) predates run (Jul 22): byte-identical, no fix
sed -n '66,74p' src/repository.rs               # fetch_one → RowNotFound
sed -n '6,23p'  src/lib.rs                       # #[from] sqlx::Error → Database → 500
cat scores.json                                  # test_coverage=1.0
```
