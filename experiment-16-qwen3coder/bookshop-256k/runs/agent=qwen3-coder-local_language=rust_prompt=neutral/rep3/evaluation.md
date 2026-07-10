# Evaluation: agent=qwen3-coder-local language=rust prompt=neutral · rep 3

## Summary

- **Factors:** language=rust, agent=qwen3-coder-local, framework=warp, prompt=neutral
- **Status:** ok (build + tests pass) — but with major spec gaps (no SQLite, tests don't exercise the app)
- **Requirements:** 9/12 implemented, 2 partial, 1 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — all trivial placeholders; the substantive tests are in a dead, uncompiled file
- **Build:** pass — `test_coverage=1.0` from scores.json (build + tests executed)
- **Lint:** pass — `code_quality=0.8333` from scores.json; `idiomatic=0.2` (very low — `unsafe static mut`)
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (0 critical, 4 high, 2 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | `src/main.rs:94` create_book persists; but client must supply `id`, `uuid` dep unused |
| R2 | GET /books lists all | ✓ implemented | `src/main.rs:61` get_books returns the Vec |
| R3 | GET /books ?author= filter | ✓ implemented | `src/main.rs:64-70` filters by author query param |
| R4 | GET /books/{id} single (404) | ✓ implemented | `src/main.rs:80` get_book_by_id, 404 via BookNotFound |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/main.rs:116` update_book replaces matching book |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/main.rs:139` delete_book removes by position |
| R7 | Data stored in SQLite | ✗ missing | `src/main.rs:23` in-memory `static mut Vec`; sqlx unused; README admits "in-memory" |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/400 returned; nit: DELETE 204 carries a body (`main.rs:144`) |
| R9 | Validation: title & author required | ✓ implemented | `src/main.rs:96-101,118-123` reject empty title/author with 400 |
| R10 | GET /health | ✓ implemented | `src/main.rs:154` health_check returns `{"status":"OK"}` |
| R11 | README with setup/run | ✓ implemented | README.md present + thorough; but falsely claims SQLite persistence |
| R12 | ≥3 unit/integration tests | ~ partial | 3 tests run & pass (literal bar met) but all placeholders; real tests dead (`src/main_test.rs`) |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 1.0     (build succeeded; 3 tests executed and passed)
code_quality    = 0.8333
defect_rate     = 0.6958
maintainability = 0.4377
idiomatic       = 0.2      (unsafe static mut global; non-idiomatic Rust)
token_efficiency= 0.0403
```

Tests that actually compile/run (all trivial):
```text
tests/api_tests.rs::test_api_endpoint_exists        assert_eq!(true, true)
tests/integration_tests.rs::test_api_endpoints_exist assert_eq!(true, true)
tests/integration_tests.rs::test_book_structure      JSON-shape check (no app code)
```
Substantive tests (`src/main_test.rs`: health/create/get/validation) are **never compiled** — `src/main.rs` does not declare `mod main_test`, so cargo ignores the file.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.rs, source only) | 216 |
| Dead test file (main_test.rs, uncompiled) | 331 |
| Running test LOC (api_tests + integration_tests) | 36 |
| Files (excl. target/, agent logs) | 14 |
| Dependencies (Cargo.toml) | 6 |
| Tests total / effective | 3 / 3 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=1.0) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R7 — No SQLite/embedded DB persistence; data held in an in-memory `static mut` global
2. [high] `unsafe static mut` shared storage is a data race under concurrent warp requests (UB; hard error in edition 2024)
3. [high] The only substantive tests live in `src/main_test.rs`, a dead file never compiled or run
4. [high] Every test that runs is a placeholder/tautology — the application is effectively untested
5. [medium] README claims SQLite persistence the code does not implement

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=rust_prompt=neutral/rep3
cat scores.json                       # build/test/quality scores (not re-run)
grep -n "static mut\|unsafe\|sqlx" src/main.rs
grep -n "mod main_test" src/main.rs   # (absent -> main_test.rs is dead)
grep -rn "assert_eq!(true, true)" tests/
```
