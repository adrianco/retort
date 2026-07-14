# Evaluation: language=rust_model=claude-fable-5 · rep 2

## Summary

- **Factors:** language=rust, model=claude-fable-5, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0, defect_rate=1.0 from scores.json
- **Lint:** code_quality=0.8333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/lib.rs:115-127` — `create_book` inserts all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:129-150` — `list_books` queries all rows |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:133-148` — `ListParams.author` filters via SQL WHERE; `tests/api.rs:91` exercises it |
| R4 | GET /books/{id} single book | ✓ implemented | `src/lib.rs:152-155` — `get_book` via `fetch_book`; 404 on missing |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/lib.rs:157-172` — `update_book` with validation; 404 if id absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/lib.rs:174-180` — `delete_book` returns 204; 404 if absent |
| R7 | SQLite embedded DB | ✓ implemented | `Cargo.toml:10` — `rusqlite` with `bundled`; `src/lib.rs:183-195` creates table |
| R8 | JSON responses + HTTP codes | ✓ implemented | `src/lib.rs:44-63` — `ApiError::IntoResponse` maps to 400/404/500 JSON; handlers return 201/200/204 |
| R9 | Input validation (title, author) | ✓ implemented | `src/lib.rs:75-90` — `validate()` rejects empty/whitespace; `tests/api.rs:71` exercises it |
| R10 | GET /health endpoint | ✓ implemented | `src/lib.rs:111-113` — returns `{"status":"ok"}`; `tests/api.rs:36` exercises it |
| R11 | README.md with instructions | ✓ implemented | `README.md` — setup, run, test commands, API docs, examples |
| R12 | At least 3 tests | ✓ implemented | `tests/api.rs` — 7 async integration tests covering all endpoints |

## Build & Test

```text
Build/test scores from scores.json (not re-run):
  test_coverage:  1.0   (build + all tests passed)
  defect_rate:    1.0   (build+test succeeded)
  code_quality:   0.8333
  maintainability: 0.7926
  idiomatic:      0.7000
  token_efficiency: 0.2202
```

```text
Test functions (7 total, 0 skipped):
  health_check_returns_ok
  create_and_get_book
  create_rejects_missing_required_fields
  list_books_supports_author_filter
  update_book_replaces_fields
  delete_book_removes_it
  get_missing_book_returns_404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Rust only) | 420 |
| Files | 12 |
| Dependencies | 7 (5 runtime + 2 dev) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Internal database errors exposed to API consumers — `src/lib.rs:58`
2. [info] Comprehensive README with examples and layout (enhancement)

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=rust_model=claude-fable-5/rep2
cat scores.json
cat stack.json
grep -rE "#[ignore]" --include="*.rs" .
grep -c "#[tokio::test]" tests/api.rs
find . -name "*.rs" -not -path "*/target/*" -exec wc -l {} +
find . -type f -not -path "*/target/*" -not -path "*/.git/*" | wc -l
```
