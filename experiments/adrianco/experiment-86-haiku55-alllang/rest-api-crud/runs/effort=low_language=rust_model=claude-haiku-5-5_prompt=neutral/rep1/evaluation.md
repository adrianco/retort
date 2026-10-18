# Evaluation: rest-api-crud · effort=low language=rust model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=claude-haiku-5-5, effort=low, prompt=neutral, agent=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — from `test_coverage=1.0` in `scores.json`
- **Build:** pass (compiles; `test_coverage=1.0` ⇒ build + all tests ran green) — not re-run
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/lib.rs:166 create_book`, INSERT at :174, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `src/lib.rs:183 list_books` None-branch SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:188-196` WHERE author=?1 COLLATE NOCASE; `tests/api.rs:83` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/lib.rs:207 get_book` -> fetch, `ApiError::NotFound`; `tests/api.rs:150` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/lib.rs:215 update_book` UPDATE, 404 if changed==0 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/lib.rs:234 delete_book` DELETE, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/lib.rs:111-129` rusqlite bundled, `CREATE TABLE books` |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/204/404/400 across handlers; `ApiError::into_response` :57 |
| R9 | Validation: title & author required | ✓ implemented | `src/lib.rs:75-84 validate` trims + rejects blank; `tests/api.rs:106` |
| R10 | GET /health | ✓ implemented | `src/lib.rs:152 health` -> `{"status":"ok"}`; `tests/api.rs:44` |
| R11 | README with setup & run | ✓ implemented | `README.md` setup/run/test + env-var table |
| R12 | >= 3 tests, test_coverage>0 | ✓ implemented | 8 `#[tokio::test]` in `tests/api.rs`; `test_coverage=1.0` |

## Build & Test

Not re-run (per skill step 2 — scores already computed). Stored mechanical scores from `scores.json`:

```text
test_coverage   = 1.0     # build + all tests passed, tests executed
code_quality    = 0.8333  # lint/quality
defect_rate     = 0.8980
maintainability = 0.7478
idiomatic       = 0.6
token_efficiency= 0.0468
```

`cargo test` compiles `src/lib.rs` + `src/main.rs` and runs 8 integration tests in `tests/api.rs` (full CRUD lifecycle, author filter, validation, malformed JSON, 404s, update-rollback). `test_coverage=1.0` ⇒ all green.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 266 (lib.rs 253 + main.rs 13) |
| Lines of code (tests) | 183 |
| Files (excl. target/.git) | 14 |
| Dependencies (direct, Cargo.toml) | 5 runtime + 2 dev |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | not re-run |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no defects:

1. [info] E1 — Validation exceeds spec (negative year, ISBN charset, blank-after-trim)
2. [info] E2 — Malformed JSON mapped to 400 (consistent `{"error":...}` envelope) instead of axum default 422
3. [info] I1 — README says "2021 edition or later" while Cargo.toml pins `edition = "2024"`

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=rust_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                 # stored mechanical scores (build/test/lint)
grep -rcE "#\[tokio::test\]" tests/   # 8 tests
grep -rE "#\[ignore\]" . --include="*.rs" | wc -l   # 0 skips
# optional full re-run: cargo test
```
