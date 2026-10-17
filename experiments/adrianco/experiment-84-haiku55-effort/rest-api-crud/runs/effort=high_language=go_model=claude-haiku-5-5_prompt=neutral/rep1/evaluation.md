# Evaluation: effort=high language=go model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 23 test functions, 0 skipped (23 effective) — build + all tests pass (test_coverage=0.759 from scores.json)
- **Build:** pass (test_coverage=0.759 ⇒ build succeeded; defect_rate=1.0)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `internal/api/server.go:createBook` → `store.go:Create`; `server_test.go:TestCreateReturnsLocationAndCreated` |
| R2 | GET /books lists all books | ✓ implemented | `server.go:listBooks` → `store.go:List`; `server_test.go:TestListBooksAndAuthorFilter` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `server.go:listBooks` reads `?author`; `store.go:List` adds `WHERE author = ? COLLATE NOCASE`; `TestListBooksAndAuthorFilter` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `server.go:getBook`; returns 404 on `store.ErrNotFound`; `TestNotFoundForUnknownBook` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:updateBook` → `store.go:Update`; `TestBookLifecycle`, `TestUpdateValidationDoesNotChangeBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:deleteBook` → `store.go:Delete` (204); `TestDeleteTwiceReturnsNotFound` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `internal/store/store.go` uses `modernc.org/sqlite`, real schema; `store_test.go:TestDataPersistsAcrossReopen` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `server.go:writeJSON/writeError`; 201/200/204/400/404/405/413; `TestMethodNotAllowedIsJSON`, `TestUnknownRouteIsJSON404` |
| R9 | Input validation: title and author required | ✓ implemented | `book.go:Validate` requires title/author (400 with details); `TestCreateValidation` |
| R10 | GET /health health check | ✓ implemented | `server.go:health` pings DB, returns `{status:ok}` / 503; `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` (5.1 KB) present with setup/run docs |
| R12 | At least 3 unit/integration tests | ✓ implemented | 23 test functions across book/store/api; test_coverage=0.759 (>0) |

## Build & Test

Scores read from `scores.json` (inline gate output) — build/tests not re-run per skill guidance.

```text
scores.json
test_coverage = 0.759   (build + all tests passed; 75.9% line coverage)
defect_rate   = 1.0     (build + test succeeded)
code_quality  = 1.0
maintainability = 0.9055
idiomatic     = 0.85
token_efficiency = 0.0194
```

```text
tests: 23 functions, 0 skipped
  internal/book  : 2  (TestValidate, TestValidateUsesCurrentYear)
  internal/store : 7  (Create/Get/List/Update/Delete + persistence)
  internal/api   : 14 (lifecycle, validation, filters, errors, health, routing)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test .go) | 592 |
| Lines of code (tests) | 660 |
| Files (excl .git) | 18 |
| Dependencies (go.sum lines; 1 direct: modernc.org/sqlite) | 50 |
| Tests total | 23 |
| Tests effective | 23 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from gate) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] ISBN-10/13 check-digit validation beyond spec (`book.go:validISBN10/13`)
2. [info] Comprehensive JSON error handling for all edge cases (`server.go:decodeBook`, fallback routes)
3. [info] Test coverage 75.9% — build + all tests pass; uncovered region is mainly `main.go` run/shutdown

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=high_language=go_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (no re-run)
cat ../../../REQUIREMENTS.json                     # pinned 12-item checklist
grep -rnE "^func Test" internal --include="*.go"   # 23 test functions
grep -rcE "t\.Skip\(|t\.Skipf\(" internal --include="*.go"  # 0 skips
```
