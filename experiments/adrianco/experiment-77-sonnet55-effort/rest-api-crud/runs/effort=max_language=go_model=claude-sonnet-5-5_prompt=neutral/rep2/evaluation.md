# Evaluation: effort=max_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, tooling=(none), prompt=neutral, effort=max
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `REQUIREMENTS.json`)
- **Tests:** 62 test functions, 0 failed / 0 skipped on the scoring host (62 effective) — derived from `scores.json` (`test_coverage=0.974`, `defect_rate=1.0`); tests were not re-run. One platform-conditional `t.Skip` exists (Windows only).
- **Build:** pass — duration not recorded (derived from `defect_rate=1.0` in `scores.json`)
- **Lint:** pass — 0 warnings (`code_quality=1.0` in `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `internal/api/api.go:38` route → `handlers.go:16 createBook` → `store.go:86 Create` (INSERT … RETURNING); test `api_test.go:106 TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `api.go:39` → `handlers.go:31 listBooks` → `store.go:109 List`; tests `api_test.go:334 TestListBooks`, `:323 TestListBooksWhenEmptyReturnsEmptyArray` |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `handlers.go:32` reads `author` query param; `store.go:112-115` `WHERE author = ? COLLATE NOCASE`; tests `api_test.go:356 TestListBooksFiltersByAuthor`, `store_test.go:127 TestListFiltersByAuthor` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `api.go:41` → `handlers.go:41 getBook`; `store.go:179 scanOne` maps no-rows → `book.ErrNotFound` → 404 at `handlers.go:112`; tests `api_test.go:397 TestGetBook`, `:410 TestGetBookNotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `api.go:42` → `handlers.go:57 updateBook` → `store.go:140 Update` (UPDATE … RETURNING); tests `api_test.go:443 TestUpdateBook`, `:546 TestUpdateBookNotFound` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `api.go:43` → `handlers.go:74 deleteBook` → `store.go:151 Delete` (204, or 404 when 0 rows affected); tests `api_test.go:559 TestDeleteBook`, `:580 TestDeleteBookNotFound` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:12` `modernc.org/sqlite` driver, `store.go:19-28` schema, file-backed by default (`main.go:25` `books.db`); tests `store_test.go:259 TestPersistsAcrossReopen`, `main_test.go:214 TestDataSurvivesRestart` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `respond.go:30 writeJSON` sets `Content-Type: application/json`; 201 + `Location` (`handlers.go:26-27`), 200, 204 (`:83`), 400 (`:103`, `respond.go:66`), 404 (`:113`), 405 (`api.go:58`), 413 (`respond.go:97`), 500 (`handlers.go:117`), 503 (`:92`); tests `api_test.go:134 TestBookJSONShape`, `:611 TestMethodNotAllowed`, `:637 TestUnknownRouteReturnsJSON404` |
| R9 | Validation: title and author required | ✓ implemented | `book/book.go:54 Validate` + `:72 requireText` (“is required”); 400 with per-field `details` at `respond.go:63-67`; applied to POST and PUT; tests `api_test.go:200 TestCreateBookValidation`, `:512 TestUpdateBookValidation`, `book_test.go:12 TestValidate` |
| R10 | GET /health health-check endpoint | ✓ implemented | `api.go:45` → `handlers.go:87 health` (pings DB, `{"status":"ok"}` / 503); tests `api_test.go:95 TestHealth`, `failure_test.go:73 TestHealthReportsUnavailableWhenDatabaseFails` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:14` Requirements, `:21` Setup and run (`go run .`, `go build`), `:44` Configuration, `:158` Tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | 62 `Test*` functions across 6 `_test.go` files; `test_coverage=0.974` (> 0) in `scores.json` |

Prompt factor `prompt=neutral` (`prompts/neutral.md`) prescribes no methodology and only asks for tests demonstrating the requirements — satisfied by R12; per the pinned list it adds no separately counted requirements.

**Enhancements beyond spec** (not deductions): graceful shutdown on SIGINT/SIGTERM (`main.go:94-109`), panic-recovery and request-logging middleware (`internal/api/middleware.go:38`), JSON 405 with `Allow` header and JSON 404 fallback (`api.go:40-49`), 1 MiB body cap → 413 (`respond.go:15`), strict single-JSON-object body decoding (`respond.go:74`), length/range limits on title/author/isbn/year (`book/book.go:15-19`), flag + env configuration (`main.go:37`).

## Build & Test

Not re-run — scores read from `scores.json` written by retort's scorers for this run:

```text
{"code_quality": 1.0, "token_efficiency": 0.003912908998079924, "test_coverage": 0.9740000000000001,
 "defect_rate": 1.0, "maintainability": 0.9139063636265506, "idiomatic": 0.9}
```

```text
go test ./...   (as executed by the scorer; not repeated here)
test_coverage=0.974  => build succeeded and tests executed
defect_rate=1.0      => build + tests succeeded
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 759 Go (non-test, 7 files) + 1,826 Go test lines (6 files) — `wc -l`, cloc unavailable |
| Files | 31 (includes harness logs, `_judge/`, `summary/`) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 9 indirect; 50 `go.sum` lines |
| Tests total | 62 test functions (+ `TestMain`) |
| Tests effective | 62 |
| Skip ratio | 0% on scoring host (1 Windows-only conditional skip) |
| Build duration | not recorded |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] `test-skip-1` — `TestMainShutsDownGracefullyOnSignal` is skipped on Windows (`main_test.go:374`); inactive on the darwin scoring host.
2. [info] `enh-1` — production hardening beyond spec (graceful shutdown, panic recovery, request logging, JSON 405/404, body-size cap).

No critical, high, or medium findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=max_language=go_model=claude-sonnet-5-5_prompt=neutral/rep2"
cat stack.json scores.json _meta.json
cat ../../../REQUIREMENTS.json ../../../prompts/neutral.md
grep -rn "^func Test" . --include="*_test.go" | wc -l        # 63 incl. TestMain
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go"          # main_test.go:374
wc -l $(find . -name "*.go")
grep -c "^\s*\S" go.sum                                      # 50
find . -type f -not -path "./.git/*" | wc -l                 # 31 before this report
```
