# Evaluation: rest-api-crud · effort=default language=typescript model=claude-fable-5-1 prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=claude-fable-5-1, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` implies `tsc` build + tests both ran (not re-run here)
- **Lint:** — `code_quality=0.7333` from `scores.json`
- **Architecture:** run-summary skill unavailable in this session — see module notes below
- **Findings:** 0 items in `findings.jsonl`

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items, constant denominator for this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:22-30` → `store.create`, `src/db.ts:29-34`; test `src/../tests/api.test.ts:42` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:32-39` → `store.list`, `src/db.ts:36-43`; test `tests/api.test.ts:90` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:33-38`, `src/db.ts:39-41` `WHERE author = ? COLLATE NOCASE`; test `tests/api.test.ts:98` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/app.ts:41-50` (404 at 45-48); test `tests/api.test.ts:108` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:52-66`, `src/db.ts:52-57`; test `tests/api.test.ts:114` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:68-76`, `src/db.ts:59-61`; test `tests/api.test.ts:130` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts:1,14-27` uses `node:sqlite` `DatabaseSync`; file-persistence test `tests/api.test.ts:144` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201/200/404/400/204 throughout `src/app.ts` (e.g. 29, 46, 75); codes asserted across tests |
| R9 | Input validation: title and author required | ✓ implemented | `src/validation.ts:14-19`, invoked `src/app.ts:23`; test `tests/api.test.ts:60` |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/app.ts:18-20`; test `tests/api.test.ts:35` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup / Run / Test / API sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 12 tests in `tests/api.test.ts`; `test_coverage=1.0` |

## Build & Test

Build/test not re-run — stored mechanical scores used per skill (do not re-run the toolchain).

```text
scores.json (from retort scorers):
  test_coverage = 1.0   → tsc build + all tests executed and passed
  defect_rate   = 1.0   → build+test succeeded
  code_quality  = 0.7333
  maintainability = 0.7240
  idiomatic     = 0.89
  token_efficiency = 0.0591
```

Test command (for reproduction only): `node --import tsx --test tests/*.test.ts` — 12 tests, 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 203 (src) + 159 (tests) = 362 |
| Files (src + tests) | 6 |
| Dependencies | 5 (1 runtime: express; 4 dev) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 pinned requirements implemented and tested; no skipped/disabled tests; build+tests pass (`test_coverage=1.0`). `findings.jsonl` is empty.

Notes (not deductions):
- Uses Node's built-in `node:sqlite` (`DatabaseSync`), avoiding a native SQLite dependency — clean fit for R7, documented in README (requires Node ≥22.13).
- Validation, DB, routing and server bootstrap are cleanly separated (`validation.ts` / `db.ts` / `app.ts` / `server.ts`); `createApp(store)` dependency-injects the store, which the tests exploit with an in-memory DB.

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=typescript_model=claude-fable-5-1_prompt=neutral/rep1"
cat scores.json                       # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json        # pinned 12-item checklist
npm install && npm test               # 12 tests (only to reproduce; scores already stored)
grep -cE "^\s*test\(" tests/api.test.ts
```
