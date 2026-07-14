# Evaluation: language=rust_model=claude-opus-4-7_tooling=none · rep 2

## Summary

- **Factors:** language=rust, model=claude-opus-4-7, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=0.833 from retort.db
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/handlers.rs:42` `create_book` accepts BookInput; `tests/api.rs:37` `create_and_get_book` |
| R2 | GET /books lists all books | ✓ implemented | `src/handlers.rs:60` `list_books`; `tests/api.rs:84` `list_filters_by_author` asserts 3 returned |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/handlers.rs:13` `ListQuery { author }`, `src/db.rs:41` `list(author_filter)`; `tests/api.rs:100` filters to 2 Alice books |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `src/handlers.rs:70` `get_book` returns 404 if absent; `tests/api.rs:58` + `tests/api.rs:160` `get_missing_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/handlers.rs:83` `update_book` validates + checks existence; `tests/api.rs:135` asserts updated fields |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/handlers.rs:106` `delete_book` returns 204/404; `tests/api.rs:147` confirms 204 then 404 on re-get |
| R7 | Data stored in SQLite | ✓ implemented | `Cargo.toml:9` `rusqlite = { version = "0.31", features = ["bundled"] }`; `src/db.rs:17` CREATE TABLE |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All handlers return `Json()` via axum; codes: 201 create, 200 get/list/update, 204 delete, 400 validation, 404 not found |
| R9 | Input validation: title and author required | ✓ implemented | `src/handlers.rs:22` `validate()` checks both; `tests/api.rs:69` `create_missing_title_returns_400` |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/handlers.rs:18` returns `{"status":"ok"}` 200; `tests/api.rs:24` `health_returns_ok` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 86 lines covering build, run, test, env vars, full API table, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 tests in `tests/api.rs`: health, create+get, validation 400, list+filter, update+delete, 404 |

## Build & Test

```text
# Stored scores from retort.db (build/test not re-run):
test_coverage    = 1.0   (build + all tests passed)
code_quality     = 0.833
defect_rate      = 0.949
maintainability  = 0.786
idiomatic        = 0.760
token_efficiency = 0.138
```

```text
# Test inventory (from tests/api.rs):
6 #[tokio::test] functions, 0 #[ignore], 0 skipped
  - health_returns_ok
  - create_and_get_book
  - create_missing_title_returns_400
  - list_filters_by_author
  - update_and_delete_book
  - get_missing_returns_404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 456 |
| Files | 13 |
| Dependencies | 7 runtime + 2 dev = 9 |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | (stored score; not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Mutex<Connection> limits concurrent SQLite throughput — `src/db.rs:6-8`

## Reproduce

```bash
cd experiment-6/runs/language=rust_model=claude-opus-4-7_tooling=none/rep2
# Scores were read from retort.db; build/test not re-run
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='rust' AND json_extract(er.run_config_json,'$.model')='claude-opus-4-7' AND json_extract(er.run_config_json,'$.tooling')='none' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -cE '#\[tokio::test\]|#\[test\]' tests/api.rs
grep -rE '#\[ignore\]' . --include='*.rs' | wc -l
find . -name '*.rs' -not -path '*/target/*' -exec wc -l {} +
```
