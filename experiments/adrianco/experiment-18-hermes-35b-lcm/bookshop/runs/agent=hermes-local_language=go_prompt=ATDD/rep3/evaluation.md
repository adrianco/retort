# Evaluation: agent=hermes-local language=go prompt=ATDD · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown (gorilla/mux + mattn/go-sqlite3), prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Prompt (ATDD):** 3/4 followed, 1 cannot-verify (initial-failing-tests ordering)
- **Tests:** 25 passed / 0 failed / 0 skipped (25 effective) — 75.4% coverage
- **Build:** pass (defect_rate=1.0 from retort.db/scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:61 handleCreateBook`, `database.go:45 CreateBook`; test `server_test.go:40` |
| R2 | GET /books lists all | ✓ implemented | `server.go:82 handleListBooks`, `database.go:94 ListBooks`; test `server_test.go:337` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:83-88`, `database.go:113 ListBooksByAuthor`; test `server_test.go:121` |
| R4 | GET /books/{id} + 404 | ✓ implemented | `server.go:102 handleGetBook` returns 404; tests `server_test.go:81,268` |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.go:120 handleUpdateBook`, `database.go:79 UpdateBook`; test `server_test.go:163` |
| R6 | DELETE /books/{id} | ✓ implemented | `server.go:156 handleDeleteBook` returns 204/404; test `server_test.go:197` |
| R7 | SQLite / embedded DB | ✓ implemented | `database.go:7 mattn/go-sqlite3`, `database.go:23 CREATE TABLE books` |
| R8 | JSON responses + status codes | ✓ implemented | `server.go:43 writeJSON`; 201/200/204/400/404/500 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `models.go:16 Validate`; tests `server_test.go:228,248` |
| R10 | GET /health | ✓ implemented | `server.go:56 handleHealth`; test `server_test.go:22` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, curl examples, testing |
| R12 | ≥3 unit/integration tests | ✓ implemented | 25 test funcs across 3 files; coverage 75.4% |

### Prompt (ATDD) conformance

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Acceptance tests exercise SUT only through public HTTP interface | ✓ followed | `server_test.go` 14 `TestAcceptance_*` use `srv.ServeHTTP` with HTTP requests/JSON; no DB back-door in acceptance tests |
| P2 | Assert on WHAT (domain language), atomic & independent, fresh empty service each scenario | ✓ followed | Each test calls `createTestServer()` → fresh `:memory:` DB (`server_test.go:12`); named for domain behaviors |
| P3 | Finer-grained unit TDD underneath | ✓ followed | `database_test.go` (7) + `models_test.go` (4) unit tests |
| P4 | Tests fail initially, then implement until pass | ~ cannot-verify | Final state only; test-first ordering not observable from the archive |

## Build & Test

Scores read from `scores.json` (inline gate) — toolchain not re-run per skill guidance:

```text
scores.json: {"code_quality": 1.0, "test_coverage": 0.754, "defect_rate": 1.0,
              "maintainability": 0.893, "idiomatic": 0.68, "token_efficiency": 0.0153}
```

```text
Tests: 25 functions (server_test.go=14, database_test.go=7, models_test.go=4)
Skips: 0   →   effective = 25
defect_rate=1.0 ⇒ go build + go test passed; coverage 75.4%
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 352 (server 176, database 131, models 24, main 21) |
| Files (source + docs + mod) | 10 |
| Dependencies | 2 (gorilla/mux, mattn/go-sqlite3) |
| Tests total | 25 |
| Tests effective | 25 |
| Skip ratio | 0% |
| Coverage | 75.4% |
| code_quality (lint) | 1.0 |
| maintainability | 0.893 |
| idiomatic | 0.68 |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] `TestModel_ValidateRequiresBothFields` has a dead `errors.Is(err, nil)` assertion branch — `models_test.go:39`
2. [info] Health check does not verify DB connectivity — `server.go:56`
3. [info] PUT uses full-replace semantics (spec-compliant) — `server.go:120`
4. [info] Coverage 75.4% — main() and 500 error paths untested — `scores.json`

No critical/high/medium findings. All requirements implemented; ATDD strongly followed.

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=go_prompt=ATDD/rep3
cat scores.json                                    # stored build/test/lint scores
grep -rEn "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rE "^func Test" *_test.go | wc -l            # 25 test functions
# (build/tests not re-run — defect_rate=1.0 already confirms pass)
```
