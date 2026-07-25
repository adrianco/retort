# Evaluation: gpt-oss-20b · go · hermes-local · rep 3 (REPAIR task)

## Summary

- **Factors:** language=go, model=mlx-community/gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok — repair succeeded; the missing README.md was added and tests pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Coverage:** test_coverage=0.678 (67.8%) from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 1 info)

This is a repair run: FEEDBACK.md flagged the prior attempt as failed for a missing
README.md (requirement_coverage 0.83) and tests not fully passing. Both are now fixed —
`README.md` (32 lines, setup + endpoints + testing) exists, and a third test
(`TestListByAuthor`) was added, giving all 12 requirements met with a passing suite.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `router.go:createBookHandler` INSERTs all four fields, 201 |
| R2 | GET /books lists all | ✓ implemented | `router.go:listBooksHandler` SELECTs collection |
| R3 | ?author= filter | ✓ implemented | `router.go:69` `WHERE author = ?` branch |
| R4 | GET /books/{id} single (404) | ✓ implemented | `router.go:getBookHandler` 404 on scan error |
| R5 | PUT /books/{id} update | ✓ implemented | `router.go:updateBookHandler` UPDATE + 404 on 0 rows |
| R6 | DELETE /books/{id} | ✓ implemented | `router.go:deleteBookHandler` DELETE + 204/404 |
| R7 | SQLite / embedded DB | ✓ implemented | `db.go` uses `mattn/go-sqlite3`, persistent `books` table |
| R8 | JSON + status codes | ✓ implemented | handlers set `Content-Type: application/json`, 201/200/400/404/204 |
| R9 | title & author required | ✓ implemented | `router.go:47,118` TrimSpace check → 400 |
| R10 | GET /health | ✓ implemented | `router.go:healthHandler` returns `{"status":"ok"}` |
| R11 | README.md | ✓ implemented | `README.md` — setup, endpoints, testing (was the prior failure) |
| R12 | ≥3 tests | ✓ implemented | `TestHealth`, `TestCRUD`, `TestListByAuthor` — 3 tests, 0 skips |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill step 2):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 0.678, "defect_rate": 1.0,
              "maintainability": 0.862, "idiomatic": 0.58, "token_efficiency": 0.013}
defect_rate=1.0  ⇒ build + `go test ./...` succeeded
agent stdout:    ok bookapi 0.366s
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, incl. tests) | 331 |
| README lines | 32 |
| Source/deliverable files | 7 (main/router/db/test .go, go.mod, go.sum, README) |
| Dependencies | chi/v5, mattn/go-sqlite3 (2 direct) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Coverage | 67.8% |

## Findings

Top items (full list in `findings.jsonl`):

1. [medium] Tests share one global in-memory DB with no per-test reset — `TestCRUD`'s `len(list)==1` assertion is order-dependent (`router_test.go:15`, `db.go:12`).
2. [low] `initDB` calls `log.Fatalf` on DB errors, killing the process instead of returning an error (`db.go:23,36`).
3. [info] `Year`/`ISBN` use `omitempty`, dropping zero values from JSON responses (`router.go:16-17`).

No critical or high findings — the repair is complete and the suite passes.

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep3
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rE "t\.Skip\(" . --include="*.go" | wc -l   # 0 skips
grep -rE "^func Test" *.go                         # 3 tests
go test ./...                                       # optional live check
```
