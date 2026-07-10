# Evaluation: agent=hermes-local language=go prompt=neutral · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=neutral
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial (R7), 0 missing
- **Tests:** 12 test functions (14 cases incl. subtests) passed / 0 failed / 0 skipped (14 effective) — `defect_rate=1.0`, `test_coverage=0.658` from `scores.json`
- **Build:** pass — `defect_rate=1.0` (build+test gate); binary `book-api` present
- **Lint:** pass — `code_quality=0.956`, `maintainability=0.979`, `idiomatic=0.8` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 1 low, 1 info)

## Requirements

Pinned checklist from `../../../REQUIREMENTS.json` (12 requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:228` createBook → `main.go:64` CreateBook; `TestCreateBook_Valid` |
| R2 | GET /books lists all | ✓ implemented | `main.go:254` listBooks → `main.go:103` ListBooks; `TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:255` authorFilter, WHERE author `main.go:109`; `TestListBooks_AuthorFilter` |
| R4 | GET /books/{id} single | ✓ implemented | `main.go:267` getBook, 404 at `main.go:281`; `TestGetBookByID`, `TestGetBookByID_NotFound` |
| R5 | PUT /books/{id} update | ✓ implemented | `main.go:289` updateBook → `main.go:141` UpdateBook; `TestUpdateBook` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `main.go:325` deleteBook → `main.go:169` DeleteBook; `TestDeleteBook` |
| R7 | Data stored in SQLite/embedded | ~ partial | `modernc.org/sqlite` + schema `main.go:42`, but DSN is `:memory:` `main.go:342` → no durable persistence |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON` `main.go:220`; 201/200/404/400/409/204/500 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `validateBook` `main.go:207-211`; `TestCreateBook_Invalid` (also over-strict on year — see findings) |
| R10 | GET /health | ✓ implemented | `main.go:351`; `TestHealthCheck` |
| R11 | README with setup/run | ✓ implemented | `README.md` (121 lines) — endpoints, setup, run |
| R12 | ≥3 unit/integration tests | ✓ implemented | 12 test funcs in `main_test.go`; `test_coverage=0.658 > 0` |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and adds no additional checkable requirements — TASK.md is the whole spec.

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill guidance):

```text
defect_rate     = 1.0    → build + tests passed (gate)
test_coverage   = 0.658  → tests executed; 65.8% coverage
code_quality    = 0.956
maintainability = 0.979
idiomatic       = 0.800
token_efficiency= 0.0151
```

Tests: `go test ./...` — 12 functions (`TestCreateBook_Valid`, `TestCreateBook_Invalid` [3 subtests], `TestGetBookByID`, `TestGetBookByID_NotFound`, `TestListBooks`, `TestListBooks_AuthorFilter`, `TestUpdateBook`, `TestDeleteBook`, `TestHealthCheck`, `TestDuplicateISBN`, `TestListBooks_Empty`, `TestDeleteNonExistentBook`). 0 skips (`grep t.Skip` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source) | 361 (main.go) + 388 (main_test.go) = 749 |
| README | 121 lines |
| Files (excl. summary/, binary) | 13 |
| Tests total | 14 (12 funcs + 2 extra subtests) |
| Tests effective | 14 |
| Skip ratio | 0% |
| Dependencies (go.sum entries) | 51 (1 direct: modernc.org/sqlite) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [high] R7 — SQLite runs in `:memory:` mode (`main.go:342`); no data persists across restarts, failing R7's "not just in-memory state" check.
2. [medium] R9 — validation requires `year` beyond the title+author spec (`main.go:213`); spec-compliant creates without a year are wrongly rejected.
3. [low] isbn column is `NOT NULL UNIQUE` (`main.go:48`) though ISBN isn't a required/spec key; two books without an ISBN collide → 409.
4. [info] DELETE of a non-existent book returns 204, never 404 (`main.go:169`, `main.go:337`).

## Reproduce

```bash
cd experiment-20-hermes35b-alllang/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep3
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
grep -cE "^func Test" main_test.go                # 12 test functions
# optional re-verify: go test ./...
```
