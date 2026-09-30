# Evaluation: effort=high_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, effort=high, prompt=neutral (agent=unknown, framework=unknown; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`)
- **Tests:** 6 test functions (plus 7 subtests in `TestValidation`) / 0 failed / 0 skipped (6 effective). Pass/fail is taken from the stored scores, not a re-run: `test_coverage=0.712`, `defect_rate=1.0` in `scores.json`.
- **Build:** pass — duration not recorded (not re-run; derived from `defect_rate=1.0`)
- **Lint:** pass — `code_quality=1.0` from `scores.json`; 0 scorer warnings (2 low lint findings from reading the code)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handlers.go:21` route, `handlers.go:136` `create`, `store.go:58` `Create` inserts all four fields; `TestCRUDLifecycle` (`handlers_test.go:70-81`) |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:22`, `handlers.go:150` `list`, `store.go:69` `List`; `TestListAndAuthorFilter` (`handlers_test.go:134-139`) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `handlers.go:151` reads `author`, `store.go:72-75` `WHERE author = ? COLLATE NOCASE`; `handlers_test.go:141-151` |
| R4 | GET /books/{id} returns one book | ✓ implemented | `handlers.go:23`, `handlers.go:159` `get` (404 at `:166`), `store.go:93` `Get`; `handlers_test.go:84-87`, `:203-206` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:24`, `handlers.go:175` `update`, `store.go:103` `Update`; `handlers_test.go:89-100`, `:207-210` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:25`, `handlers.go:196` `delete` (204), `store.go:118` `Delete`; `handlers_test.go:102-113` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:29` `sql.Open("sqlite", dsn)`, schema at `store.go:40-46`; `TestPersistence` reopens the file (`handlers_test.go:213-234`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `handlers.go:38` `writeJSON` sets `application/json`; 201 (`:147`), 200, 204 (`:208`), 400 (`:130`), 404, 413, 422, 500; Content-Type asserted at `handlers_test.go:174` |
| R9 | Validation: title and author required | ✓ implemented | `handlers.go:111-116` rejects blank/missing title and author; rejected with 422 rather than 400 (`handlers.go:121`); `TestValidation` (`handlers_test.go:160-162`, PUT at `:182`) |
| R10 | GET /health | ✓ implemented | `handlers.go:20`, `handlers.go:55` `health` pings the DB and returns `{"status":"ok"}`; `TestHealth` (`handlers_test.go:54`) |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:7-28` requirements, `go run .`, env vars, `go test ./...` |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 `Test*` functions in `handlers_test.go`; `test_coverage=0.712` (> 0) |

The `prompt=neutral` factor file prescribes no methodology and only asks for tests that demonstrate the requirements, which R12 already covers. The pinned list is the complete checklist, so no `P*` items are scored.

## Build & Test

Not re-run — the skill forbids re-running when stored scores exist. From `scores.json`:

```text
test_coverage    0.712   (tests executed; 71.2% statement coverage)
defect_rate      1.0     (build + tests succeeded)
code_quality     1.0
maintainability  0.875
idiomatic        0.78
token_efficiency 0.037
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 626 Go lines (392 non-test, 234 test); `cloc` unavailable, `wc -l` used |
| Files | 22 in the archive (4 Go source files, `go.mod`, `go.sum`, `README.md`; the rest are harness/summary files) |
| Dependencies | 10 modules in `go.mod` (1 direct: `modernc.org/sqlite`; 20 `go.sum` lines) |
| Tests total | 6 functions (+7 subtests) |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | not recorded |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] `go.mod` marks the directly imported `modernc.org/sqlite` as `// indirect` (`go.mod:15`, `store.go:7`)
2. [low] README says Go 1.22 or newer but `go.mod` requires 1.26.6 (`README.md:9`, `go.mod:3`)
3. [low] Tests discard `json.Unmarshal` errors (`handlers_test.go:61,136,143,189`)
4. [info] Validation failures return 422, not the 400 in the requirement's verification hint (`handlers.go:121`)
5. [info] Extras beyond spec: graceful shutdown, body limit, Location header, DB-backed health check

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=high_language=go_model=claude-sonnet-5-5_prompt=neutral/rep2"
cat scores.json
cat ../../../REQUIREMENTS.json
grep -cE "t\.Skip\(|t\.Skipf\(" *.go
grep -c "^func Test" handlers_test.go
wc -l *.go
grep -c "" go.sum
```
