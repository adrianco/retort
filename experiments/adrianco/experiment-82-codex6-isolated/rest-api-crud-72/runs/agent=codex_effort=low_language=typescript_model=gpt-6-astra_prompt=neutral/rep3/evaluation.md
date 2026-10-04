# Evaluation: rest-api-crud · agent=codex effort=low language=typescript model=gpt-6-astra prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=express (inferred)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — from `test_coverage=1.0` in `scores.json`
- **Build:** pass — `test_coverage=1.0` implies `tsc` build + `node --test` succeeded (not re-run)
- **Lint:** n/a — `code_quality=0.7333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Mechanical scores (from `scores.json`, not re-run): test_coverage=1.0, defect_rate=1.0, code_quality=0.733, maintainability=0.691, idiomatic=0.78, token_efficiency=0.0116.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.ts:56` INSERT, returns 201 + Location; test `app.test.ts:53` |
| R2 | GET /books lists all books | ✓ implemented | `app.ts:45` `SELECT * ... ORDER BY id`; test `app.test.ts:52` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.ts:51-53` parameterized `WHERE author = ?`; test `app.test.ts:71` |
| R4 | GET /books/{id} single book, 404 if absent | ✓ implemented | `app.ts:71-75`; 404 tested `app.test.ts:100` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.ts:76-87` (full replace); test `app.test.ts:59` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.ts:88-92`; test `app.test.ts:62` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `app.ts:2,30` `node:sqlite` DatabaseSync; persistence test `app.test.ts:108` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/404/400/413/500 throughout; error middleware `app.ts:94` |
| R9 | Input validation: title and author required | ✓ implemented | `validateBook` `app.ts:12-27`; test `app.test.ts:78` |
| R10 | GET /health endpoint | ✓ implemented | `app.ts:41-44` (does a `SELECT 1` DB check); test `app.test.ts:96` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — install/build/start, env vars, API table, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 5 tests in `app.test.ts`; `test_coverage=1.0` |

Prompt factor `neutral` prescribes no methodology and asks for tests demonstrating the requirements — satisfied by the 5-test suite; no additional checkable P-requirements.

## Build & Test

Not re-run per skill guidance — stored scores used as the build+test signal.

```text
scores.json: test_coverage=1.0  defect_rate=1.0   (=> tsc build + node --test all passed)
package.json test script: "npm run build && node --test dist/app.test.js"
```

```text
5 tests (app.test.ts), 0 skipped:
  - CRUD lifecycle returns JSON and appropriate statuses
  - author filter is exact and handles SQL-like input safely
  - validates required fields, optional types, and malformed JSON
  - health, invalid IDs, missing books, and unknown routes
  - SQLite data persists when the service is reopened
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 234 (app.ts 102, app.test.ts 120, server.ts 12) |
| Files (excl. node_modules/.git) | 15 |
| Dependencies | 4 (express + @types/express, @types/node, typescript) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] ISBN uniqueness and checksum not enforced (documented as intentional)
2. [info] PUT is a full replace, not a partial update (documented)

No critical/high/medium/low findings — clean run: all 12 requirements implemented, all tests pass, no skipped/disabled tests, parameterized SQL (injection-safe), thorough validation and error handling.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=typescript_model=gpt-6-astra_prompt=neutral/rep3"
cat scores.json                        # stored build/test/quality scores (not re-run)
grep -rEc "\.skip\(|xit\(|it\.todo\(" app.test.ts   # skip detection => 0
# optional full re-run: npm install && npm test
```
