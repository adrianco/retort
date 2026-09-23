# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 4

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (build+test gate)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `books.go:60-74` INSERT ... RETURNING id |
| R2 | GET /books lists all books | ✓ implemented | `books.go:75-102` |
| R3 | GET /books ?author= filter | ✓ implemented | `books.go:78-81` appends `WHERE author = ?`; tested `books_test.go:72-76` |
| R4 | GET /books/{id} single book | ✓ implemented | `books.go:117-127`; 404 via `sql.ErrNoRows` at :119 |
| R5 | PUT /books/{id} updates | ✓ implemented | `books.go:128-152`; 404 when RowsAffected==0 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `books.go:153-164`; 204 on success, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:17` file-backed `modernc.org/sqlite`; `books.go:24-33` schema |
| R8 | JSON responses + status codes | ✓ implemented | `books.go:202-210` writeJSON/writeError; 201/200/404/400/204/405 |
| R9 | Validation: title & author required | ✓ implemented | `books.go:177-185` validate(); tested `books_test.go:91-95` |
| R10 | GET /health endpoint | ✓ implemented | `books.go:40,46-52`; pings DB |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run, API, Verify sections |
| R12 | At least 3 tests | ✓ implemented | `books_test.go` — 3 passing `Test*` funcs; `test_coverage=0.595` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill, DB/scores are authoritative):

```text
scores.json: defect_rate=1.0 (build + tests passed), test_coverage=0.595,
             code_quality=1.0, maintainability=0.718, idiomatic=0.76
```

`defect_rate=1.0` ⇒ `go build ./...` and `go test ./...` succeeded; `test_coverage=0.595` ⇒ 59.5% statement coverage with all tests passing.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 341 (books.go 210, books_test.go 100, main.go 31) |
| Files | 5 source (go.mod, go.sum, main.go, books.go, books_test.go) |
| Dependencies | 1 direct (`modernc.org/sqlite`); 51 go.sum lines |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Coverage | 59.5% |

## Findings

Top items (full list in `findings.jsonl`) — all informational, no defects:

1. [info] Defensive request decoding beyond spec (MaxBytesReader, DisallowUnknownFields, single-object guard)
2. [info] Health check verifies DB connectivity via `db.Ping()`
3. [info] Coverage moderate at 59.5% — happy paths covered, error branches less so (R12 still satisfied)

## Reproduce

```bash
cd experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep4
cat scores.json                 # mechanical scores (build/test/lint), not re-run
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" books_test.go                            # 3 tests
# optional live check:
go test ./... && go build ./...
```
