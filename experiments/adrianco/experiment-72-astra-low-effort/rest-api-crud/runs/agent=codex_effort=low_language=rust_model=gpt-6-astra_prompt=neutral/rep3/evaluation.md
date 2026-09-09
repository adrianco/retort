# Evaluation: rest-api-crud · agent=codex effort=low language=rust model=gpt-6-astra prompt=neutral · rep 3

## Summary

- **Factors:** language=rust, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=axum
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — via `test_coverage=1.0` in scores.json
- **Build:** pass (inferred from `test_coverage=1.0`; tests build the crate)
- **Lint:** pass — `code_quality=0.8333` in scores.json (no re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `lib.rs:168 create_book` INSERTs + returns 201 |
| R2 | GET /books lists all | ✓ implemented | `lib.rs:192 list_books` ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `lib.rs:188 Filter`, `lib.rs:198 WHERE (?1 IS NULL OR author = ?1)`; tested `tests.rs:84` |
| R4 | GET /books/{id} single | ✓ implemented | `lib.rs:204 get_book` → `find` → 404 if absent |
| R5 | PUT /books/{id} update | ✓ implemented | `lib.rs:211 update_book` UPDATE, 404 on 0 rows |
| R6 | DELETE /books/{id} | ✓ implemented | `lib.rs:232 delete_book` DELETE, 404 on 0 rows |
| R7 | SQLite / embedded DB | ✓ implemented | `Cargo.toml:15 rusqlite bundled`; `lib.rs:26` CREATE TABLE; file persistence tested `tests.rs:171` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/405 throughout; `ApiError::into_response` `lib.rs:101` emits JSON |
| R9 | Validation: title+author required | ✓ implemented | `lib.rs:69 BookInput::validate` trims + rejects blank → 400; tested `tests.rs:114` |
| R10 | GET /health | ✓ implemented | `lib.rs:122 health` runs `SELECT 1`, returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/run, env vars, API table, curl examples |
| R12 | ≥3 tests | ✓ implemented | 5 `#[tokio::test]` in `tests.rs`; `test_coverage=1.0` |

No requirement is partial, missing, or cannot-verify.

## Build & Test

Scores read from `scores.json` (inline gate output) — toolchain not re-run, per skill:

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.8333
             maintainability=0.4658  idiomatic=0.76  token_efficiency=0.0341
```

`test_coverage=1.0` ⇒ the crate built and all 5 tests passed. No test failures, no
skipped/`#[ignore]` tests (grep for `#[ignore]` / `#[cfg(ignore)]` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 461 (lib.rs 248, tests.rs 197, main.rs 16) |
| Files (excl. target/) | 14 |
| Dependencies (Cargo.toml declared) | 5 runtime + 2 dev |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | not re-run (scores from scores.json) |

## Findings

All findings are low/info — no deductions. Full list in `findings.jsonl`:

1. [low] `?author=` filter is exact case-sensitive match (documented) — satisfies R3.
2. [low] All DB access serialized through a single `Arc<Mutex<Connection>>`.
3. [info] POST sets a `Location` header beyond spec.
4. [info] Author filter parameterized with an explicit SQL-injection test.

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=rust_model=gpt-6-astra_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rnE "#\[ignore\]|#\[cfg\(ignore\)\]" . --include="*.rs" | wc -l   # skip count = 0
grep -rcE "#\[tokio::test\]|#\[test\]" tests.rs   # test count = 5
# Optional re-verify (slow): cargo test --locked
```
