# Evaluation: rest-api-crud · effort=low language=go model=claude-fable-5-2 prompt=none · rep 1

## Summary

- **Factors:** language=go, model=claude-fable-5-2, effort=low, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 test functions (several table-driven subtests), 0 skipped — all effective. test_coverage=0.731 (build + tests pass; defect_rate=1.0 from scores.json)
- **Build:** pass — not re-run (defect_rate=1.0, test_coverage=0.731 from scores.json)
- **Lint:** pass — code_quality=0.9555 from scores.json
- **Architecture:** single-package Go service (`main.go`), `net/http` 1.22+ method-routed mux over a SQLite store (`modernc.org/sqlite`, pure-Go). `run-summary` skill unavailable in this session — not generated.
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `main.go:144` createBook → INSERT; TestCreateAndGetBook |
| R2 | GET /books lists all books | ✓ implemented | `main.go:165` listBooks; TestListAndAuthorFilter |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:168` `WHERE author = ? COLLATE NOCASE`; TestListAndAuthorFilter asserts 2/0 |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:197` getBook; 404 at `main.go:207`; TestNotFoundAndBadID |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:217` updateBook; 404 on no rows; TestUpdateBook |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:240` deleteBook → 204/404; TestDeleteBook |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `main.go:53` OpenDB `sql.Open("sqlite", …)`, CREATE TABLE books |
| R8 | JSON responses, appropriate status codes | ✓ implemented | `main.go:91` writeJSON; 201/200/204/400/404/500 used across handlers |
| R9 | Validation: title and author required | ✓ implemented | `main.go:32` validate() rejects blank title/author → 400; TestCreateValidation |
| R10 | GET /health health check | ✓ implemented | `main.go:136` health pings DB → 200 ok / 503; TestHealth |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` Setup/Run/Test/API sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` — 7 top-level Test funcs, 0 skips; test_coverage=0.731 |

## Build & Test

Not re-run per skill guidance — mechanical scores read from `scores.json`:

```text
test_coverage = 0.731   (build succeeded, test suite ran and passed; coverage fraction)
defect_rate   = 1.0     (build + test success)
code_quality  = 0.9555
maintainability = 1.0
idiomatic     = 0.85
token_efficiency = 0.0632
```

Skip scan (`grep t.Skip` over *.go): 0 skipped tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: main.go) | 274 |
| Lines of code (tests: main_test.go) | 176 |
| Files (excl. .git) | 13 |
| Dependencies (go.sum lines; 1 direct: modernc.org/sqlite) | 50 |
| Tests total (top-level funcs) | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |

## Findings

No correctness, build, test, or requirement defects. All items are beyond-spec enhancements (info):

1. [info] Location header set on create (`main.go:161`)
2. [info] Request body size capped at 1MiB (`main.go:112`)

## Reproduce

```bash
cd runs/effort=low_language=go_model=claude-fable-5-2_prompt=none/rep1
cat scores.json
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -rE "^func Test" main_test.go | wc -l
# optional, re-run toolchain:
go test ./...
```
