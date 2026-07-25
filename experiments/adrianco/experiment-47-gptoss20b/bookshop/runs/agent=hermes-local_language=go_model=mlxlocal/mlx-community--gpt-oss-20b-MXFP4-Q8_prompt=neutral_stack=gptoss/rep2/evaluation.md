# Evaluation: go · gpt-oss-20b-MXFP4-Q8 · neutral · rep 2

## Summary

- **Factors:** language=go, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `defect_rate=1.0` (retort.db/scores.json)
- **Lint:** pass — `code_quality=0.956` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:70 handleCreate` — decodes body, INSERTs, 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:93 handleList` — returns `[]Book` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:97-101` — `WHERE author = ?` branch |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:121 handleGet` — 404 on `sql.ErrNoRows` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:139 handleUpdate` — UPDATE, 404 if 0 rows |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:167 handleDelete` — DELETE, 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:11,30 mattn/go-sqlite3`, `initDB` CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204 set; JSON on success (errors are text — see finding) |
| R9 | Validation: title+author required | ✓ implemented | `main.go:76,147` — 400 if either empty |
| R10 | GET /health | ✓ implemented | `main.go:184 handleHealth` — `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, endpoint table, test instructions |
| R12 | ≥3 tests | ✓ implemented | `book_test.go` — 4 `Test*` funcs, `test_coverage=0.596` (>0, passed) |

No partial or missing requirements. All routes exercised by tests except the
error branches (see coverage finding).

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
defect_rate    = 1.0    → build + tests succeeded
test_coverage  = 0.596  → tests executed and passed (59.6% coverage)
code_quality   = 0.956
maintainability= 0.967
idiomatic      = 0.52
```

Test functions (`grep '^func Test' book_test.go`): TestCreateAndGetBook,
TestListFilter, TestUpdateAndDelete, TestHealth. Skip scan
(`grep 't.Skip'`): 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go) | 187 |
| Lines of code (book_test.go) | 180 |
| Files (excl .git) | 14 |
| Dependencies (go.sum entries) | 4 (2 direct: gorilla/mux, go-sqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Coverage | 59.6% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Error responses are plain text, not JSON (`main.go:73,77,82` use `http.Error`)
2. [info] `Year`/`ISBN` use `omitempty`, hiding zero/empty values (`main.go:20-21`)
3. [info] Coverage 59.6% — 400/404/malformed-JSON error branches untested

## Reproduce

```bash
cd "runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep2"
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rE 't\.Skip\(|t\.Skipf\(' . --include='*.go' | wc -l   # 0 skips
grep -E '^func Test' book_test.go                 # 4 tests
# build/test NOT re-run — defect_rate=1.0 from scores.json is the build+test signal
```
