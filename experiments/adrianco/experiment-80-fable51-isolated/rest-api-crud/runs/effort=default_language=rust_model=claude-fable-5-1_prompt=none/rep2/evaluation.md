# Evaluation: effort=default language=rust model=claude-fable-5-1 prompt=none · rep 2

## Summary

- **Factors:** language=rust, model=claude-fable-5-1, prompt=none, effort=default (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — from `test_coverage=1.0`
- **Build:** pass — from `scores.json` (`test_coverage=1.0` ⇒ build + all tests passed)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/lib.rs:174` `create_book`, INSERT at :181; test `tests/api.rs:53` |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:189` `list_books`; test `tests/api.rs:156` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:194-198` WHERE author=?1; test `tests/api.rs:160` |
| R4 | GET /books/{id} single book | ✓ implemented | `src/lib.rs:207` `get_book`; 404 via `find_book` :137; test `tests/api.rs:217` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/lib.rs:214` `update_book`, 404 when 0 rows :226; test `tests/api.rs:175` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/lib.rs:232` `delete_book`, 204/404; test `tests/api.rs:201` |
| R7 | Data stored in SQLite | ✓ implemented | rusqlite bundled; `init_db` `src/lib.rs:141`; `AppState` conn :17 |
| R8 | JSON responses + status codes | ✓ implemented | `ApiError` `IntoResponse` `src/lib.rs:66`; 201/200/204/404/422/400/500 |
| R9 | Validation: title+author required | ✓ implemented | `validate` `src/lib.rs:99-118` (rejects blank/missing); test `tests/api.rs:84` — see info finding (422 not 400) |
| R10 | GET /health | ✓ implemented | `src/lib.rs:170` `health` -> `{status:"ok"}`; test `tests/api.rs:45` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, env vars, test, full API table + curl examples |
| R12 | >= 3 tests | ✓ implemented | 10 `#[tokio::test]` in `tests/api.rs`; `test_coverage=1.0` |

## Build & Test

Not re-run — stored mechanical scores are authoritative (per skill Step 2).

```text
scores.json
{"code_quality": 0.833, "token_efficiency": 0.102, "test_coverage": 1.0,
 "defect_rate": 1.0, "maintainability": 0.764, "idiomatic": 0.85}
```

`test_coverage=1.0` and `defect_rate=1.0` ⇒ `cargo build` + `cargo test` succeeded with all tests passing. 10 tests, 0 `#[ignore]`/skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 491 (lib 243, main 23, tests 225) |
| Files (excl. target/.git) | 14 |
| Dependencies (Cargo.toml) | 5 runtime + 2 dev |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| code_quality | 0.83 |
| maintainability | 0.76 |
| idiomatic | 0.85 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R9 validation rejects with `422` rather than the `400` named in `REQUIREMENTS.how_to_verify` — requirement still satisfied; noted for cross-run status-code comparison.

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=rust_model=claude-fable-5-1_prompt=none/rep2"
cat scores.json                 # stored mechanical scores (build+test+lint)
grep -rcE "#\[tokio::test\]" tests/   # test count
grep -rnE "#\[ignore\]" . --include="*.rs" | wc -l   # skip count (0)
# Optional full rebuild (not required — scores are authoritative):
# cargo test
```
