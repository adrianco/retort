# Evaluation: agent=hermes-local_language=go_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown (Gorilla Mux), prompt=neutral
- **Status:** ok — build + all tests pass, all 12 requirements implemented
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 test funcs (3 sub-tests) passed / 0 failed / 0 skipped (all effective); coverage 33.7%
- **Build:** pass (defect_rate=1.0 from retort scores.json)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 3 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `book_handler.go:28 CreateBook`, `model/book.go:27 CreateBook` persists |
| R2 | GET /books lists all books | ✓ implemented | `book_handler.go:86 ListBooks` → `model/book.go:73 GetAllBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `book_handler.go:87-95` → `model/book.go:54 GetBooksByAuthor` (untested) |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `book_handler.go:62 GetBook`, 404 at :73-76; tested `TestGetBookNotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `book_handler.go:107 UpdateBook`; happy path works — but no 404 on missing id + id=0 in response (findings) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `book_handler.go:154 DeleteBook`; tested `TestDeleteBook` — but no 404 on missing id (finding) |
| R7 | Data stored in SQLite | ✓ implemented | `mattn/go-sqlite3` in go.mod, `migrate/migrate.go` CREATE TABLE, `books.db` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400/204 across handlers; minor: error bodies labelled text/plain (finding) |
| R9 | Validation: title & author required | ✓ implemented | `book_handler.go:35-43`; tested `TestCreateBookValidationError` |
| R10 | GET /health health check | ✓ implemented | `book_handler.go:177 HealthCheck`; tested `TestHealthCheck` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (install/build/run/endpoints) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 6 test funcs; test_coverage=0.337 > 0 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
defect_rate    = 1.0    → build + tests succeeded
test_coverage  = 0.337  → tests executed, 33.7% line coverage
code_quality   = 1.0
maintainability= 0.886   idiomatic = 0.74
```

Test inventory (`go test ./...`): TestHealthCheck, TestCreateBook, TestCreateBookValidationError (3 sub-tests: missing title / missing author / invalid JSON), TestGetBook, TestGetBookNotFound, TestDeleteBook — 0 `t.Skip`, 0 failures.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, source incl. tests) | 593 |
| Source files (excl. binary/db/logs) | 9 |
| Dependencies (go.sum entries) | 13 |
| Tests total (funcs) | 6 (+3 sub-tests) |
| Tests effective | 6/6 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 33.7% |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] PUT and DELETE return success for non-existent IDs — `UpdateBook`/`DeleteBook` ignore `RowsAffected`, so 404 branches are unreachable.
2. [low] PUT response body has id=0 and zero timestamps (response built from request, ID not set).
3. [low] Error responses labelled `text/plain` despite JSON body (`http.Error`).
4. [low] Coverage 33.7% — `?author=` filter (R3), update path (R5), and store/migrate/main untested.

## Reproduce

```bash
cd "experiment-22-qwennext80b/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep2"
cat scores.json                 # mechanical scores (build/test/lint) — not re-run
go test ./... -cover            # optional re-verify: 6 pass, ~33.7% coverage
grep -rnE "t\.Skip" --include='*.go' .   # 0 skips
```
