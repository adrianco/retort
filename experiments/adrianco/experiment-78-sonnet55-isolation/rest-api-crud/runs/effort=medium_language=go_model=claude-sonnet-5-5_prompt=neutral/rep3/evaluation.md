# Evaluation: effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 test functions, all passing (0 skipped, 4 effective) — coverage 77.9%
- **Build:** pass (test_coverage=0.779 from scores.json ⇒ build + tests ran and passed)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:79 create` → `store.go:47 Store.Create` INSERT |
| R2 | GET /books lists all books | ✓ implemented | `main.go:92 list` → `store.go:57 Store.List` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `store.go:60` `WHERE author = ?`; test `main_test.go:85 TestListFilter` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `main.go:101 get` → `store.go:80` maps `ErrNoRows`→`errNotFound`→404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:114 update` → `store.go:90 Store.Update` (404 if 0 rows) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:131 delete` → `store.go:102 Store.Delete` (404 if 0 rows) |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:7,26` `modernc.org/sqlite`, `CREATE TABLE books` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:29 writeJSON`; 201/200/404/400/204 across handlers |
| R9 | Input validation: title & author required | ✓ implemented | `main.go:57-61` returns 400; test `main_test.go:71 TestValidation` |
| R10 | GET /health endpoint | ✓ implemented | `main.go:18` returns 200 `{"status":"ok"}`; test `TestHealth` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — run/test/env/endpoints documented |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test funcs in `main_test.go`; test_coverage=0.779 > 0 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.074, "test_coverage": 0.779,
              "defect_rate": 1.0, "maintainability": 0.858, "idiomatic": 0.9}
```

`test_coverage=0.779` ⇒ `go test ./...` built and passed with 77.9% coverage;
`defect_rate=1.0` ⇒ build+test succeeded. No skipped tests
(`grep t.Skip → 0`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, main.go+store.go) | 270 |
| Lines of code (incl. tests) | 371 |
| Files (source) | 3 (.go) |
| Dependencies (go.sum lines) | 50 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Coverage | 77.9% |

## Findings

Top items (full list in `findings.jsonl`) — none above `info`:

1. [info] Defensive request handling beyond spec (MaxBytesReader, Location header)
2. [info] Extra validation: negative year rejected
3. [info] PUT semantics are full-replace (documented in README)

## Reproduce

```bash
cd experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral/rep3
cat scores.json                         # mechanical scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" main_test.go      # 4 tests
# optional re-verify: go test ./... -cover
```
