# Evaluation: agent=hermes-local language=go prompt=ATDD · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local (Qwen3.6-35B-A3B, local), prompt=ATDD, framework=unknown (stdlib `net/http`)
- **Status:** ok — builds and all tests pass; one required deliverable (README.md) is missing
- **Requirements:** 11/12 implemented, 0 partial, 1 missing (R11 README)
- **Tests:** 33 passed / 0 failed / 0 skipped (33 effective) — 75.9% line coverage
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 2 low, 1 info)

## Requirements

Checklist is the pinned `bookshop/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.go:57 createBook` → `repository.go:50 CreateBook`; `acceptance_test.go:82 CreateBookReturns201` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:39 listBooks` → `repository.go:67 GetAllBooks`; `acceptance_test.go:161 ListAllBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:40` reads `author` query; `repository.go:71-73` WHERE author=?; `acceptance_test.go:213 FilterBooksByAuthor` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.go:109 getBook`; 404 at `app.go:121`; `acceptance_test.go:258/294` get + 404 cases |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.go:125 updateBook` → `repository.go:108 UpdateBook`; `acceptance_test.go:305 UpdateBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.go:153 deleteBook` (204) → `repository.go:127 DeleteBook`; `acceptance_test.go:392 DeleteBook` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `repository.go:7` `mattn/go-sqlite3`; schema at `repository.go:36 initSchema` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/404/400/409/204 across `app.go`; JSON via `json.NewEncoder` |
| R9 | Validation: title and author required | ✓ implemented | `book.go:32 Validate`; enforced at `app.go:64`; `book_test.go` + `acceptance_test.go:111-158` |
| R10 | GET /health health check | ✓ implemented | `app.go:16 HealthCheck` returns `{"status":"ok"}`; `acceptance_test.go:62` |
| R11 | README.md with setup and run instructions | ✗ missing | no README.md in run_dir; `_agent_stdout.log` — write_file sandbox-blocked, file never written |
| R12 | At least 3 unit/integration tests | ✓ implemented | 33 test funcs across 3 files; test_coverage=0.759 (tests ran) |

**Prompt factor (ATDD) conformance:** The suite follows the ATDD prompt well — `acceptance_test.go` drives the service through its public HTTP contract (`router` + `httptest`), scenarios use domain language (create/list/filter/update/delete/reject), and each test starts from a fresh empty `:memory:` service (`newTestApp`, `acceptance_test.go:14`). Finer-grained unit TDD sits underneath (`book_test.go`, `repository_test.go`), as the prompt allows. "Tests fail first" is a process claim not verifiable from the final state.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate):

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0171, "test_coverage": 0.759,
              "defect_rate": 1.0, "maintainability": 0.894, "idiomatic": 0.88}
# defect_rate=1.0 -> build + tests succeeded; test_coverage=0.759 -> 33 tests ran, 75.9% coverage
```

```text
go test ./...  (per scorer)  -> PASS, 0 failures, 0 skips (grep t.Skip -> 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, 4 .go) | 379 |
| Files (excl. summary/) | 17 |
| Dependencies (direct) | 1 (`mattn/go-sqlite3`) |
| Tests total | 33 |
| Tests effective | 33 |
| Skip ratio | 0% |
| Line coverage | 75.9% |
| Tokens (in/out) | 66,497 / 58,152 (42 API calls) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [high] R11 — No README.md with setup/run instructions (write_file was sandbox-blocked; deliverable never produced)
2. [low] getBook compares against wrong error strings (`app.go:116`); dead branch, falls through to correct 404
3. [low] Duplicate-ISBN 409 detection relies on substring match of "UNIQUE" (`app.go:74`); brittle
4. [info] Duplicate-ISBN 409 handling is an enhancement beyond spec (`app.go:74`, `acceptance_test.go:490`)

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=go_prompt=ATDD/rep2
cat scores.json                               # mechanical scores (do not re-run toolchain)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # -> 0
ls README*                                    # -> no matches (R11 missing)
go test ./... -cover                          # optional: PASS, ~75.9% coverage
```
