# Evaluation: agent=codex effort=xhigh language=go model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-5.6-terra, agent=codex, effort=xhigh, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective), coverage 60.7%
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** run-summary skill unavailable; single-package `main` — `main.go` (wiring) + `server.go` (router/handlers/DB) + `server_test.go`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Using the pinned `bookshop/REQUIREMENTS.json` checklist (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.go:111` createBook INSERT; test `TestCreateAndGetBook` |
| R2 | GET /books lists all books | ✓ implemented | `server.go:133` listBooks SELECT |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:137` adds `WHERE author = ?`; test `TestListBooksFiltersByAuthor` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `server.go:166` getBook; `sql.ErrNoRows`→404 `server.go:168` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:179` updateBook UPDATE; test `TestUpdateThenDeleteBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:206` deleteBook DELETE→204; same test |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:9,18` mattn/go-sqlite3; `server.go:34` CREATE TABLE books |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `writeJSON` `server.go:260`; 201/200/204/400/404/405/503 across handlers |
| R9 | Validation: title and author required | ✓ implemented | `server.go:248-253`; test `TestBookValidationAndHealth` asserts 400 "author is required" |
| R10 | GET /health | ✓ implemented | `server.go:68` health pings DB; test `TestBookValidationAndHealth` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Run, API table, Test and build sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 5 tests in `server_test.go`; coverage 60.7% > 0 |

Enhancements beyond spec (not deductions): unknown-JSON-field rejection (`DisallowUnknownFields`, `server.go:235`), 1 MiB request-body limit (`server.go:234`), `Allow` header on 405 (`server.go:271`), trailing-slash normalization (`server.go:51`), year range validation.

## Build & Test

Not re-run — stored scores are authoritative (per evaluate-run skill).

```text
scores.json: defect_rate=1.0 (build + tests pass), test_coverage=0.607 (go coverage), code_quality=1.0
```

```text
go test ./...   # 5 tests, 0 skips (grep t.Skip -> 0)
TestCreateAndGetBook, TestListBooksFiltersByAuthor, TestUpdateThenDeleteBook,
TestBookValidationAndHealth, TestUnknownJSONFieldIsRejected
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, source only) | 311 (main.go 38 + server.go 273) |
| Test LOC | 149 |
| Files | 8 (3 .go, go.mod, go.sum, README.md, TASK.md, stack.json) |
| Dependencies | 1 direct (mattn/go-sqlite3) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Coverage | 60.7% |

## Findings

Top items (full list in `findings.jsonl`):

1. [info] GET /books has no pagination (enhancement, not required)
2. [info] PUT uses full-replace semantics — all fields required on update
3. [info] run-summary skill not invoked (architecture summary omitted)

No critical/high/medium/low findings — the run fully implements the spec with passing tests and clean lint.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=xhigh_language=go_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
# (optional, re-run tests) go test ./...
```
