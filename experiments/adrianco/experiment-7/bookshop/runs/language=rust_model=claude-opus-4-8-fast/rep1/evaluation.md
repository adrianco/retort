# Evaluation: language=rust_model=claude-opus-4-8-fast · rep 1

## Summary

- **Factors:** language=rust, model=claude-opus-4-8-fast, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — test_coverage=1.0 from scores.json (build+tests succeeded)
- **Lint:** pass — code_quality=0.833 from scores.json
- **Architecture:** summary skill unavailable
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/lib.rs:136` `create_book` accepts BookInput, inserts via SQL, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:158` `list_books` queries all rows; tested in `tests/api.rs:117` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/lib.rs:163-169` branches on `query.author`; tested in `tests/api.rs:125` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `src/lib.rs:182` `get_book` with 404 on missing; tested in `tests/api.rs:70,189` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:201` `update_book` with 404 on missing; tested in `tests/api.rs:149` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:226` `delete_book` returns 204; tested in `tests/api.rs:166` |
| R7 | Data stored in SQLite | ✓ implemented | `src/lib.rs:83` `init_db` uses `rusqlite`; `Cargo.toml:11` bundled feature |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create, 200 get/list/update, 204 delete, 400 validation, 404 missing |
| R9 | Input validation: title and author required | ✓ implemented | `src/lib.rs:112` `validate` rejects empty/whitespace; tested in `tests/api.rs:85` |
| R10 | GET /health endpoint | ✓ implemented | `src/lib.rs:131` returns `{"status":"ok"}`; tested in `tests/api.rs:41` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 104 lines with build, run, config, API docs, test instructions |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 integration tests in `tests/api.rs`; test_coverage=1.0 |

## Build & Test

```text
Build & test scores read from scores.json (not re-run):
  test_coverage  = 1.0    (build + all tests passed)
  code_quality   = 0.8333
  defect_rate    = 1.0    (no defects)
  maintainability = 0.7381
  idiomatic      = 0.8000
  token_efficiency = 0.2700
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Rust source only) | 468 (lib.rs: 251, main.rs: 16, api.rs: 201) |
| Files | 11 |
| Dependencies | 7 (5 runtime + 2 dev) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0.0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Single Mutex<Connection> serialises all DB access — acceptable for demo, but a pool would scale better

## Reproduce

```bash
cd experiment-7/bookshop/runs/language=rust_model=claude-opus-4-8-fast/rep1
cat scores.json                          # pre-computed build/test/lint scores
cat stack.json                           # factor levels
grep -rE '#\[ignore\]' --include="*.rs"  # skipped tests (none)
find . -type f -not -path "*/target/*"   # file listing
```
