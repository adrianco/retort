# Evaluation: rest-api-crud · agent=codex effort=low language=go model=gpt-6-astra prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown (stdlib `net/http`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 test functions (many table-driven subtests) passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `scores.json` (inline gate): test_coverage=0.73, defect_rate=1.0,
code_quality=0.9556, maintainability=0.9628, idiomatic=0.76, token_efficiency=0.0402.
`defect_rate=1.0` ⇒ build + tests succeeded; `test_coverage=0.73` is the measured
statement-coverage fraction (tests executed). No build/test/lint was re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:95,153` save(id=0) → INSERT, returns 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `main.go:93,191` list() → `SELECT ... ORDER BY id` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:194-197` `WHERE author = ?` when query has author |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `main.go:114,220` get() → 200/404 via `sql.ErrNoRows` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:117,162` save(id!=0) → UPDATE, 404 on 0 rows |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:118,233` delete() → 204/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:20,40-53` go-sqlite3, persistent file, `books` table |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:63-76` respond/fail; 201/200/204/400/404/405/500/503 |
| R9 | Validation: title and author required | ✓ implemented | `main.go:144-149` trim + empty check (400); CHECK at `main.go:49-50` |
| R10 | GET /health health-check | ✓ implemented | `main.go:79-90` PingContext → 200 `{"status":"ok"}` / 503 |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — setup, CGO note, run/build/test commands, API table |
| R12 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` — 5 Test functions, httptest-based |

## Build & Test

Not re-run per skill policy — stored scores used.

```text
scores.json
defect_rate=1.0  → build + tests passed
test_coverage=0.73  → tests executed; 73% statement coverage
code_quality=0.9556  lint/quality
```

Skipped/disabled tests: `grep t.Skip` → 0. All tests effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 443 (main.go 280 + main_test.go 163) |
| Files | 13 (incl. go.mod/go.sum/README/logs) |
| Dependencies | 1 direct (`github.com/mattn/go-sqlite3`) |
| Tests total | 5 functions (multiple table-driven subtests) |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All findings are info-level enhancements beyond spec — no deductions:

1. [info] Body hardening: MaxBytesReader(1MiB) + DisallowUnknownFields + trailing-JSON rejection (`main.go:130-138`)
2. [info] SQLite CHECK constraints mirror app-layer validation (`main.go:49-50`)
3. [info] Graceful shutdown + server timeouts (`main.go:260-279`)
4. [info] SQL-injection test coverage (`main_test.go:83`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6-astra_prompt=neutral/rep2"
cat scores.json
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
# optional re-run (not required): go test ./...
```
