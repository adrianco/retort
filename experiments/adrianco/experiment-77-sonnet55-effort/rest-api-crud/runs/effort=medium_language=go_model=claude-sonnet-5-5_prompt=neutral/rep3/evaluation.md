# Evaluation: effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=medium (agent/framework recorded as `unknown` in `stack.json`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `rest-api-crud/REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — derived from stored scores, not re-run (`test_coverage=0.755`, `defect_rate=1.0` in `scores.json`)
- **Build:** pass — duration not recorded (derived from `defect_rate=1.0`)
- **Lint:** pass — 0 warnings (`code_quality=1.0`)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handlers.go:18`, `handlers.go:82` `create`; `store.go:52` `Store.Create` inserts all four fields; `handlers_test.go:53` `TestCRUD` asserts 201 |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:19`, `handlers.go:97` `list`; `store.go:63` `Store.List`; `handlers_test.go:125` asserts 3 books |
| R3 | GET /books supports ?author= filter | ✓ implemented | `handlers.go:98` passes `r.URL.Query().Get("author")`; `store.go:66-68` `WHERE author = ?`; `handlers_test.go:128-133` (2 matches / 0 matches) |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `handlers.go:20`, `handlers.go:106` `get`, 404 at `handlers.go:112-113`; `handlers_test.go:64`, `handlers_test.go:78` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:21`, `handlers.go:122` `update`; `store.go:96` `Store.Update` (404 on 0 rows); `handlers_test.go:69`, `handlers_test.go:102` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:22`, `handlers.go:143` `delete` → 204; `store.go:108`; `handlers_test.go:74-85` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:27` `sql.Open("sqlite", dsn)`, `store.go:33` `CREATE TABLE IF NOT EXISTS books`; file DB `books.db` by default (`main.go:17`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `handlers.go:28` `writeJSON` sets `Content-Type: application/json`; 201 (`:94`), 200, 204 (`:155`), 400 (`:76`, `:85`), 404 (`:113`), 500 (`:40`), 503 (`:45`) |
| R9 | Validation: title and author required | ✓ implemented | `handlers.go:63-66` in `decodeBook` (after `TrimSpace`); `handlers_test.go:88` `TestValidation` asserts 400 for missing title, missing author, blank title |
| R10 | GET /health endpoint | ✓ implemented | `handlers.go:17`, `handlers.go:43` `health` (pings DB); `handlers_test.go:42` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — "Run" (`go run .`, `ADDR`/`DB_PATH`), "Test", endpoint table, curl example |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test functions in `handlers_test.go` (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListFilter`); `test_coverage=0.755 > 0` |

Enhancements beyond spec (not deductions): year range validation, `Location` header on create,
DB-backed health check with 503, 1 MiB request body cap, 400 on non-numeric ids.

## Build & Test

Not re-run — scores read from `scores.json` written by retort's scorers during the run.

```text
scores.json
{"code_quality": 1.0, "token_efficiency": 0.05003077809647296, "test_coverage": 0.755,
 "defect_rate": 1.0, "maintainability": 0.8717615319168946, "idiomatic": 0.76}
```

```text
go test ./...   (not re-executed)
test_coverage=0.755  -> tests executed; 75.5% statement coverage
defect_rate=1.0      -> build + tests succeeded
skips: grep -E "t\.Skip\(|t\.Skipf\(" *.go -> 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 267 non-blank Go lines excluding tests (390 incl. tests; 432 raw lines) |
| Files | 14 (excluding `_judge/`, `summary/`) — 4 Go source files |
| Dependencies | 1 direct (`modernc.org/sqlite`), 10 modules in `go.mod`, 20 `go.sum` lines |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not recorded |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] `go.mod:15` marks the directly imported `modernc.org/sqlite` as `// indirect` (needs `go mod tidy`).
2. [low] `handlers.go:53-57` — oversized bodies and trailing data are not distinguished from malformed JSON (no 413).
3. [low] `handlers_test.go:58`, `:115`, `:24` — tests discard some errors and don't assert seeding POST statuses.
4. [info] Enhancements beyond spec (year validation, `Location` header, DB-backed health, body cap); PUT is a full replace.

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral/rep3
cat scores.json
cat ../../../REQUIREMENTS.json
grep -nE "t\.Skip\(|t\.Skipf\(" *.go | wc -l
grep -c "^func Test" handlers_test.go
grep -cvE '^\s*$' main.go store.go handlers.go handlers_test.go
grep -c "^\s*\S" go.sum
```
