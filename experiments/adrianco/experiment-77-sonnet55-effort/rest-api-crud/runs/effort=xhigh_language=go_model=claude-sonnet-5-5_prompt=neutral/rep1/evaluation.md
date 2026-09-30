# Evaluation: effort=xhigh_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, effort=xhigh, prompt=neutral (agent=unknown, framework=unknown; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, fixed denominator 12)
- **Tests:** 22 passed / 0 failed / 0 skipped (22 effective) — 22 top-level `Test*` functions counted by grep; pass status derived from `scores.json` (`defect_rate=1.0`, `test_coverage=0.762`), not re-run
- **Build:** pass — duration not measured (derived from `scores.json` `defect_rate=1.0`; toolchain not re-run per skill)
- **Lint:** pass — 0 warnings (`code_quality=1.0` from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

Stored scores (`scores.json`): `test_coverage=0.762`, `code_quality=1.0`, `defect_rate=1.0`,
`maintainability=0.863`, `idiomatic=0.85`, `token_efficiency=0.024`. `test_coverage` here is
statement coverage (76.2%), well above 0, so the test gate is met.

The `neutral` prompt factor (`prompts/neutral.md`) prescribes no methodology and only asks for
tests demonstrating the requirements — already covered by R12 — so it adds no `P*` items. The
requirement list is the pinned `REQUIREMENTS.json`, used verbatim.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `internal/api/api.go:46` route, `api.go:73` `create` → `internal/books/store.go:79` `Create` (INSERT of all four fields, `store.go:85`); test `api_test.go:98` `TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `api.go:47`, `api.go:87` `list` → `store.go:115` `List`; test `api_test.go:181` `TestListAndAuthorFilter` (empty list is `[]`, then all three) |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `api.go:88` reads `author` query → `store.go:118-121` `WHERE author = ? COLLATE NOCASE`; tests `api_test.go:212-217`, `store_test.go:112` |
| R4 | GET /books/{id} returns one book | ✓ implemented | `api.go:48`, `api.go:97` `get` → `store.go:98` `Get` (`ErrNotFound` → 404 at `api.go:145`); test `api_test.go:220` `TestGetBook` (200, 404, 400 for bad ids) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `api.go:49`, `api.go:110` `update` → `store.go:146` `Update` (full replace, 404 via `requireAffected`); test `api_test.go:239` `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `api.go:50`, `api.go:127` `delete` → `store.go:164` `Delete`; test `api_test.go:277` `TestDeleteBook` (204, then 404) |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:10` `modernc.org/sqlite` driver, `store.go:19-28` schema, `store.go:38` `sql.Open("sqlite", …)`; `main.go:30` default `DB_PATH=books.db`; on-disk reopen test `store_test.go:206` `TestPersistsOnDisk` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `api.go:213` `writeJSON` sets `Content-Type: application/json`; 201 (`api.go:84`), 200, 204 (`api.go:136`), 400/404/500 (`api.go:140-151`), 405 (`api.go:196`), 413 (`api.go:185`); test `api_test.go:296` `TestRoutingErrorsAreJSON` |
| R9 | Validation: title and author required | ✓ implemented | `internal/books/books.go:56` `Input.Clean` (`books.go:63-64`, `69-70` "is required") → 400 at `api.go:144`; tests `api_test.go:121` `TestCreateValidation`, `api_test.go:164`, `store_test.go:53` `TestValidation`; also enforced on PUT (`api_test.go:264`) |
| R10 | GET /health endpoint | ✓ implemented | `api.go:45`, `api.go:64` `health` (pings DB, 200 `{"status":"ok"}` / 503); tests `api_test.go:79` `TestHealth`, `api_test.go:91` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:8-11` Requirements, `README.md:12-33` "Setup and run" (`go mod download`, `go run .`, build, env vars), `README.md:35-40` Tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | 22 test functions: 12 in `internal/api/api_test.go`, 10 in `internal/books/store_test.go`; `test_coverage=0.762` (> 0, tests executed) |

Enhancements beyond spec (not deductions): request-body size cap (413), JSON 404/405 with `Allow`
header, panic-recovery and request-logging middleware, graceful shutdown, DB-pinging health check,
URI-safe SQLite DSN with WAL + busy timeout, length/range validation on all fields, `Location`
header on create.

Minor observations (not spec deviations, no finding filed): unknown JSON fields are silently
ignored (`api.go:167`, no `DisallowUnknownFields`); `year: 0` doubles as "not given"
(`books.go:53-55`), so an omitted year is returned as `"year": 0`.

## Build & Test

Not re-run — the skill forbids re-running the toolchain when stored scores exist.

```text
# build (derived)
scores.json: defect_rate=1.0  => build + tests succeeded
```

```text
# test (derived)
scores.json: test_coverage=0.762, code_quality=1.0
grep -hE "^func Test" internal/*/*_test.go | wc -l   => 22
grep -rnE "t\.Skip\(|t\.Skipf\(|t\.SkipNow\(" . --include="*.go" | wc -l   => 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 594 (non-test `.go`, `wc -l`; `cloc` unavailable) |
| Lines of test code | 586 |
| Files | 17 (excluding `summary/`, `_judge/`, and evaluation outputs) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 9 indirect; 50 `go.sum` lines |
| Tests total | 22 |
| Tests effective | 22 |
| Skip ratio | 0% |
| Build duration | not measured (scores read from `scores.json`) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Hardening beyond spec: body-size cap, JSON 404/405 with `Allow`, panic recovery, request logging, graceful shutdown, DB-pinging health check (`enhancement`, not a deduction)

No critical, high, medium or low findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=xhigh_language=go_model=claude-sonnet-5-5_prompt=neutral/rep1"
cat scores.json
cat ../../../REQUIREMENTS.json
cat ../../../prompts/neutral.md
grep -hE "^func Test" internal/*/*_test.go | wc -l
grep -rnE "t\.Skip\(|t\.Skipf\(|t\.SkipNow\(" . --include="*.go" | wc -l
wc -l main.go internal/books/books.go internal/books/store.go internal/api/api.go
wc -l internal/*/*_test.go
grep -c "" go.sum
# optional, to confirm the stored scores (not run during this evaluation):
# go test ./...
```
