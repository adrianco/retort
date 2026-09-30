# Evaluation: effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=default (agent=unknown, framework=unknown; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — derived from stored scores, not re-run
- **Build:** pass — duration not recorded (derived from `defect_rate=1.0`, `test_coverage=0.771` in `scores.json`)
- **Lint:** pass — 0 warnings recorded (`code_quality=1.0` in `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 1 info)

Stored scores (`scores.json`): test_coverage=0.771, code_quality=1.0, defect_rate=1.0,
maintainability=0.910, idiomatic=0.72, token_efficiency=0.048. Build, tests and lint were
**not** re-run, per the skill; the pass/fail lines above are read from these scores.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:21` route, `main.go:82` `create`, `store.go:50` `Create` INSERT of all four fields; `main_test.go:52` `TestCRUD` asserts 201 + body |
| R2 | GET /books lists all books | ✓ implemented | `main.go:22`, `main.go:97` `list`, `store.go:60` `List`; `main_test.go:108` `TestListAndAuthorFilter` (empty `[]` and 3 rows) |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `main.go:98` reads `author` query param, `store.go:63-66` `WHERE author = ?`; `main_test.go:121-124` asserts 2 of 3 rows for `?author=Alice` |
| R4 | GET /books/{id} returns one book | ✓ implemented | `main.go:23`, `main.go:106` `get`, `store.go:83` `Get` (→ `errNotFound` → 404 via `main.go:40`); `main_test.go:63` 200, `main_test.go:77` 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:24`, `main.go:120` `update`, `store.go:93` `Update` (0 rows → 404); `main_test.go:68` 200 + new title, `main_test.go:100` 404 for missing id |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:25`, `main.go:139` `delete`, `store.go:105` `Delete`; `main_test.go:73` 204, `main_test.go:81` 404 on repeat |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite` driver, `store.go:26` `sql.Open("sqlite", dsn)`, `store.go:32` `CREATE TABLE IF NOT EXISTS books`; `main.go:160` defaults to file `books.db` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:29` `writeJSON` sets `Content-Type: application/json`; 201 (`main.go:94`), 200, 204 (`main.go:149`), 400 (`main.go:85`), 404 (`main.go:41`), 500 (`main.go:45`); codes asserted throughout `main_test.go` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:63-67` in `decodeBook`, applied to both create and update; `main_test.go:87` `TestValidation` asserts 400 for missing title, missing author, blank title |
| R10 | GET /health endpoint | ✓ implemented | `main.go:20`, `main.go:74` `health` returns `{"status":"ok"}`; `main_test.go:42` `TestHealth` asserts 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` "Run" (`go run .`, `ADDR`/`DB_PATH` env) and "Test" sections, endpoint table, curl example |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test functions in `main_test.go` (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListAndAuthorFilter`); `test_coverage=0.771` > 0 so they ran |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology beyond "include tests",
which R12 already covers; the pinned list is the complete checklist, so no `P*` items.

Enhancements beyond spec (not deductions): `Location` header on create, `/health` pings the DB
(503 on failure), 1 MiB request-body cap, whitespace trimming and negative-year rejection,
400 for malformed ids.

## Build & Test

```text
(not re-run — scores read from scores.json)
defect_rate   = 1.0    => build + tests succeeded
code_quality  = 1.0    => lint clean
```

```text
go test ./...   (not re-run — scores read from scores.json)
test_coverage = 0.771  => tests executed and passed; 77.1% statement coverage
4 test functions, 0 t.Skip/t.Skipf calls
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 282 (main.go 168, store.go 114); 408 including main_test.go (126) |
| Files | 13 (excluding `_judge/`, `summary/`) |
| Dependencies | 20 go.sum lines; 10 modules in go.mod (1 direct: modernc.org/sqlite) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not recorded |

`cloc` is not installed; line counts are from `wc -l`.

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] go.mod marks the directly imported `modernc.org/sqlite` as `// indirect` (`go.mod:15`, `store.go:7`) — `go mod tidy` was not run
2. [low] HTTP server started without read/write timeouts (`main.go:167`)
3. [low] Ignored error returns in response encoding and test helpers (`main.go:32`, `main_test.go:24,57,120,122`)
4. [info] Enhancements beyond spec: Location header, DB-pinging health check, body size limit, extra validation

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral/rep2
cat scores.json
cat ../../../REQUIREMENTS.json
cat -n main.go store.go main_test.go
grep -nE "t\.Skip\(|t\.Skipf\(" *.go | wc -l
grep -c "^func Test" main_test.go
wc -l *.go
grep -c "" go.sum
find . -type f -not -path "*/.git/*" -not -path "./_judge/*" -not -path "./summary/*" | wc -l
```
