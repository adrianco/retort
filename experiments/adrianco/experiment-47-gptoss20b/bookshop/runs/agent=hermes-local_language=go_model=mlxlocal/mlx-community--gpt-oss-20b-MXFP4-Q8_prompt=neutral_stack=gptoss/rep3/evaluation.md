# Evaluation: go · gpt-oss-20b-MXFP4-Q8 · neutral · rep 3

## Summary

- **Factors:** language=go, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok (repair task — previous attempt's gaps, missing README + non-passing tests, are now fixed)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (`defect_rate=1.0` from scores.json — build+test succeeded)
- **Lint:** pass (`code_quality=1.0` from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `router.go:42 createBookHandler` — decodes 4 fields, INSERTs, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `router.go:65 listBooksHandler` — SELECT all |
| R3 | GET /books ?author= filter | ✓ implemented | `router.go:70` — `WHERE author = ?` when query param set |
| R4 | GET /books/{id} by id | ✓ implemented | `router.go:92 getBookHandler` — 404 on Scan error (`:103`) |
| R5 | PUT /books/{id} update | ✓ implemented | `router.go:110 updateBookHandler` — UPDATE, 404 if RowsAffected==0 |
| R6 | DELETE /books/{id} | ✓ implemented | `router.go:141 deleteBookHandler` — DELETE, 204/404 |
| R7 | SQLite persistence | ✓ implemented | `db.go:7,22` — `mattn/go-sqlite3`, `sql.Open("sqlite3", ...)`, CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | `router.go` — Content-Type application/json, 201/200/204/400/404 |
| R9 | Validation: title+author required | ✓ implemented | `router.go:48,122` — TrimSpace empty check → 400 |
| R10 | GET /health | ✓ implemented | `router.go:25,37 healthHandler` — `{"status":"ok"}` |
| R11 | README.md | ✓ implemented | `README.md` — setup, endpoints, testing sections present |
| R12 | ≥3 tests | ✓ implemented | `router_test.go` — TestHealth, TestCRUD, TestListByAuthor (test_coverage=0.678>0) |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.678   # tests executed and passed; Go statement coverage
defect_rate   = 1.0     # build + test succeeded
code_quality  = 1.0     # lint clean
```

Agent stdout confirms: `go test ./...` → `ok bookapi 0.366s`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 331 (db.go 49, main.go 15, router.go 160, router_test.go 107) |
| Files | 14 (incl. artifacts) |
| Dependencies | 2 (go-chi/chi/v5, mattn/go-sqlite3) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Token efficiency | 0.013 (440k total tokens, 26 API calls) |

## Findings

Full list in `findings.jsonl`:

1. [low] Tests share a process-global SQLite singleton; pass depends on test order + cleanup (`db.go:12`, `router_test.go:76,105`)
2. [info] Idiomatic score 0.58 — errors written as plain text rather than JSON bodies (`scores.json`)

## Reproduce

```bash
cd "runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep3"
cat scores.json            # stored build/test/lint scores (do not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
wc -l *.go                 # LOC
# optional live check: go test ./...
```
