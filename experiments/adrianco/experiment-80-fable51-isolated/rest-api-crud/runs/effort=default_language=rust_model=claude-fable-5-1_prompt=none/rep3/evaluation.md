# Evaluation: rest-api-crud (effort=default, language=rust, model=claude-fable-5-1, prompt=none) · rep 3

## Summary

- **Factors:** language=rust, model=claude-fable-5-1, prompt=none, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — from `test_coverage=1.0`
- **Build:** pass (not re-run — `test_coverage=1.0` in scores.json/retort.db implies build+tests succeeded)
- **Lint:** pass — `code_quality=0.833` (retort.db)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

This is a clean, complete run. Every pinned requirement is implemented with real
SQLite persistence and exercised by integration tests; build and the full test
suite pass (`test_coverage=1.0`, `defect_rate=1.0`). No skipped/ignored tests.

## Requirements

Checklist from the pinned `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/lib.rs:162 create_book` → `src/db.rs:58 insert`; test `create_then_get_book` (tests/api.rs:53) |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:153 list_books` → `src/db.rs:73 list`; test `list_books_supports_author_filter` (tests/api.rs:146) |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:148 ListParams.author` → `src/db.rs:75-80` WHERE author COLLATE NOCASE; test tests/api.rs:150 |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `src/lib.rs:177 get_book` → `db::get`; 404 via `not_found` (lib.rs:122); test tests/api.rs:210 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:188 update_book` → `src/db.rs:98 update`; test `update_book_replaces_fields` (tests/api.rs:164) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:201 delete_book` → `src/db.rs:113 delete`; test `delete_book_removes_it` (tests/api.rs:190) |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.rs:25-46` rusqlite Connection + CREATE TABLE books; Cargo.toml rusqlite bundled |
| R8 | JSON responses + correct status codes | ✓ implemented | 201 (lib.rs:170), 200, 204 (lib.rs:207), 404 (lib.rs:52), 400 (lib.rs:47-51), 500 (lib.rs:53); all `Json(...)` |
| R9 | Validation: title and author required | ✓ implemented | `src/lib.rs:81-102 BookInput::validate` (trim + non-blank); test `create_rejects_missing_or_blank_required_fields` (tests/api.rs:85) |
| R10 | GET /health | ✓ implemented | `src/lib.rs:144 health` returns `{"status":"ok"}`; test `health_check_returns_ok` (tests/api.rs:45) |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Requirements/Run/Test/API/Examples/Layout sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 9 `#[tokio::test]` in tests/api.rs; `test_coverage=1.0` |

## Build & Test

Not re-run per skill Step 2 — stored mechanical scores stand in for the toolchain:

```text
scores.json / retort.db:
  test_coverage = 1.0   → build + all tests passed (test gate)
  defect_rate   = 1.0   → build+test succeeded
  code_quality  = 0.833 → lint/quality (Lint: pass)
```

```text
tests: 9 #[tokio::test] in tests/api.rs, 0 #[ignore], 0 skipped → 9 effective, all passing
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 569 |
| Files (excl. target/, logs) | 13 |
| Dependencies (Cargo.toml) | 5 runtime (axum, rusqlite, serde, serde_json, tokio) + 2 dev |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All 5 findings are `info`-level (enhancements beyond spec); no defects. Full list in `findings.jsonl`:

1. [info] 201 Created returns a Location header (src/lib.rs:168)
2. [info] SQLite I/O offloaded to spawn_blocking with poisoned-lock recovery (src/lib.rs:128)
3. [info] Graceful shutdown on ctrl_c (src/main.rs:18)
4. [info] author filter is exact case-insensitive match (satisfies R3) (src/db.rs:77)
5. [info] PUT is full replacement, documented (src/db.rs:98, README.md)

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=rust_model=claude-fable-5-1_prompt=none/rep3"
cat scores.json                                  # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json                   # pinned 12-item checklist
grep -rE "#\[tokio::test\]|#\[test\]" . --include="*.rs" | wc -l   # 9 tests
grep -rE "#\[ignore\]" . --include="*.rs" | wc -l                  # 0 skips
wc -l src/*.rs tests/*.rs                         # 569 LOC
```
