# Evaluation: language=rust_model=opus_tooling=none · rep 1

## Summary

- **Factors:** language=rust, model=opus, tooling=none
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=0.8333 from retort.db (0 warnings surfaced)
- **Architecture:** summary skill not invoked
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 1 medium)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book | ✓ implemented | `src/lib.rs:70-98` — `create_book` accepts title, author, year, isbn; returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:101-123` — `list_books` queries all rows |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:33-34` `ListQuery` + `lib.rs:106` branches on `q.author` |
| R4 | GET /books/{id} returns single book | ✓ implemented | `src/lib.rs:136-152` — `get_book` with 404 on missing |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/lib.rs:154-186` — `update_book` with 404 on missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/lib.rs:188-200` — `delete_book` returns 204, 404 on missing |
| R7 | Data stored in SQLite | ~ partial | `src/lib.rs:37` uses rusqlite `Connection::open(path)` but `src/main.rs:6` passes `":memory:"` — data lost on restart; `how_to_verify` requires "not just in-memory state" |
| R8 | JSON responses with proper HTTP codes | ✓ implemented | 201 Created, 200 OK, 204 No Content, 400 Bad Request, 404 Not Found throughout |
| R9 | Input validation: title/author required | ✓ implemented | `src/lib.rs:74-81` (create) and `src/lib.rs:159-166` (update) validate both fields, reject empty/whitespace |
| R10 | GET /health endpoint | ✓ implemented | `src/lib.rs:53` route + `lib.rs:62-64` returns `{"status":"ok"}` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` covers build, run, test, and endpoint documentation |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/integration.rs` — 5 tests: health, create+get, validation, update+delete, author filter |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage    = 1.0  (build + all tests passed)
  code_quality     = 0.8333
  defect_rate      = 1.0  (build+test succeeded)
  maintainability  = 0.7854
  idiomatic        = 0.68
  token_efficiency = 0.50
```

```text
5 integration tests in tests/integration.rs:
  health_works                — verifies GET /health returns 200
  create_and_get_book         — POST + GET round-trip
  create_book_requires_title  — validation rejects missing title
  update_and_delete_book      — PUT + DELETE + 404 after delete
  list_books_filter_by_author — creates 3 books, filters by author
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 391 (lib.rs 200 + main.rs 12 + integration.rs 179) |
| Files | 9 |
| Dependencies | 7 (axum, tokio, serde, serde_json, rusqlite, tower, uuid) + 2 dev (http-body-util, tower) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |

## Findings

Top by severity (full list in `findings.jsonl`):

1. **[medium]** R7 — SQLite used in `:memory:` mode only — data does not persist across restarts (`src/main.rs:6`)

## Reproduce

```bash
cd experiment-1/runs/language=rust_model=opus_tooling=none/rep1
cat stack.json
cat TASK.md
# Scores read from retort.db via:
python3 -c "
import sqlite3
conn = sqlite3.connect('file:../../retort.db?mode=ro', uri=True)
cur = conn.cursor()
cur.execute(\"SELECT metric_name, value FROM run_results WHERE run_id = (SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'$.language')='rust' AND json_extract(run_config_json,'$.model')='opus' AND json_extract(run_config_json,'$.tooling')='none' AND replicate=1 AND status='completed' ORDER BY finished_at DESC LIMIT 1)\")
print(cur.fetchall())
"
grep -c '#\[tokio::test\]' tests/integration.rs
grep -rE '#\[ignore\]' --include='*.rs' .
wc -l src/lib.rs src/main.rs tests/integration.rs
```
