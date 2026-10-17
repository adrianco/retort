# Evaluation: rest-api-crud · effort=max · go · claude-haiku-5-5 · neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=max, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 25 passed / 0 failed / 0 skipped (25 effective)
- **Build:** pass — `test_coverage=0.807` from `scores.json` (build + tests ran; 0.807 is coverage, not pass-rate)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

A textbook-clean run. Four idiomatic Go files (637 non-test LOC) implement the
full spec with the standard library's `net/http` router and a pure-Go SQLite
backend, exercised by 25 tests with no skips. Stored scores: `test_coverage=0.807`,
`code_quality=1.0`, `defect_rate=1.0`, `idiomatic=0.9`, `maintainability=0.84`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:102 createBook`, 201 + Location; `store.go:63 Create` |
| R2 | GET /books lists all | ✓ implemented | `server.go:91 listBooks`; `store.go:93 List` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:92`; `store.go:96-98 LIKE ... ESCAPE` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `server.go:117 getBook`; `store.go:80 Get`→`ErrNotFound`→404 `server.go:164` |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.go:132 updateBook`; `store.go:124 Update` (full replace) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `server.go:150 deleteBook`→204; `store.go:139 Delete` |
| R7 | SQLite / embedded DB | ✓ implemented | `store.go:10 modernc.org/sqlite`; `store.go:17 CREATE TABLE books` |
| R8 | JSON + correct status codes | ✓ implemented | `server.go:293 writeJSON`; 201/200/204/400/404/413/500 throughout |
| R9 | title & author required | ✓ implemented | `book.go:54-64 validate` → 400 `server.go:280` |
| R10 | GET /health | ✓ implemented | `server.go:71 handleHealth` pings DB → 200/503 |
| R11 | README with setup/run | ✓ implemented | `README.md` — requirements, setup, run, flags, endpoint table, curl examples |
| R12 | ≥3 tests | ✓ implemented | 25 test funcs across `server_test.go`, `store_test.go`, `book_test.go` |

Enhancements beyond spec (not deductions): ISBN format validation, request
size caps, graceful shutdown + server timeouts, WAL/busy_timeout, literal LIKE
escaping. See findings E1–E3.

## Build & Test

Build/test not re-run — stored scores used per skill policy.

```text
scores.json
test_coverage=0.807  (build + tests executed; value is coverage fraction, >0 ⇒ gate passed)
code_quality=1.0  defect_rate=1.0  idiomatic=0.9  maintainability=0.839  token_efficiency=0.0067
```

```text
go test ./...  (not re-run)
25 test functions, 0 t.Skip, 0 failures implied by defect_rate=1.0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test) | 637 |
| Lines of code (incl. tests) | 1543 |
| Files (excl. .git) | 18 |
| Dependencies (go.sum lines) | 50 |
| Tests total | 25 |
| Tests effective | 25 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All four are informational (no action required):

1. [info] E1 — ISBN format validation beyond spec
2. [info] E2 — Production hardening (timeouts, body caps, graceful shutdown, WAL)
3. [info] E3 — LIKE wildcards escaped in author filter
4. [info] D1 — No pagination on GET /books (documented limitation, not required)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=max_language=go_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json
grep -rhE "^func (Test|Benchmark|Fuzz)" *_test.go | wc -l   # 25
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0
# optional: go test ./...
```
