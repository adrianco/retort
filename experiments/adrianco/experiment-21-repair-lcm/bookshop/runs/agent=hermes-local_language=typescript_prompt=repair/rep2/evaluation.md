# Evaluation: agent=hermes-local · language=typescript · prompt=repair · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-local (model Qwen3.6-35B-A3B, local/oMLX), framework=express, prompt=repair
- **Status:** ok (with caveat) — build/static-analysis clean and all 12 requirements implemented, but the independent test/coverage gate scored only 0.294 (see Findings)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 16 present / 0 skipped (16 effective) — test/coverage gate score `test_coverage=0.2941`; not re-run (stored score)
- **Build:** pass — `defect_rate=1.0` ⇒ `tsc --noEmit` + `eslint` reported 0 defects (from scores.json)
- **Lint:** pass — 0 warnings (`code_quality=0.733`, `defect_rate=1.0`)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 2 low)

This is a **repair** run: a prior attempt failed evaluation (per `FEEDBACK.md`: "build/tests did not fully pass, requirement_coverage 0.92"). The agent restored `better-sqlite3` (removed in an earlier attempt that switched to `sql.js`), rebuilt the native binary for the current Node, and fixed `jest.config.js` to run `.ts` via `ts-jest`. Code-level requirement coverage improved to 12/12, but the independent test gate (`test_coverage=0.294`) still does not demonstrate a clean, fully-passing suite.

## Requirements

Pinned checklist from `REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `routes.ts:12` POST handler → `db.ts:56` `createBook` INSERT; returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `routes.ts:29` → `db.ts:42` `getAllBooks` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `routes.ts:31` reads `req.query.author`; `db.ts:44` `WHERE author = ?` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `routes.ts:37` → `db.ts:51` `getBookById`; 404 at `routes.ts:45` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `routes.ts:52` → `db.ts:66` `updateBook` (partial-update merge); 404 handled |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `routes.ts:86` → `db.ts:90` `deleteBook`; returns 204, 404 if absent |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `db.ts:1` `better-sqlite3`; real SQLite engine — but `:memory:` mode (see finding R7-inmemory) |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/204/400/404/500 across `routes.ts` + `app.ts:12,16` |
| R9 | Input validation: title & author required | ✓ implemented | `routes.ts:16` `if (!title || !author) → 400`; tests at `tests.spec.ts:52,60` |
| R10 | GET /health health check | ✓ implemented | `app.ts:12` returns 200 `{status:"ok"}`; test `tests.spec.ts:24` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, build, run, test, curl examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 16 supertest tests in `tests.spec.ts`; `test_coverage=0.2941 > 0` |

## Build & Test

Per skill policy, stored scores were used — **build/tests/lint were not re-run**.

```text
Source (scores.json):
  test_coverage   = 0.2941   # TS scorer: jest --coverage statement %  (build+test gate)
  defect_rate     = 1.0000   # tsc --noEmit + eslint: 0 defects/kloc  (compiles clean)
  code_quality    = 0.7333
  maintainability = 0.8613
  idiomatic       = 0.6800
  token_efficiency= 1.0000
```

Interpretation: TypeScript source compiles and passes static analysis (`defect_rate=1.0`). The test gate for TS is the parsed coverage percentage, recorded at **29.4%**. The agent's own log (`_agent_stdout.log`) asserts "All 16 tests pass," but the independent scorer does not corroborate a fully-passing / well-covered run — the gap is the run's principal weakness and the reason it falls short of the repair task's stated goal. `server.ts` (listener + signal handlers) and the 404/500 handlers in `app.ts` are never exercised by the suite, which partly explains the low statement coverage.

Skipped/disabled tests: **0**. (The skip grep matched 2 lines, both false positives — `process.exit(` in `server.ts` matching the `xit(` pattern.)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, non-test .ts) | 273 |
| Lines of code (incl. tests.spec.ts) | 463 |
| Files (.ts source) | 5 |
| Dependencies (deps + devDeps) | 12 |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Test/coverage gate (test_coverage) | 0.2941 |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. **[high]** Independent test/coverage gate scored 0.294 — far below a fully-passing suite; contradicts the agent's self-reported 16/16 (`scores.json`, `_agent_stdout.log`).
2. **[medium]** R7 SQLite runs in `:memory:` mode — server does not persist across restarts (`db.ts:26`).
3. **[low]** `jest.config.js` uses the deprecated `globals['ts-jest']` form alongside `transform` (`jest.config.js:11`).
4. **[low]** POST/PUT validate presence but not type of `title`/`author` (`routes.ts:14`).

## Reproduce

```bash
cd "experiment-21-repair-lcm/bookshop/runs/agent=hermes-local_language=typescript_prompt=repair/rep2"
cat scores.json            # stored gate scores (do not re-run per skill policy)
cat _agent_stdout.log      # agent's self-report
# Skip detection (2 matches are false positives — process.exit vs xit()):
grep -rEn "\.skip\(|xit\(|xdescribe\(|it\.todo\(|\.only\(" . --include="*.ts" | grep -v node_modules
wc -l app.ts db.ts routes.ts server.ts   # 273 non-test source LOC
# To independently confirm the test gate (NOT done here — scores.json present):
#   npm install && npm rebuild better-sqlite3 && npx jest --coverage
```
