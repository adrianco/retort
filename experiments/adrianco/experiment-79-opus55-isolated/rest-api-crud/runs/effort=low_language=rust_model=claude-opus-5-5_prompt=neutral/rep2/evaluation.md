# Evaluation: rest-api-crud (effort=low, rust, claude-opus-5-5, prompt=neutral) · rep 2

## Summary

- **Factors:** language=rust, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (implied by `test_coverage=1.0`; `defect_rate=1.0`) — not re-run
- **Lint:** pass — `code_quality=0.833` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/lib.rs:167 create_book` — INSERT, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:187 list_books` — `SELECT ... ORDER BY id` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/lib.rs:192-198` — `WHERE author = ?1 COLLATE NOCASE`; test `list_and_filter_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/lib.rs:207 get_book` — `.optional()` → `ApiError::NotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:216 update_book` — UPDATE, 404 when `changed==0` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:239 delete_book` — DELETE, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/lib.rs:109 Db::open` rusqlite; `CREATE TABLE books` (line 119) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/404/422/400 across handlers; `ApiError::into_response` (line 76) |
| R9 | Validation: title and author required | ✓ implemented | `src/lib.rs:42 BookInput::validate` — rejects blank/missing; test `create_rejects_missing_or_blank_required_fields`. Returns 422, not the 400 named in how_to_verify (low finding) |
| R10 | GET /health endpoint | ✓ implemented | `src/lib.rs:163 health` — `{status:"ok"}`; test `health_check` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — Setup/Run/Test/API sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/api.rs` — 10 `#[tokio::test]` functions; `test_coverage=1.0` |

## Build & Test

Not re-run (per skill: read stored scores). From `scores.json`:

```text
test_coverage = 1.0    # build + all tests passed (test gate)
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.8333 # lint/quality
maintainability = 0.7395
idiomatic     = 0.88
token_efficiency = 0.0989
```

Skip scan: `grep -rE "#\[ignore\]|#\[cfg\(ignore\)\]" tests src` → 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 473 (lib 263, main 18, tests 192) |
| Files (source) | 3 (`src/lib.rs`, `src/main.rs`, `tests/api.rs`) |
| Dependencies | 4 runtime (axum, tokio, rusqlite, serde/serde_json) + 2 dev |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 — validation failures return 422 rather than the 400 implied by the spec (malformed/wrong-type JSON does return 400). Defensible REST semantics; noted for conformance.
2. [info] Implementation exceeds the low-effort minimum: case-insensitive filter, poisoned-lock recovery, graceful shutdown, distinct error bodies, testable lib/main split.

## Reproduce

```bash
cd experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=rust_model=claude-opus-5-5_prompt=neutral/rep2
cat scores.json                 # stored mechanical scores (no re-run)
grep -rE "#\[ignore\]" tests src   # skip scan → 0
# optional independent check:
cargo test                      # builds + runs the 10 integration tests
```
