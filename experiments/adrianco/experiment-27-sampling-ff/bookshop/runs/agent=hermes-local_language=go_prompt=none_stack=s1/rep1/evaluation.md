# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s1 · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown (Gin), prompt=none, stack=s1
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — defect_rate=1.0 from scores.json (build + tests succeeded)
- **Lint:** pass — code_quality=0.956 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores (from `scores.json`): test_coverage=0.558, code_quality=0.956, defect_rate=1.0, maintainability=0.955, idiomatic=0.58, token_efficiency=0.018. `test_coverage > 0` with `defect_rate=1.0` confirms the build compiled and all 11 tests ran and passed; 0.558 is the Go coverage fraction, not a pass rate.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:50 createBook` INSERT; `app_test.go:91 TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:79 listBooks`; `app_test.go:154 TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:85-86` WHERE author=?; `app_test.go:183 TestListBooksByAuthor` |
| R4 | GET /books/{id} single book (404) | ✓ implemented | `app.go:114 getBook` sql.ErrNoRows→404; `TestGetBook`/`TestGetBookNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:138 updateBook`; `app_test.go:266 TestUpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:179 deleteBook`; `TestDeleteBook`/`TestDeleteBookNotFound` |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:27 sql.Open("sqlite3",...)`, `go-sqlite3` driver; table DDL `app.go:32` |
| R8 | JSON responses + status codes | ✓ implemented | `c.JSON(...)` with 201/200/400/404/500 throughout `app.go` |
| R9 | Validation: title & author required | ✓ implemented | `app.go:57-64` (create), `152-159` (update); `TestCreateBookValidation` |
| R10 | GET /health endpoint | ✓ implemented | `app.go:203 healthCheck`; `app_test.go:68 TestHealthCheck` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Setup, Testing, API examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 11 `func Test*` in `app_test.go`; test_coverage=0.558 > 0 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run step 2).

```text
scores.json: defect_rate=1.0  ⇒ build + tests succeeded
test_coverage=0.558 (> 0)     ⇒ 11 tests executed and passed
code_quality=0.956            ⇒ lint/quality clean
```

Agent stdout (`_agent_stdout.log`) reports "Build compiles cleanly, all 11 tests pass". (Note: the log also contains a file-mutation verifier warning about a sandbox path-refusal, but the files are present and scored, so the writes ultimately succeeded via terminal.)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 226 (app.go) + 368 (app_test.go) = 594 |
| Files | 2 Go source files (+ README, go.mod/go.sum) |
| Dependencies | 2 direct (gin v1.10.0, go-sqlite3 v1.14.24); 91 go.sum lines |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all minor, none block conformance:

1. [low] Health check is static and does not verify DB connectivity (`app.go:203`)
2. [info] GET /books has no pagination (`app.go:79`)
3. [info] SQLite path hardcoded to `./books.db` (`app.go:27`)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s1/rep1
cat scores.json                          # mechanical scores (build/test/lint) — do not re-run
grep -cE "^func Test" app_test.go        # 11
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
# Optional live rebuild (not required — scores already stored):
# go test -v ./...
```
