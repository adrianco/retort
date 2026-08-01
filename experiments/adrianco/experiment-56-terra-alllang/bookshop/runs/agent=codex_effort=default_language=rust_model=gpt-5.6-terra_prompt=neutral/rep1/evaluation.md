# Evaluation: agent=codex · language=rust · model=gpt-5.6-terra · prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, agent=codex, model=gpt-5.6-terra, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.72` (scores.json); no lint re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

`test_coverage=1.0` from `scores.json` ⇒ the crate builds and all tests pass. No build/test/lint was re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/lib.rs:84 create_book` INSERTs all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:106 list_books` else-branch selects all |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:112` `WHERE author = ?1`; test `filters_books_by_author` |
| R4 | GET /books/{id} single book | ✓ implemented | `src/lib.rs:138 get_book`, 404 via `not_found()` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/lib.rs:146 update_book`, 404 if `changed==0` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/lib.rs:175 delete_book`, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `rusqlite` `Connection`, `books` table `src/lib.rs:21` |
| R8 | JSON responses + status codes | ✓ implemented | `Json<...>` returns; 201/200/204/404/400 throughout |
| R9 | Validation: title & author required | ✓ implemented | `src/lib.rs:206 validate` trims, 400; test `rejects_books_without_required_fields` |
| R10 | GET /health | ✓ implemented | `src/lib.rs:80 health` → 200 `ok` (plain text; info note) |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run / Endpoints / Test sections |
| R12 | ≥3 tests | ✓ implemented | 4 `#[tokio::test]` fns in `src/lib.rs:258-349` |

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=1.0  defect_rate=0.94  code_quality=0.72
             maintainability=0.33  idiomatic=0.78  token_efficiency=0.05
test_coverage=1.0 ⇒ `cargo test` built the crate and all 4 tests passed.
```

Tests present (all active, none `#[ignore]`d):
- `creates_and_retrieves_a_book`
- `filters_books_by_author`
- `rejects_books_without_required_fields`
- `updates_and_deletes_a_book`

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 364 (lib.rs 350, main.rs 14) |
| Files (excl. target/.git) | 12 |
| Dependencies | 6 (axum, serde, serde_json, tokio, tower, rusqlite) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Both findings are info-level (no penalty):

1. [info] `/health` returns plain text `"ok"` rather than JSON — spec only requires a healthy status, so it passes.
2. [info] `?author=` filter is exact-match/case-sensitive — spec only requires filtering by author.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=rust_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                    # stored build/test/lint scores (not re-run)
grep -rnE "#\[ignore\]" src        # 0 → no disabled tests
grep -rcE "#\[tokio::test\]" src   # 4 tests
cargo test                         # optional: reproduces test_coverage=1.0
```
