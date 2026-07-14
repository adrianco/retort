# Evaluation: bookshop-128k / agent=qwen3-coder-local language=rust · rep 3

## Summary

- **Factors:** language=rust, agent=qwen3-coder-local, framework=unknown (actix-web + sqlx in practice)
- **Status:** ok (build + tests pass) — but conformance gaps: R12 fails and R3 is broken
- **Requirements:** 10/12 implemented, 1 partial (R3), 1 missing (R12)
- **Tests:** 1 passed / 0 failed / 0 skipped (1 effective) — the sole test is a trivial `2+2` placeholder
- **Build:** pass — test_coverage=1.0 from `scores.json`
- **Lint:** pass — code_quality=0.833 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 3 high, 1 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/main.rs:18` `create_book` → `database.rs:30` INSERT, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `src/main.rs:63` → `database.rs:72` `SELECT * ... ORDER BY id` |
| R3 | GET /books ?author= filter | ~ partial | `src/main.rs:64` `web::Query<Option<String>>` cannot bind `author`; `?author=X` 400s instead of filtering |
| R4 | GET /books/{id} by id | ✓ implemented | `src/main.rs:92` → `database.rs:56`, 404 on `None` (`main.rs:120`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/main.rs:126` → `database.rs:93`, 404 when 0 rows |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/main.rs:176` → `database.rs:123`, 404 when nothing deleted |
| R7 | SQLite / embedded DB | ✓ implemented | sqlx `SqlitePool` + `CREATE TABLE books` `database.rs:16` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/500 via `HttpResponse::*().json(...)` throughout `main.rs` |
| R9 | Validate title & author required | ✓ implemented | `src/main.rs:21,27` (create) & `129,135` (update) → 400 |
| R10 | GET /health | ✓ implemented | `src/main.rs:11` returns 200 `{"status":"OK"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `cargo run`, endpoints, DB |
| R12 | ≥ 3 unit/integration tests | ✗ missing | Only `src/lib.rs:11` `it_works` (`add(2,2)==4`); `tests/` empty; no route/DB test |

## Build & Test

Build/test not re-run — mechanical scores read from `scores.json` (inline gate):

```text
test_coverage = 1.0   → cargo build + `cargo test` pass (1/1 test)
code_quality  = 0.833
defect_rate   = 0.646
maintainability = 0.485
idiomatic     = 0.42
```

The single passing test does not exercise the book API; test_coverage=1.0 is a
pass-rate over one trivial placeholder test, not evidence the service works.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .rs) | 446 |
| Files (excl. target/, agent log) | 16 |
| Dependencies (runtime) | 5 (actix-web, serde, serde_json, sqlx, tokio) |
| Tests total | 1 |
| Tests effective | 1 |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R12 — only a trivial placeholder test; <3 real tests (`src/lib.rs:11`)
2. [high] R3 — `?author=` filter uses `web::Query<Option<String>>`, does not filter (`src/main.rs:64`)
3. [high] SQLite connect string lacks create-if-missing; server exits on fresh start (`src/main.rs:217`)
4. [medium] New DB pool per request; injected `web::Data<SqlitePool>` unused (`src/main.rs:36,65,94,144,178`)
5. [low] Dead placeholder crate `book_api/` left in workspace (`book_api/src/main.rs:1`)

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-128k/runs/agent=qwen3-coder-local_language=rust/rep3
cat scores.json                                  # mechanical scores (do not re-run toolchain)
grep -rn '#\[test\]' src/                         # confirm sole test
sed -n '63,66p' src/main.rs                       # broken author filter extractor
sed -n '213,224p' src/main.rs                     # sqlite connect w/o create_if_missing
```
