# Evaluation: agent=hermes-local language=go prompt=none stack=s5 · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=none, stack=s5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 test functions (all pass, incl. 2 validation subtests) / 0 failed / 0 skipped (9 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=1.0` (scores.json), 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Scores read from `scores.json` (inline gate, not re-run): `test_coverage=0.658`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.847`, `idiomatic=0.58`, `token_efficiency=0.0154`. `test_coverage>0` ⇒ build succeeded and all tests executed and passed; the 0.658 is line coverage, not a pass-rate deficit.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:29 CreateBook`, route `main.go:33`, `models.go:75 Create` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:61 ListBooks`, `models.go:97 GetAll` |
| R3 | GET /books ?author= filter | ✓ implemented | `handlers.go:62` reads `author`; `models.go:101-104` WHERE author=? |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `handlers.go:78 GetBook`; 404 at `handlers.go:87`; test `main_test.go:199` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:101 UpdateBook`, `models.go:158 Update`; test `main_test.go:208` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:144 DeleteBook`, `models.go:191 Delete`; 204 at `handlers.go:162` |
| R7 | Data stored in SQLite | ✓ implemented | `models.go:7,44` `modernc.org/sqlite`, real DB file (`main.go:16 DB_PATH`) |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/409/204 across `handlers.go`; JSON encoders throughout |
| R9 | Validation: title & author required | ✓ implemented | `handlers.go:36-43`; test `main_test.go:102 TestCreateBookValidation` |
| R10 | GET /health endpoint | ✓ implemented | `handlers.go:23 HealthCheck`, route `main.go:30`; test `main_test.go:37` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build, run, env vars, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 test functions in `main_test.go`; `test_coverage=0.658>0` |

## Build & Test

Not re-run — scores taken from `scores.json` (inline eval gate).

```text
build: pass       (defect_rate=1.0)
lint:  pass       (code_quality=1.0, 0 warnings)
tests: 9 funcs, 0 skipped, all pass (test_coverage=0.658 line coverage)
```

Skip scan: `grep -rE "t\.Skip\(|t\.Skipf\("` → 0 matches. No skipped or disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go source, incl. tests) | 780 |
| Files (excl. .git) | 15 |
| Dependencies (go.sum entries, all transitive of `modernc.org/sqlite`) | 21 |
| Tests total (top-level funcs) | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — none at or above `high`:

1. [low] GET /health route is not method-restricted (`main.go:30`)
2. [low] Bare `/books/` path returns 400 rather than 404/list (`handlers.go:79`)
3. [info] Duplicate ISBN handled as 409 Conflict — enhancement beyond spec (`handlers.go:47`)
4. [info] created_at/updated_at timestamps tracked — enhancement beyond spec (`models.go:17`)

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s5/rep1
cat scores.json                                    # stored mechanical scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" # skip scan → 0
wc -l *.go                                          # source LOC
# to actually re-run (optional; scores already stored):
go test -v ./...
```
