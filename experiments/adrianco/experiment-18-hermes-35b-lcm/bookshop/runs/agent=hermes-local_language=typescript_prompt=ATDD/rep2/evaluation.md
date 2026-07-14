# Evaluation: agent=hermes-local language=typescript prompt=ATDD · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-local, framework=unknown (Express), prompt=ATDD
- **Status:** ok — all 12 requirements implemented; build + tests pass (`defect_rate=1.0`)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **ATDD prompt factor:** followed — acceptance suite drives the public HTTP interface only; unit TDD underneath (P1–P4 met, P5 test-first ordering cannot-verify from artifact)
- **Tests:** 34 total, 0 skipped (34 effective). Suite passes per `defect_rate=1.0`.
- **Build:** pass — `tsc --noEmit` clean, `eslint` clean (`defect_rate=1.0`, not re-run)
- **Lint:** pass — 0 defects/kloc (`code_quality=0.733`, `defect_rate=1.0`)
- **Coverage:** 36.2% line coverage (`test_coverage=0.362`) — low relative to the passing suite; see finding `cov-1`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 2 low, 1 info)

## Requirements

Denominator pinned by `bookshop/REQUIREMENTS.json` (12 requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.ts:32`, `db.ts:createBook:43`; test "creates a book when all required fields are provided" |
| R2 | GET /books lists all books | ✓ implemented | `app.ts:43`, `db.ts:getAllBooks:58`; test "returns all books when books exist" |
| R3 | GET /books ?author= filter | ✓ implemented | `app.ts:44-46`, `db.ts:60`; test "returns books filtered by author" |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.ts:51-58`; tests "returns the book when ID exists" / "returns 404" |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.ts:61-73`, `db.ts:updateBook:73`; test "updates the book" |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.ts:76-83`, `db.ts:deleteBook:90`; test "deletes the book and returns 200" |
| R7 | Data stored in SQLite | ✓ implemented | `db.ts:16-29` better-sqlite3 `CREATE TABLE books`, WAL |
| R8 | JSON + appropriate status codes | ✓ implemented | 201 (`app.ts:39`), 200, 400 (`app.ts:36`), 404 (`app.ts:55,70,80`) |
| R9 | Validation: title+author required | ✓ implemented | `validation.ts:13-21`, `app.ts:34-37`; tests "rejects missing title/author" |
| R10 | GET /health | ✓ implemented | `app.ts:27-29`; test "returns 200 with status ok" |
| R11 | README with setup/run | ✓ implemented | `README.md` — install/build/run/test + API examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 34 tests across `tests/acceptance.test.ts` + `tests/unit.test.ts` (`test_coverage>0`) |

### ATDD prompt-factor conformance

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Acceptance tests exercise SUT via public HTTP only, no DB back-door | ✓ | `acceptance.test.ts` asserts only on supertest HTTP responses; no direct DB reads in assertions |
| P2 | Atomic & independent, each starts from empty service | ✓ | `acceptance.test.ts:19-23` fresh `:memory:` DB + app in `beforeEach` |
| P3 | Domain-language scenario names | ✓ | "create a book", "filter by author", "reject … missing title", etc. |
| P4 | Finer-grained unit TDD underneath | ✓ | `unit.test.ts` covers `validateBook` + DB layer |
| P5 | Tests written to fail first, then implemented | ~ cannot-verify | No git history in archive to confirm test-first ordering; structure is consistent with it |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate; no `retort.db` row for this cell).

```text
scores.json
  test_coverage   = 0.362   # jest --coverage "Lines : 36.2%"
  defect_rate     = 1.0     # tsc --noEmit clean + eslint clean + tests pass → 0 defects/kloc
  code_quality    = 0.733
  maintainability = 0.925
  idiomatic       = 0.700
  token_efficiency= 1.0
```

```text
tests: 34 it-blocks (17 acceptance + 17 unit), 0 skipped → 34 effective
agent self-report (_agent_stdout.log): "All 34 tests pass. Build succeeds."
```

Note: `test_coverage=0.362` (36.2% line coverage) is low relative to a comprehensive, all-passing 34-test suite. The most plausible drivers are the `src/app.ts` coverage exclusion in `jest.config.js:9` (`cov-2`) and/or native-module (`better-sqlite3`) instrumentation in the scoring environment. Flagged as `cov-1`; not treated as a test failure since `defect_rate=1.0` and the suite passes.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, src/) | 237 |
| Lines of code (tests) | 380 |
| Files (excl. node_modules/dist) | 18 |
| Dependencies | 12 (2 runtime + 10 dev) |
| Tests total | 34 |
| Tests effective | 34 |
| Skip ratio | 0% |
| Line coverage | 36.2% |
| Build duration | not re-run |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] cov-1 — Measured line coverage 36.2% despite 34 passing tests (`scores.json`)
2. [medium] cov-2 — `jest.config.js:9` excludes `src/app.ts` (HTTP route layer / ATDD SUT) from coverage
3. [low] dead-1 — Unused module-global DB handle `setAppDb`/`getAppDb`/`shutdownDb` (`db.ts:14,31-37`)
4. [low] repr-1 — Omitted year/isbn returned as `0`/`""` on create but `null` on GET (`db.ts:55,87`)
5. [info] naming-1 — SCREAMING_CASE function names `COUNT_ALL`/`COUNT_BY_AUTHOR` (`db.ts:98,104`)

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=typescript_prompt=ATDD/rep2
cat scores.json                       # stored mechanical scores (no re-run)
grep -rE "\.skip\(|xit\(|it\.todo\(" tests --include="*.ts" | wc -l   # 0 skips
grep -rhE "^\s*(it|test)\(" tests --include="*.ts" | wc -l            # 34 tests
# Optional full re-run: npm install && npm test
```
