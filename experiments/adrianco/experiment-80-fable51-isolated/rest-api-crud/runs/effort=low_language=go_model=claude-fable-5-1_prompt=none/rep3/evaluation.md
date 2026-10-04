# Evaluation: effort=low language=go model=claude-fable-5-1 prompt=none · rep 3

## Summary

- **Factors:** language=go, model=claude-fable-5-1, effort=low, prompt=none, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective); coverage 74.2%
- **Build:** pass — `defect_rate=1.0` from `scores.json`
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (inline gate output); build/tests NOT re-run per skill guidance.
`test_coverage=0.742`, `defect_rate=1.0` (build+tests succeeded), `code_quality=0.9556`,
`maintainability=0.9952`, `idiomatic=0.7`, `token_efficiency=0.0917`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:117 createBook` INSERTs 4 fields; `TestCreateAndGetBook` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:134 listBooks`; `TestListWithAuthorFilter` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:137` adds `WHERE author = ?`; filter asserted in `TestListWithAuthorFilter` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:164 getBook`, 404 on `sql.ErrNoRows`; `TestCreateAndGetBook` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:184 updateBook`, 404 when `RowsAffected==0`; `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:208 deleteBook`, 204/404; `TestDeleteBook` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:29 OpenDB` uses `modernc.org/sqlite`, real `books` table |
| R8 | JSON responses + status codes | ✓ implemented | `main.go:66 writeJSON`; 201/200/204/400/404/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `main.go:89-96 decodeBook` rejects empty (trimmed); `TestCreateValidation` |
| R10 | GET /health health check | ✓ implemented | `main.go:109 health` pings DB, returns `{"status":"ok"}`; `TestHealth` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Setup/Run/Test/Endpoints sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 `Test*` funcs in `main_test.go`; `test_coverage=0.742>0` |

No prompt factor (`prompt=none`) — no `P*` requirements.

## Build & Test

```text
# Not re-run — scores read from scores.json (inline eval gate).
defect_rate = 1.0   -> go build + go test ./... succeeded
test_coverage = 0.742 (74.2% statement coverage)
```

```text
main_test.go: 6 test functions, 0 skipped
TestHealth, TestCreateAndGetBook, TestCreateValidation,
TestListWithAuthorFilter, TestUpdateBook, TestDeleteBook
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 242 (main.go) + 142 (main_test.go) = 384 |
| Files | 12 (incl. go.mod/go.sum, README) |
| Dependencies | 1 direct (`modernc.org/sqlite`); 50 go.sum lines |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] Request body capped with `MaxBytesReader` (beyond spec) — `main.go:82`
2. [info] `Location` header returned on create (beyond spec) — `main.go:130`
3. [info] PUT is a full replace, not partial update — `main.go:193` (spec-conformant)

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=go_model=claude-fable-5-1_prompt=none/rep3"
cat scores.json                                   # stored mechanical scores
grep -cE "^func Test" main_test.go                # test count (6)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skips (0)
# Optional full re-run (not required — scores cached):
# go test -cover ./...
```
