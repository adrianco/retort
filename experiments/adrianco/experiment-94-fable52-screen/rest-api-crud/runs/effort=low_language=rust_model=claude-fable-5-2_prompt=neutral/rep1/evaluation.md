# Evaluation: rest-api-crud · effort=low language=rust model=claude-fable-5-2 prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=claude-fable-5-2, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — from `test_coverage=1.0`
- **Build:** pass (compiled as part of the test gate) — not re-run
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

Scores read from `scores.json` (inline gate, run not yet in retort.db):
`test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.833`, `maintainability=0.758`,
`idiomatic=0.82`. `test_coverage=1.0` ⇒ build + all tests passed; not re-run per skill.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/lib.rs:150` `create_book` INSERT, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `src/lib.rs:175` `list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:180` `ListParams.author`, bound SQL param; test `list_and_filter_by_author` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/lib.rs:193` `get_book` → `ApiError::NotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/lib.rs:205` `update_book`, 404 on 0 rows changed |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/lib.rs:222` `delete_book` → 204, 404 on 0 rows |
| R7 | Data stored in SQLite | ✓ implemented | `rusqlite` `Connection`, `CREATE TABLE books` `src/lib.rs:24-36` |
| R8 | JSON responses, appropriate status codes | ✓ implemented | 201/200/204/404/422/400/500 via `ApiError` `src/lib.rs:74-96` |
| R9 | Validation: title & author required | ✓ implemented | `src/lib.rs:116` `validate()` (non-blank, trimmed); test `create_requires_title_and_author`. Returns 422 (see finding) |
| R10 | GET /health | ✓ implemented | `src/lib.rs:146` `health` → `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, env vars, endpoints, examples |
| R12 | ≥ 3 tests | ✓ implemented | 8 `#[tokio::test]` in `tests/api.rs` |

## Build & Test

Not re-run (per evaluate-run skill §2 — stored scores authoritative):

```text
scores.json: test_coverage=1.0  defect_rate=1.0
# test_coverage=1.0 ⇒ `cargo test` built and all tests passed
```

```text
tests/api.rs: 8 #[tokio::test], 0 #[ignore]
health_check, create_and_get_book, create_requires_title_and_author,
malformed_json_is_rejected_with_json_error, list_and_filter_by_author,
update_book, delete_book, missing_and_invalid_ids
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 253 (lib 241 + main 12) |
| Test LOC | 158 |
| Files (src + tests) | 3 |
| Dependencies (Cargo.toml) | 5 + 2 dev |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| code_quality | 0.833 |
| idiomatic | 0.82 |

## Findings

Full list in `findings.jsonl`:

1. [low] R9 validation returns 422 Unprocessable Entity; REQUIREMENTS parenthetical suggests 400. Defensible and documented in README; noted only for cross-run status-code comparability.

No critical/high/medium findings. The implementation is idiomatic, uses
parameterized SQL (no injection surface on `?author=`), funnels all errors
through a single `ApiError` type, and handles extractor rejections explicitly
so malformed input yields JSON 400s rather than framework plain-text.

## Reproduce

```bash
cd experiments/adrianco/experiment-94-fable52-screen/rest-api-crud/runs/effort=low_language=rust_model=claude-fable-5-2_prompt=neutral/rep1
cat scores.json                                   # stored mechanical scores (not re-run)
grep -cE "#\[tokio::test\]" tests/api.rs          # 8
grep -rnE "#\[ignore\]" . --include="*.rs" | wc -l  # 0
# optional full re-run: cargo test
```
