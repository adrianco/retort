# Evaluation: language=typescript_model=sonnet-5_prompt=tdd · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet-5, prompt=tdd (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — `npm run build` (tsc) succeeded (test_coverage=1.0 from scores.json)
- **Lint:** unavailable — no linter configured (code_quality=0.73 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:14` INSERT with all four fields; test `books.test.ts:16` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:29` SELECT all; test `books.test.ts:75` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:33` `WHERE author = ?`; test `books.test.ts:82` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/app.ts:40`; tests `books.test.ts:100,117` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:51` UPDATE + 404 guard; tests `books.test.ts:134,171` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:75` DELETE + 404 guard; tests `books.test.ts:191,205` |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `src/db.ts:1` `node:sqlite` `DatabaseSync`, `books` table |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/204/400/404 across `src/app.ts`; all handlers `res.json` |
| R9 | Validation: title and author required | ✓ implemented | `src/app.ts:17,54` reject missing title/author with 400; tests `books.test.ts:34,43,157` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:10` returns `{status:"ok"}`; test `health.test.ts:6` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — setup/run/test/API sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 13 tests across 2 files; test_coverage=1.0 |

**Prompt factor (tdd):** The agent's stdout log states each route was driven by a failing supertest first, then minimally implemented, then refactored (extracted `getBookById`). Test coverage over every route is complete (13/13). The red/green/refactor *cycle* is not reconstructable from final artifacts (cannot-verify by nature), but the outcome is consistent with the TDD instruction. No skipped/todo tests.

## Build & Test

Build and tests were **not re-run** — mechanical scores are read from `scores.json`:

```text
scores.json: test_coverage=1.0, defect_rate=1.0, code_quality=0.7333, idiomatic=0.9,
             maintainability=0.8698, token_efficiency=1.0
```

test_coverage=1.0 ⇒ `npm run build` (tsc) and `npm test` (jest, 13 tests) both passed.
Agent stdout confirms: "npm run build (tsc) and npm test (jest) both pass; manually smoke-tested with curl."

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 116 (src) + 226 (tests) = 342 |
| Files (excl. node_modules/.git) | 19 |
| Dependencies (deps + devDeps) | 10 |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scored earlier) |

## Findings

Top findings by severity (full list in `findings.jsonl`) — none reach medium:

1. [low] Validation is presence-only; non-numeric `year` unchecked (`src/app.ts:17`)
2. [low] No error-handling middleware around DB calls (`src/app.ts`)
3. [info] Author filter is exact-match only (`src/app.ts:34`)
4. [info] TDD discipline followed per agent log; every route test-covered

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=typescript_model=sonnet-5_prompt=tdd/rep1
# scores read from scores.json (build/test not re-run per skill guidance)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests/ --include="*.ts" | wc -l   # 0 skips
grep -rEc "\bit\(|\btest\(" tests/*.ts    # 13 tests
# To re-verify manually:
npm install && npm run build && npm test
```
