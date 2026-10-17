# Evaluation: rest-api-crud · effort=max · language=go · model=claude-haiku-5-5 · prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=max, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 19 test functions, 0 skipped (19 effective); build + tests pass (`defect_rate=1.0`), coverage 80.6% (`test_coverage=0.806`)
- **Build:** pass — from `defect_rate=1.0` / `test_coverage=0.806` in `scores.json` (not re-run)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `api.go:97 createBook` → `store.go:66 Create` (INSERT … RETURNING id); `book.go:27 bookInput` has all four fields |
| R2 | GET /books lists all books | ✓ implemented | `api.go:86 listBooks` → `store.go:95 List`; `api_test.go TestListBooks` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `api.go:87` reads `?author=`; `store.go:98` `WHERE author LIKE ? ESCAPE '\'`; `store_test.go TestStoreListFiltersByAuthor` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `api.go:112 getBook`; `store.go:78 Get` returns `ErrNotFound` → `writeNotFound` 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `api.go:130 updateBook` → `store.go:126 Update`; full-record replace, documented |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `api.go:151 deleteBook` → `store.go:146 Delete`; 204 on success, 404 if absent |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:10` `modernc.org/sqlite`; on-disk file, WAL; `store_test.go TestStorePersistsAcrossReopen` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `api.go:287 writeJSON` sets `Content-Type`; 201/200/204/400/404/405/503 used throughout |
| R9 | Input validation: title and author required | ✓ implemented | `book.go:48` `checkRequiredText` on title/author → 400; `api_test.go TestCreateBookRejectsInvalidInput` |
| R10 | GET /health endpoint | ✓ implemented | `api.go:73 health` pings DB, 200/503; `api_test.go TestHealth` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` `## Setup`, `## Run` (`go run .`, `go build`), `## Tests` |
| R12 | At least 3 unit/integration tests | ✓ implemented | 19 test functions across 3 files; `test_coverage=0.806` > 0 |

No prompt-factor requirements: `prompt=neutral` is retort's baseline instruction, not an added checkable prompt file.

## Build & Test

Not re-run — stored mechanical scores from `scores.json` stand in (per skill step 2):

```text
scores.json
  defect_rate     = 1.0    (build + tests succeeded)
  test_coverage   = 0.806  (tests ran; 80.6% coverage)
  code_quality    = 1.0
  maintainability = 0.847
  idiomatic       = 0.9
```

Skip scan (`grep t.Skip` over `*.go`): 0 skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .go non-test) | 669 |
| Lines of code (tests) | 742 |
| Files (.go) | 7 |
| Dependencies (go.sum lines) | 50 |
| Tests total | 19 |
| Tests effective | 19 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

All findings are `info` (enhancements / notes) — no defects. Full list in `findings.jsonl`:

1. [info] ISBN-10/13 check-digit validation beyond spec (`book.go:92`)
2. [info] Strict JSON decoding rejects unknown/duplicate fields (`api.go:216`)
3. [info] 405 with `Allow` header and JSON catch-all 404 (`api.go:55`, `api.go:40`)
4. [info] Graceful shutdown on SIGINT/SIGTERM (`main.go:46`)
5. [info] PUT replaces the full record — intentional, documented (`api.go:128`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=max_language=go_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores (not re-run)
grep -rhE "^func Test" *_test.go | wc -l          # test function count (19)
grep -rnE "t\.Skip\(|t\.Skipf\(" *.go             # skip scan (none)
wc -l api.go book.go store.go main.go             # source LOC
# optional, slow: go test ./...
```
