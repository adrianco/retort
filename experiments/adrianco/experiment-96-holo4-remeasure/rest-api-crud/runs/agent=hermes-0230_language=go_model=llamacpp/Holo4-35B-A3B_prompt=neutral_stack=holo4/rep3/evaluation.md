# Evaluation: rest-api-crud · agent=hermes-0230 language=go model=llamacpp/Holo4-35B-A3B prompt=neutral stack=holo4 · rep 3

## Summary

- **Factors:** language=go, agent=hermes-0230, model=llamacpp/Holo4-35B-A3B, prompt=neutral, stack=holo4
- **Task type:** REPAIR (a prior attempt failed eval — missing README + build/tests not fully passing; this run was asked to fix in place)
- **Status:** ok — build + tests passed, all 12 pinned requirements implemented
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass (inferred — `test_coverage=0.621` from scores.json; coverage is only parseable when the build+tests run)
- **Lint:** `go vet` surfaced 9 diagnostics (all the same go-version mismatch) — `defect_rate=0.6484` from scores.json
- **Coverage:** 62.1% statement coverage (`test_coverage=0.621`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 1 info)

The agent's `_agent_stdout.log` claim ("all 5 tests pass, every requirement met") is
corroborated by the stored scores: `test_coverage=0.621 > 0` (tests executed and
passed), and every requirement has concrete code + test evidence below. The repair
fixed the prior run's two complaints: the README now exists, and the suite builds and
passes.

## Requirements

Source: pinned `REQUIREMENTS.json` (12 items, fixed denominator for all runs of this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `handlers.go:createBook` decodes all 4 fields → `database.go:CreateBook`; `main_test.go:TestCreateBook` asserts 201 + body |
| R2 | GET /books lists all | ✓ implemented | `handlers.go:listBooks` → `database.go:ListBooks("")`; `TestListBooks` asserts 3 rows |
| R3 | GET /books ?author= filter | ✓ implemented | `listBooks` reads `Query().Get("author")`; `ListBooks` `WHERE author=?`; `TestListBooks` asserts 2 filtered |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `handlers.go:getBook`; `GetBook` maps `sql.ErrNoRows→ErrNotFound→404`; `TestGetBook` asserts 200 and 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:updateBook` → `database.go:UpdateBook`; `TestUpdateBook` asserts updated fields |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:deleteBook` → `DeleteBook` (204); `TestDeleteBook` asserts 204 then 404 |
| R7 | Data stored in SQLite | ✓ implemented | `database.go` uses `mattn/go-sqlite3`, `sql.Open("sqlite3", ...)`, `CREATE TABLE books` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `handlers.go:jsonResponse` sets `Content-Type: application/json`; 201/200/204/400/404/500 used |
| R9 | Validation: title + author required | ✓ implemented | `handlers.go:validateCreateBook` → 400; `TestCreateBook` asserts 400 on missing title |
| R10 | GET /health | ✓ implemented | `main.go` `/health` handler returns `{"status":"ok"}` 200 (not covered by a test — see finding) |
| R11 | README.md with setup/run | ✓ implemented | `README.md` documents setup, `go run .`, `-addr`, build, `go test` (this is what the prior run lacked) |
| R12 | ≥ 3 tests that run | ✓ implemented | 5 `Test*` funcs in `main_test.go`; `test_coverage=0.621 > 0` ⇒ they executed |

No requirement is missing or partial. Enhancements beyond spec: graceful shutdown,
WAL mode, `created_at`/`updated_at` timestamps.

## Build & Test

Not re-run — stored scores from `scores.json` are authoritative (skill step 2):

```text
scores.json: {"code_quality": 0.85, "token_efficiency": 0.0634, "test_coverage": 0.621,
              "defect_rate": 0.6484, "maintainability": 0.8255, "idiomatic": 0.7}
```

- `test_coverage=0.621` → `go test -cover ./...` ran and parsed 62.1% coverage ⇒ build OK, all tests passed.
- `defect_rate=0.6484` → `go vet ./...` emitted 9 diagnostics. Reproduced in a scratchpad copy:

```text
main_test.go:24:18: httptest.NewRequestWithContext requires go1.23 or later (module is go1.21)
  ... (9 identical diagnostics at lines 24,41,64,79,105,120,140,166,174)
```

  9 defects / 512 LOC × 1000 = 17.58/kloc ⇒ `1 − 17.58/50 = 0.6484` (exactly matches scores.json).
  The suite only builds/passes because the eval toolchain is ≥ go1.23; on the **declared**
  `go 1.21` the test file would not compile. See finding `defect-go-version`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (non-test source) | 354 |
| Lines of code (tests) | 158 |
| Files (source + go.mod/sum + README) | 9 |
| Dependencies (go.sum entries) | 1 (`mattn/go-sqlite3`) |
| Tests total | 5 |
| Tests effective (passed+failed) | 5 |
| Tests skipped | 0 |
| Skip ratio | 0% |
| Statement coverage | 62.1% |
| `go vet` diagnostics | 9 (all the go1.21/1.23 mismatch) |

## Findings

Full list in `findings.jsonl` (3 items; none critical/high):

1. [medium] `defect-go-version` — `go.mod` declares `go 1.21` but tests call `httptest.NewRequestWithContext` (go1.23+); `go vet` flags 9 sites and the code would not compile on the declared minimum version. This is the sole driver of `defect_rate`.
2. [low] `isbn-unique-empty` — `isbn` is `NOT NULL UNIQUE` but optional per spec; a duplicate/empty ISBN surfaces as a 500 rather than a 4xx (`database.go` migrate + `handlers.go:handleError`).
3. [info] `health-untested` — `GET /health` is implemented (R10) but has no test; contributes to the 62.1% (not 100%) coverage.

## Reproduce

```bash
cd "<run_dir>"
cat scores.json                      # authoritative stored scores (do not re-run build/test)
# go vet reproduction (in a COPY, never in run_dir):
cp *.go go.mod go.sum /tmp/gocopy/ && cd /tmp/gocopy
GOFLAGS=-mod=mod go vet ./...        # 9 "requires go1.23 or later (module is go1.21)" diagnostics
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" main_test.go   # 5 tests
```
