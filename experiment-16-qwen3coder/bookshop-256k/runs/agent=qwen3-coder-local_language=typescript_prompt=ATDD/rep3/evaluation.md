# Evaluation: agent=qwen3-coder-local language=typescript prompt=ATDD · rep 3

## Summary

- **Factors:** language=typescript, agent=qwen3-coder-local, prompt=ATDD, framework=unknown
- **Status:** ok (app functional) — but the ATDD acceptance suite does not pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (against pinned `REQUIREMENTS.json`)
- **Tests:** acceptance 1/12 pass (11 fail, `SQLITE_IOERR`); functional 2/3; simple 2/2; unit 2/2 — of which 2 are vacuous/soft-skipped. Stored `test_coverage=0.7241` (tests executed; gate not full-stop).
- **Build:** pass — `defect_rate=1.0` from `scores.json` (server imports & runs)
- **Lint:** n/a — no linter configured; `code_quality=0.7333`, `maintainability=0.5285`, `idiomatic=0.0` (stored)
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (0 critical, 3 high, 3 medium, 1 low, 1 info)

## Requirements

Checklist is the pinned `bookshop-256k/REQUIREMENTS.json` (constant denominator = 12).
All are satisfied by `src/server.js` at runtime; failures below are in the *test
harness*, not the endpoints.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/server.js:42-76` insert + 201 |
| R2 | GET /books lists all | ✓ implemented | `src/server.js:79-99` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/server.js:84-87` WHERE author=? |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `src/server.js:102-122` 404 at 114 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/server.js:125-166` |
| R6 | DELETE /books/{id} | ✓ implemented | `src/server.js:169-189` |
| R7 | SQLite / embedded DB | ✓ implemented | `src/server.js:15` sqlite3, `books.db` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/400/404/500 throughout |
| R9 | Validation: title & author required | ✓ implemented | `src/server.js:46-50` (400) |
| R10 | GET /health | ✓ implemented | `src/server.js:37-39` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, endpoints, testing) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 19 tests across 4 suites; `test_coverage=0.7241>0` |

**Prompt-factor (ATDD) conformance:** *Partially met.* The agent did produce an
external, HTTP-only acceptance suite (`tests/acceptance.test.js` via supertest,
asserting on domain behavior) — the right *shape* for ATDD. But it fails the
prompt's own bar: the suite does not pass (`SQLITE_IOERR`, F1) and its scenarios
are neither atomic nor independent (shared persistent DB, F2). The prompt states
"passing the executable acceptance suite is what demonstrates the requirements
are met" — that demonstration never happens.

## Build & Test

```text
# Stored scores (scores.json) — build/test NOT re-run per evaluate-run skill
defect_rate    = 1.0     (build/import OK)
test_coverage  = 0.7241  (tests executed; not all pass)
code_quality   = 0.7333
maintainability= 0.5285
idiomatic      = 0.0     (typescript factor, plain JS delivered)
token_efficiency = 1.0
```

```text
# Final agent test runs (_agent_stdout.log)
FAIL tests/acceptance.test.js   -> 11 failed, 1 passed, 12 total   (SQLITE_IOERR: disk I/O error; endpoints 500)
mixed run                        -> 7 failed, 9 passed, 16 total
FAIL tests/functional.test.js   -> 1 failed, 2 passed, 3 total     (validation regex assertion, F6)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 238 (`server.js` 216 + `database.js` 22) |
| Test LOC | 473 |
| Files (excl. node_modules/logs) | 18 |
| Dependencies | 4 (express, sqlite3, jest, supertest) |
| TypeScript files | 0 |
| Tests total | 19 |
| Tests effective (excl. 2 vacuous/soft-skip) | 17 |
| Acceptance-suite pass rate | 1/12 |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] F1 — ATDD acceptance suite fails on every scenario: `beforeAll` unlinks `books.db` after the server opened the handle → `SQLITE_IOERR`, all endpoints 500 (`tests/acceptance.test.js:20-26`).
2. [high] F2 — Acceptance scenarios are not atomic/independent: one shared persistent DB, no per-test reset, `toHaveLength(2)` assumes isolation — a direct ATDD-prompt violation.
3. [high] F3 — `language=typescript` run delivered plain CommonJS JavaScript (0 `.ts` files, `idiomatic=0.0`).
4. [medium] F4 — `tests/unit.test.js:19` tautological `expect(true).toBe(true)` placeholder.
5. [medium] F5 — `tests/simple.test.js:26-34` soft-skips the health test by swallowing errors.

## Reproduce

```bash
cd "experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=typescript_prompt=ATDD/rep3"
cat scores.json                                   # stored mechanical scores (source of truth)
cat ../../REQUIREMENTS.json                        # pinned 12-req checklist
find . -name '*.ts' -not -path '*/node_modules/*' | wc -l   # 0 -> idiomatic=0
grep -aoE "Tests:[^\\]*(passed|failed|total)[^\\]*" _agent_stdout.log   # jest summaries
# App itself runs: npm install && npm start ; curl localhost:3000/health
```
