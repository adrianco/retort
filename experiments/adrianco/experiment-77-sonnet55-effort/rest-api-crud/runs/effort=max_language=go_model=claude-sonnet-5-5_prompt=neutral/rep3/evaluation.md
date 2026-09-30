# Evaluation: effort=max_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, effort=max, prompt=neutral (agent=unknown, framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `REQUIREMENTS.json`)
- **Tests:** 76 test functions + 2 fuzz targets; pass/fail counts not re-run — `test_coverage=0.953`, `defect_rate=1.0` from `scores.json` ⇒ build and tests passed. 5 conditional `t.Skipf` sites (loopback-unavailable guards), 0 unconditional skips
- **Build:** pass — derived from `scores.json` (`defect_rate=1.0`); duration not recorded
- **Lint:** pass — `code_quality=1.0` from `scores.json`; 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 6 low, 1 info)

Stored scores (`scores.json`, not re-run): `test_coverage=0.953`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.915`, `idiomatic=0.88`, `token_efficiency=0.0016`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `internal/api/api.go:49`, `handlers.go:31 createBook` → `sqlite/store.go:87 Create` (INSERT of all four fields); `books_test.go:56 TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `api.go:48`, `handlers.go:46 listBooks`, `store.go:113 List`; `books_test.go:287 TestListBooksWhenEmpty`, `:15 TestBookLifecycle` |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `handlers.go:54` passes `query.Get("author")`; `store.go:116` `WHERE author = ? COLLATE NOCASE`; `books_test.go:297 TestListBooksFilterByAuthor`, `store_test.go:134` |
| R4 | GET /books/{id} returns one book | ✓ implemented | `api.go:52`, `handlers.go:66 getBook`, `store.go:99 Get` (→ `ErrNotFound` → 404 at `handlers.go:143`); `books_test.go:347 TestGetBookNotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `api.go:53`, `handlers.go:81 updateBook`, `store.go:142 Update`; `books_test.go:379 TestUpdateBook`, `:433 TestUpdateBookNotFound` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `api.go:54`, `handlers.go:99 deleteBook` (204), `store.go:157 Delete`; `books_test.go:480 TestDeleteBook` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:12` `modernc.org/sqlite`, schema `store.go:20-29`, file-backed default `main.go:25 books.db`; `store_test.go:257 TestDataSurvivesReopen`, `main_test.go:151` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `respond.go:31 writeJSON` sets `application/json`; 201+Location `handlers.go:41-42`, 204 `:108`, 400 `:127`, 404 `:144`, 405 `:118`, 413 `respond.go:71`, 500 `handlers.go:149`; `routing_test.go:40,52` |
| R9 | Validation: title and author required | ✓ implemented | `book/book.go:64-69 Validate` ("is required"), 400 via `respond.go:54 writeValidationError`; `books_test.go:127 TestCreateBookValidation`, `:446 TestUpdateBookValidation`; DB `CHECK` backstop `store.go:23-24` |
| R10 | GET /health | ✓ implemented | `api.go:45`, `handlers.go:18 health` (DB ping, 200 `{"status":"ok"}` / 503); `routing_test.go:14 TestHealth`, `:27` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` "Requirements", "Setup and run" (`go run .`, `go build -o bookapi .`), "Configuration" |
| R12 | At least 3 unit/integration tests | ✓ implemented | 76 `Test*` + 2 `Fuzz*` across 8 test files; `test_coverage=0.953` (> 0) |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology beyond "include tests", which R12 covers; the pinned list is the complete checklist, so no `P*` items.

## Build & Test

```text
(not re-run — skill step 2: read stored scores)
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0016, "test_coverage": 0.953,
              "defect_rate": 1.0, "maintainability": 0.915, "idiomatic": 0.88}
```

```text
go test ./...   (as run by retort's scorer; output not archived)
test_coverage=0.953 ⇒ tests executed and passed; defect_rate=1.0 ⇒ build+test succeeded
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 832 Go non-test (+ 2,218 test) = 3,050 total |
| Files | 21 (8 source `.go`, 8 `_test.go`, go.mod, go.sum, README.md, TASK.md, .gitignore; harness files excluded) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 9 indirect; 50 `go.sum` lines |
| Tests total | 78 (76 `Test*` + 2 `Fuzz*`) |
| Tests effective | 78 assumed (passed + failed; per-test counts not archived) |
| Skip ratio | 0% unconditional; 5 conditional `t.Skipf` sites in `main_test.go` affecting 4 tests only when loopback listen is unavailable |
| Build duration | not recorded |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] `main_test.go:141` — server-start helper skips the end-to-end restart test when loopback listen fails
2. [low] `main_test.go:217` — TestRunReportsStartupFailures conditional skip
3. [low] `main_test.go:240` — TestRunReportsStartupFailures conditional skip (second listener)
4. [low] `main_test.go:261` — TestServeReturnsListenerFailures conditional skip
5. [low] `main_test.go:278` — TestServeLetsInFlightRequestsFinish conditional skip

Also: [low] unauthenticated API on `:8080` with unenforced Content-Type (disclosed in README); [info] extensive hardening beyond spec.

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=max_language=go_model=claude-sonnet-5-5_prompt=neutral/rep3
cat scores.json stack.json _meta.json
cat ../../../REQUIREMENTS.json ../../../prompts/neutral.md
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go"
grep -c "^func Test" $(find . -name "*_test.go")
wc -l $(find . -name "*.go")
grep -c "^\s*\S" go.sum
```
