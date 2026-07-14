# Evaluation: agent=hermes-local language=go prompt=none stack=s6 · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local, prompt=none, stack=s6, framework=Gin (from source)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — 56.6% statement coverage
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.956 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Clean, fully-conformant run. Every pinned requirement is implemented and exercised
by a test. Build and tests pass (`defect_rate=1.0`, `test_coverage=0.566`). No
skipped or disabled tests. The only observations are cosmetic (low idiomatic
score, hardcoded DB path, shared test globals) — none are defects.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:62 createBook`, route `app.go:234`; test `app_test.go:62` |
| R2 | GET /books lists all | ✓ implemented | `app.go:97 listBooks` (else branch `:106`); test `app_test.go:134` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:103-104` WHERE author=?; test `app_test.go:166` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.go:131 getBook`, 404 at `:143`; tests `app_test.go:198,227` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:154 updateBook`, 404 at `:186`; test `app_test.go:247` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:201 deleteBook`, 404 at `:217`; tests `app_test.go:280,309` |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:36` sql.Open("sqlite3"), table `:41`; driver go-sqlite3 |
| R8 | JSON responses + correct status codes | ✓ implemented | `c.JSON(...)` throughout with 201/200/400/404/500 |
| R9 | Validation: title & author required | ✓ implemented | `app.go:69-76` (create), `:168-175` (update); tests `app_test.go:94,114` |
| R10 | GET /health | ✓ implemented | `app.go:58 healthHandler`, route `:232`; test `app_test.go:43` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — deps, `go run`, curl examples, testing |
| R12 | >= 3 unit/integration tests | ✓ implemented | 12 Test funcs in `app_test.go`; test_coverage=0.566 (>0) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline eval gate):

```text
defect_rate    = 1.0    → build + tests passed
test_coverage  = 0.566  → tests executed; 56.6% statement coverage
code_quality   = 0.956
maintainability= 0.947
idiomatic      = 0.380
```

Skip scan (`grep -rE 't\.Skip'`): 0 skipped tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.go) | 244 |
| Lines of code (app_test.go) | 343 |
| Files (source) | 4 (app.go, app_test.go, go.mod, go.sum) |
| Direct dependencies | 2 (gin-gonic/gin, mattn/go-sqlite3) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Statement coverage | 56.6% |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] SQLite path hardcoded to `./books.db` — `app.go:36`
2. [low] Tests mutate the shared package-global `db` — `app_test.go:18`
3. [info] Idiomatic score low (0.38) despite clean build
4. [info] 12 tests, well beyond the ≥3 required

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s6/rep3
cat scores.json                                   # mechanical scores (no re-run)
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"
grep -rEc "^func Test" app_test.go
# to re-verify manually: go test -v -cover ./...
```
