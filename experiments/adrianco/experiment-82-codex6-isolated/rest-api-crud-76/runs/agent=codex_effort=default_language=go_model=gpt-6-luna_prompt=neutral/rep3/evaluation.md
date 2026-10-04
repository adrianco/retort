# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — defect_rate=1.0 from scores.json (build + tests succeeded)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Mechanical scores read from `scores.json` (no re-run): test_coverage=0.596,
defect_rate=1.0, code_quality=0.9556, maintainability=0.9128, idiomatic=0.78,
token_efficiency=0.0227. `test_coverage > 0` confirms tests executed and passed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:55` createBook → INSERT, 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:77` listBooks → SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:80` WHERE author = ?; test at `main_test.go:65` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:106` getBook; `main.go:113` 404 on ErrNoRows |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:123` updateBook → UPDATE; 404 if RowsAffected==0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:156` deleteBook → DELETE; 204 / 404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:15,232` modernc.org/sqlite; `main.go:29` books table |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `main.go:218` writeJSON; 201/200/204/400/404/500 across handlers |
| R9 | Input validation: title & author required | ✓ implemented | `main.go:191` validateBook → 400; test at `main_test.go:56` |
| R10 | GET /health endpoint | ✓ implemented | `main.go:44` returns `{"status":"ok"}` 200; test `main_test.go:93` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — Run, Endpoints, Tests sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` — 3 Test funcs, all httptest integration tests |

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: defect_rate=1.0  → go build + go test ./... succeeded
scores.json: test_coverage=0.596  → tests executed (non-zero pass signal)
grep '^func Test' main_test.go → 3 test functions, 0 t.Skip() calls
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 347 (main.go 250 + main_test.go 97) |
| Files | 12 (incl. go.mod/go.sum/README/_agent logs) |
| Dependencies | 1 direct (modernc.org/sqlite), 9 indirect |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — none at or above medium severity:

1. [low] PUT /books/{id} is a full replace, not a partial update (`main.go:123`) — acceptable CRUD replace semantics, documented in README.
2. [info] Strict request decoding beyond spec — DisallowUnknownFields + 1 MiB cap (`main.go:200`).
3. [info] isbn has no uniqueness constraint (`main.go:29`) — not required by spec.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                                   # mechanical scores (no re-run)
grep -E '^func Test' main_test.go                 # 3 tests
grep -rE 't\.Skip\(|t\.Skipf\(' . --include='*.go'  # 0 skips
# Optional full re-run: go test ./...
```
