# Evaluation: agent=hermes-local language=typescript prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-local (model Qwen3.6-35B-A3B via custom/local provider), prompt=neutral, framework=express (inferred)
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial, 0 missing (pinned REQUIREMENTS.json, 12 total)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective) — from stored scores; not re-run
- **Build:** pass — `tsc` compiled cleanly (test gate requires build; test_coverage=0.294 > 0, defect_rate=1.0 from scores.json)
- **Lint:** unavailable — no lint score/config; code_quality=0.733 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 2 info)

Stored mechanical scores (`scores.json`): test_coverage=0.294, code_quality=0.733, defect_rate=1.0, maintainability=0.864, idiomatic=0.68, token_efficiency=1.0.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `routes.ts:14`; `db.ts:57 createBook` persists all four fields |
| R2 | GET /books lists all | ✓ implemented | `routes.ts:30`; `db.ts:49 SELECT * FROM books` |
| R3 | GET /books ?author= filter | ✓ implemented | `routes.ts:31-32`; `db.ts:44-47 WHERE author = ?` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `routes.ts:37-49`; 404 at `routes.ts:46` |
| R5 | PUT /books/{id} update | ✓ implemented | `routes.ts:53`; `db.ts:66 updateBook` (partial-field merge) |
| R6 | DELETE /books/{id} | ✓ implemented | `routes.ts:85`; `db.ts:89 deleteBook`, 204 at `routes.ts:97` |
| R7 | Data stored in SQLite/embedded DB | ~ partial | `db.ts:1` better-sqlite3 (real embedded DB) but `:memory:` only — no cross-restart persistence |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/204/400/404/500 across `routes.ts` + `app.ts:13,18,31` |
| R9 | Validation: title & author required | ✓ implemented | `routes.ts:18-23` returns 400 when missing |
| R10 | GET /health | ✓ implemented | `app.ts:13-15` returns 200 `{status:"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, setup, build, run, testing sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests.spec.ts` — 16 supertest tests; test_coverage>0 |

Prompt factor `neutral` prescribes no methodology and adds no checkable instructions; requirement list is the pinned REQUIREMENTS.json (P* list empty).

## Build & Test

Build/test were **not re-run** — stored scores were used per the evaluate-run skill.

```text
# build (implied by test gate; jest testMatch targets dist/tests.spec.js)
tsc  → clean compile (test_coverage=0.294 > 0 and defect_rate=1.0 ⇒ build+tests succeeded)
```

```text
# test  (npm test → jest --forceExit --detectOpenHandles)
16 tests, all passing, 0 skipped  (scores.json test_coverage=0.294 = coverage fraction, defect_rate=1.0)
```

Note: two grep hits for skip patterns (`process.exit(` matching `xit(` in `server.ts`) are false positives — no tests are skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Source files (ts) | 6 (app, server, routes, db, tests.spec, jest.config) |
| Total files (excl node_modules/.git) | 18 |
| Dependencies (prod+dev) | 14 |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| test_coverage (stored) | 0.294 |
| code_quality (stored) | 0.733 |
| maintainability (stored) | 0.864 |

Agent usage: 90 API calls, 160,825 input / 37,264 output tokens, model Qwen3.6-35B-A3B (local).

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] R7 — SQLite runs in `:memory:` mode; running service does not persist across restarts (`db.ts:8`, `server.ts`).
2. [low] Unused `sql.js` / `@types/sql.js` dependencies declared but never imported (`package.json:14-17`).
3. [info] Agent-reported better-sqlite3 native ABI mismatch for `npm start`; contradicted by passing in-memory tests (`_agent_stdout.log`).
4. [info] 404/500 handlers and server bootstrap untested (`app.ts:18-33`), contributing to low coverage fraction.

## Reproduce

```bash
cd experiment-20-hermes35b-alllang/bookshop/runs/agent=hermes-local_language=typescript_prompt=neutral/rep2
cat scores.json          # stored mechanical scores (build/test not re-run)
cat stack.json _meta.json
grep -rEc "\b(it|test)\(" tests.spec.ts   # 16 tests
# to actually run (optional): npm install && npm run build && npm test
```
