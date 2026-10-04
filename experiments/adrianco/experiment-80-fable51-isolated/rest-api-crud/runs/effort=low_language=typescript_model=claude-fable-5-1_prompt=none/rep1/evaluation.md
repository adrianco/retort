# Evaluation: effort=low_language=typescript_model=claude-fable-5-1_prompt=none · rep 1

## Summary

- **Factors:** language=typescript, model=claude-fable-5-1, prompt=none, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — from `test_coverage=1.0` in scores.json
- **Build:** pass (from `test_coverage=1.0`; `npm test` runs `tsc` then the suite)
- **Lint:** n/a — `code_quality=0.7333` (scores.json); no linter configured in this workspace
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:49` handler → `src/db.ts:29` `store.create`; test `src/../tests/books.test.ts:40` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:58` → `src/db.ts:36` `store.list`; test line 70 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:59` reads `req.query.author`; `src/db.ts:39` `WHERE author = ?`; test line 77 |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `src/app.ts:63-71`; test lines 46, 107 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:73-90` → `src/db.ts:47` `store.update`; test line 84 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:92-99` → `src/db.ts:54` `store.delete`; test line 100 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts:1` `node:sqlite` `DatabaseSync`, real `CREATE TABLE`/prepared statements |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404/500 across `src/app.ts:45-112` |
| R9 | Input validation: title and author required | ✓ implemented | `src/app.ts:13-18` `validateBook`; test line 51 (missing) + malformed JSON line 61 |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:45-47`; test line 34 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup/Run/Test/Endpoints/Example sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 8 `node:test` cases, all pass (`test_coverage=1.0`) |

## Build & Test

Not re-run — mechanical scores were read from `scores.json` (inline gate output):

```text
scores.json: {"code_quality": 0.7333, "token_efficiency": 0.0326, "test_coverage": 1.0,
              "defect_rate": 1.0, "maintainability": 0.7293, "idiomatic": 0.87}
```

`test_coverage=1.0` and `defect_rate=1.0` ⇒ `npm test` (`tsc` build + `node --test`) succeeded with all tests passing. 0 skipped tests (grep for `.skip(`/`xit(`/`xdescribe(`/`it.todo(` → 0 matches).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 295 (app 115, db 61, server 9, tests 110) |
| Files | 4 source/test files |
| Dependencies | 4 (express + 3 dev: @types/express, @types/node, typescript) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; read from scores.json) |

## Findings

None. All 12 pinned requirements are implemented and exercised by passing tests; no
skipped/disabled tests; build and test gates green (`test_coverage=1.0`).

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=typescript_model=claude-fable-5-1_prompt=none/rep1"
cat scores.json                                   # stored mechanical scores (do not re-run)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests/ --include="*.ts" | wc -l   # 0 skips
# Full build+test (only if re-verifying): npm install && npm test
```
