# Evaluation: effort=low_language=rust_model=claude-fable-5-1_prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=claude-fable-5-1, prompt=neutral, effort=low (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass — code_quality=0.833 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/lib.rs:149 create_book` + INSERT; test `create_and_get_book` |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:169 list_books`; test `list_with_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:174-177 WHERE ?1 IS NULL OR author = ?1`; test asserts filtered len==1 |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/lib.rs:184 get_book` → `ApiError::NotFound`; test `unknown_or_invalid_id_is_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:197 update_book`; test `update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:221 delete_book` → 204; test `delete_book` |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `src/lib.rs:74 open_db` rusqlite, `books` table |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/204/404/400/422 via `ApiError` `src/lib.rs:45-64`; see low finding on 422 vs 400 |
| R9 | Validation: title and author required | ✓ implemented | `src/lib.rs:118 validate` (trims, empty→error); test `create_requires_title_and_author` |
| R10 | GET /health health check | ✓ implemented | `src/lib.rs:145 health` → `{"status":"ok"}`; test `health_check` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` — setup, run, env vars, endpoints table |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 8 tests in `tests/api.rs` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage = 1.0   ⇒ cargo build + cargo test: all tests passed
code_quality  = 0.833
defect_rate   = 1.0
maintainability = 0.765
idiomatic     = 0.8
```

Skipped/ignored tests: `grep -rE "#\[ignore\]" --include=*.rs` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 417 (src + tests) |
| Files (excl. target/.git) | 14 |
| Dependencies (Cargo.toml) | 4 runtime + 2 dev |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Validation errors return 422 where the spec's R9 suggests 400 (`src/lib.rs:50`). Malformed JSON correctly returns 400. 422 is a defensible choice for semantic validation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=rust_model=claude-fable-5-1_prompt=neutral/rep1"
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rE "#\[ignore\]" . --include="*.rs" | wc -l # skipped tests
# to re-verify from scratch (optional; slow):
cargo test
```
