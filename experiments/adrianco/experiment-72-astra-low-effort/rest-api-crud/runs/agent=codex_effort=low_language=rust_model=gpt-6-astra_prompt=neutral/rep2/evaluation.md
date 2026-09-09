# Evaluation: rest-api-crud · agent=codex effort=low language=rust model=gpt-6-astra prompt=neutral · rep 2

## Summary

- **Factors:** language=rust, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (from `test_coverage=1.0` / `defect_rate=1.0`; not re-run)
- **Lint:** pass — `code_quality=0.833` from `scores.json` (clippy `-D warnings` documented in README)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `lib.rs:164 create_book` — INSERT + re-read, 201 |
| R2 | GET /books lists all | ✓ implemented | `lib.rs:190 list_books` — SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `lib.rs:197-201` parameterized WHERE author=?1; test `tests.rs:95` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `lib.rs:216 get_book` via `find()` → `ApiError::not_found` |
| R5 | PUT /books/{id} update | ✓ implemented | `lib.rs:223 update_book` — UPDATE, 404 if 0 rows |
| R6 | DELETE /books/{id} delete | ✓ implemented | `lib.rs:244 delete_book` — DELETE, 404 if 0 rows, 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `Cargo.toml:8` rusqlite bundled; `lib.rs:25-33` schema; persist test `tests.rs:227` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/204/400/404/422/415/405 across handlers; `lib.rs:100-104` JSON errors |
| R9 | Validation: title & author required | ✓ implemented | `lib.rs:68-77 BookInput::validate` trims + rejects blank (400); test `tests.rs:128` |
| R10 | GET /health | ✓ implemented | `lib.rs:121 health` runs `SELECT 1`, returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, env vars, API table, verify |
| R12 | ≥3 tests | ✓ implemented | `tests.rs` — 7 `#[tokio::test]`; `test_coverage=1.0` |

## Build & Test

Not re-run per skill policy — stored mechanical scores used as the build+test signal.

```text
scores.json: test_coverage=1.0, defect_rate=1.0, code_quality=0.833,
             maintainability=0.446, idiomatic=0.72, token_efficiency=0.0377
```

`test_coverage=1.0` ⇒ `cargo test` built the crate and all 7 integration tests passed. No `#[ignore]` / disabled tests (grep count 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, lib+main) | 273 |
| Lines of code (incl. tests.rs) | 516 |
| Files (excl. target/.git) | 14 |
| Dependencies (Cargo.toml decls) | 6 (+2 dev) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All findings are `info`-level enhancements beyond the spec — no defects, no gaps:

1. [info] E1 — 415/422/405 handling + `Location` header + route/method fallbacks (beyond R8)
2. [info] E2 — SQLite offloaded via `spawn_blocking`, keeping the async runtime unblocked
3. [info] E3 — DB CHECK constraints mirror app validation; `books_author` index
4. [info] E4 — tests cover SQL-injection metacharacters and persistence across DB reopen

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=rust_model=gpt-6-astra_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores (build/test/lint signal)
grep -rnE "#\[ignore\]" . --include="*.rs" | wc -l # 0 disabled tests
grep -rnE "#\[(tokio::)?test\]" . --include="*.rs" | wc -l  # 7 tests
# (optional) full re-run:
cargo test --locked
```
