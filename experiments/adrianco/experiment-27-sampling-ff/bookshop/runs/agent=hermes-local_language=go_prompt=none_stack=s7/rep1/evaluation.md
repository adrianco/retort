# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s7 · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=none, stack=s7
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective) — per `_agent_stdout.log` "16/16 PASS"
- **Build:** pass (test_coverage=0.685, defect_rate=1.0 from scores.json — tests executed & passed)
- **Lint:** pass — code_quality=0.9556, maintainability=0.9993 from scores.json
- **Architecture:** `run-summary` skill unavailable; single-file layout (app.go) — BookStore (SQLite CRUD) + Server (net/http handlers)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:248 createBook`, tested `app_test.go:83 TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:281 listBooks` / `app.go:103 ListBooks`, `app_test.go:206 TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:282` reads query, `app.go:107` WHERE author, `app_test.go:236 TestListBooksByAuthor` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.go:298 getBook` → 404 on miss, `app_test.go:163/194` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.go:309 updateBook`, `app_test.go:271 TestUpdateBook` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `app.go:342 deleteBook`, `app_test.go:319 TestDeleteBook` |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:31 sql.Open("sqlite3")`, `app.go:45 initializeDB` creates books table |
| R8 | JSON + appropriate status codes | ✓ implemented | `app.go:193 writeJSON`; 201/200/404/400/204 used across handlers |
| R9 | Validate title & author required | ✓ implemented | `app.go:262-269` (create), `app.go:323-330` (update), `app_test.go:127 TestCreateBookValidation` |
| R10 | GET /health endpoint | ✓ implemented | `app.go:205 healthHandler` returns `{"status":"ok"}`, `app_test.go:57 TestHealthEndpoint` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (3062 bytes) documents endpoints, setup & run |
| R12 | At least 3 tests | ✓ implemented | 15 `func Test*` + table subtests; test_coverage=0.685 > 0 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline eval gate):

```text
scores.json: test_coverage=0.685, defect_rate=1.0, code_quality=0.9556,
             maintainability=0.9993, idiomatic=0.75, token_efficiency=0.0209
_agent_stdout.log: "Test results: 16/16 PASS"
```

`defect_rate=1.0` and non-zero coverage ⇒ build succeeded and all tests passed. 0 skipped tests (`grep t.Skip` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 818 (app.go 371 + app_test.go 447) |
| Files | 13 (incl. logs/meta) |
| Dependencies | 1 (github.com/mattn/go-sqlite3) |
| Tests total | 16 (15 top-level funcs + subtests) |
| Tests effective | 16 |
| Skip ratio | 0% |
| Test coverage | 0.685 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] README claims Gin framework but code uses stdlib net/http — `README.md:3` vs `app.go:8`
2. [low] Handlers registered on global http.DefaultServeMux — `app.go:183-185`
3. [info] Test coverage exceeds the 3-test minimum with edge cases — `app_test.go`

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s7/rep1
cat scores.json                                  # mechanical scores (do not re-run toolchain)
grep -rEn "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
# optional: go test ./...   (already scored: 16/16 pass)
```
