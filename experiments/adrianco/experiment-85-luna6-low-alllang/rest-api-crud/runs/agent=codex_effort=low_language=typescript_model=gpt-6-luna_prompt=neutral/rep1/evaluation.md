# Evaluation: agent=codex effort=low language=typescript model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral (framework=unknown)
- **Status:** ok — repair task; the existing code now builds, tests pass, and every requirement is met
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `tsc` + vitest (test_coverage=1.0 from scores.json)
- **Lint:** pass — code_quality=0.733 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:55-62` INSERT then re-select, 201; test `app.test.ts:43` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:64-70` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:66-68` `WHERE author = ? COLLATE NOCASE`; test `app.test.ts:54-61` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/app.ts:72-78`; tests `app.test.ts:66,71` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:80-89` UPDATE, 404 on no change; test `app.test.ts:67-69` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:91-97` DELETE, 204; test `app.test.ts:70` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/app.ts:2,42-49` `node:sqlite` `DatabaseSync`, `books` table, file `books.sqlite` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400/204 across `src/app.ts:53-97` |
| R9 | Validation: title and author required | ✓ implemented | `src/app.ts:24-25` reject blank/missing → 400; test `app.test.ts:48-52` |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:53` returns `{status:'ok'}`; test `app.test.ts:42` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` setup/run/API/tests (minor Node-version inconsistency, see findings) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/app.test.ts` has 4 `it()` tests, 0 skipped |

## Build & Test

Build/test were **not re-run** — scores read from `scores.json` (inline gate during `retort run`):

```text
scores.json: test_coverage=1.0, defect_rate=1.0, code_quality=0.733,
             maintainability=0.721, idiomatic=0.3, token_efficiency=0.0055
```

`test_coverage=1.0` ⇒ `npm test` (vitest) built and all 4 tests passed. Tests run against an in-memory `node:sqlite` DB (`tests/app.test.ts:10`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 111 (src/app.ts 104 + src/server.ts 7) |
| Test LOC | 73 |
| Files (excl. node_modules) | 8 source/config (src ×2, tests ×1, README, TASK, package.json, tsconfig, package-lock) |
| Dependencies | 8 (1 runtime: express; 7 dev) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not re-run (gate scores reused) |

## Findings

Full list in `findings.jsonl` (both low):

1. [low] README Setup claims Node 18+ but `node:sqlite` requires Node 22.13+ — a user on Node 18 would fail at runtime (`README.md` Setup vs `src/app.ts:2`).
2. [low] Tests dispatch handlers off `app._router.stack` instead of over HTTP, so `express.json()` and the error-handling middleware (`src/app.ts:99-102`) are untested and the declared `supertest` dep is unused.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=typescript_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json            # reuse gate scores; do NOT re-run the toolchain
cat REQUIREMENTS.json      # pinned 12-requirement checklist
# optional, to re-verify locally (needs Node >=22.13):
npm install && npm test
```
