# Evaluation: rest-api-crud · effort=default language=go model=claude-fable-5-1 prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-fable-5-1, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all pass (6 test functions, ~28 subtests) / 0 failed / 0 skipped
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores read from `scores.json` (no re-run): `test_coverage=0.786`, `code_quality=1.0`,
`defect_rate=1.0`, `maintainability=0.875`, `idiomatic=0.9`, `token_efficiency=0.091`.
`defect_rate=1.0` ⇒ build + tests passed; `test_coverage>0` confirms the suite executed.

## Requirements

Checklist from pinned `REQUIREMENTS.json` (12 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:69 createBook` → `store.go:61 Create`; test `main_test.go:70` (201 + Location) |
| R2 | GET /books lists all | ✓ implemented | `handlers.go:83 listBooks` → `store.go:74 List`; test `main_test.go:126` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:77 WHERE author = ? COLLATE NOCASE`; test `main_test.go:131` (incl. case-insensitive) |
| R4 | GET /books/{id} single (404) | ✓ implemented | `handlers.go:92 getBook`, `storeError`→404; tests `main_test.go:82,206` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:105 updateBook` → `store.go:113 Update`; test `main_test.go:89` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:122 deleteBook` (204) → `store.go:124 Delete`; test `main_test.go:101` |
| R7 | SQLite / embedded DB | ✓ implemented | `store.go:8 modernc.org/sqlite`, file-backed; test `main_test.go:228` reopens the file |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON` sets `application/json`; 201/200/404/400/422/204/413 used across handlers |
| R9 | Validation: title+author required | ✓ implemented | `handlers.go:43 validate()` rejects blank title/author; test `main_test.go:157-159`. Returns 422 (see finding) |
| R10 | GET /health | ✓ implemented | `handlers.go:61 health` (200/503); test `main_test.go:56` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, env vars, API table, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 test functions in `main_test.go`; `test_coverage=0.786` |

Beyond spec: 1 MiB body cap + `DisallowUnknownFields`, single-object body enforcement,
`405` for wrong methods (free from method-pattern routing), `Location` header on create,
single-connection pool for `:memory:`/write consistency.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: defect_rate=1.0  → build + tests passed
scores.json: test_coverage=0.786  → test suite executed, high pass/coverage
scores.json: code_quality=1.0  → lint/quality clean
skips: grep t.Skip/t.Skipf → 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 371 (main.go 34, handlers.go 197, store.go 141 — approx) |
| Lines of test code | 253 |
| Files (excl. .git) | 15 (4 .go + go.mod/go.sum + README + task/meta/logs) |
| Dependencies (go.sum lines) | 50 (1 direct: modernc.org/sqlite; rest indirect) |
| Tests total | 6 functions (~28 subtests) |
| Tests effective | 6 / ~28 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] R9 — validation failures return `422` where the spec example suggests `400` (defensible; noted only)
2. [info] Request hardening beyond spec (body cap, unknown-field rejection, single-conn pool)
3. [info] File-persistence test reopens the SQLite DB, verifying durable R7 storage

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=go_model=claude-fable-5-1_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/lint scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
grep -rE "^func Test" *.go                        # test functions
# Optional full re-run (not required — scores.json already has results):
# go test ./...
```
