# Evaluation: rest-api-crud · effort=default language=typescript model=claude-fable-5-1 prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, model=claude-fable-5-1, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json); `npm test` compiles (`tsc`) then runs
- **Lint:** n/a (no linter in stack) — `code_quality=0.733` from scores.json
- **Architecture:** run-summary skill unavailable in this session; structure summarized inline below
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:67-71` POST handler → `src/store.ts:27-32` INSERT; 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:63-65` → `src/store.ts:34-42` SELECT ... ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:64` reads `author` param → `src/store.ts:38-40` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/app.ts:82-86`, 404 via `store.get` miss; `tests/books.test.ts:106-109` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:87-91` → `src/store.ts:49-54` UPDATE; 404 if no rows changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:92-97` → `src/store.ts:56-58`; 204 on success, 404 if absent |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/store.ts:1,11-25` `node:sqlite` `DatabaseSync`, real table; file persistence test `tests/books.test.ts:147-164` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `src/app.ts:17-24` `sendJson`; 201/200/204/400/404/405/413/500 used across routes |
| R9 | Input validation: title and author required | ✓ implemented | `src/validation.ts:12-19,28-29` `requiredString`; 400 in `app.ts:41-45`; `tests/books.test.ts:59-74` |
| R10 | GET /health health-check | ✓ implemented | `src/app.ts:57-60` returns `{status:"ok"}`; `tests/books.test.ts:35-42` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup/Run/Test sections, API table, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 14 `it(...)` in `tests/books.test.ts`; `test_coverage=1.0` |

## Build & Test

```text
npm test    # (tsc && node --test "dist/tests/**/*.test.js")
```

Not re-run per skill guidance — mechanical scores read from `scores.json`:
`test_coverage=1.0` ⇒ TypeScript build (`tsc`, strict + noUncheckedIndexedAccess)
succeeded and all tests passed. `defect_rate=1.0` corroborates build+test success.
14 tests across health, POST validation, list/filter, get-by-id, update, delete,
routing (404/405) and SQLite file-persistence; 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 250 (src) + 164 (tests) = 414 |
| Files (excl. build artifacts) | 17 |
| Dependencies | 2 (both devDependencies: typescript, @types/node — zero runtime deps) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| test_coverage (scores.json) | 1.0 |
| code_quality (scores.json) | 0.733 |
| maintainability (scores.json) | 0.879 |
| idiomatic (scores.json) | 0.87 |
| token_efficiency (scores.json) | 0.067 |

## Architecture (inline; run-summary unavailable)

Clean four-module separation with zero runtime dependencies — uses only Node
stdlib (`node:http`, `node:sqlite`):
- `src/validation.ts` — pure body validation, discriminated-union `ValidationResult`.
- `src/store.ts` — `BookStore` over `DatabaseSync`, parameterized SQL, `:memory:` default.
- `src/app.ts` — routing + handlers, `HttpError` for status mapping, 1 MB body cap.
- `src/server.ts` — entry point, env-configurable PORT/DB_PATH, graceful SIGINT/SIGTERM.
Tests inject an in-memory store and hit a real ephemeral server via `fetch`.

## Findings

No findings — 0 items in `findings.jsonl`. All 12 pinned requirements are
implemented and tested; the build and full test suite pass; no skipped/disabled
tests. Input validation, correct status codes, SQLite persistence, and the
health endpoint are all present with test coverage.

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=typescript_model=claude-fable-5-1_prompt=neutral/rep2"
cat scores.json                 # mechanical scores (test_coverage=1.0)
cat ../../../REQUIREMENTS.json  # pinned 12-requirement checklist
# Optional full re-run (not required; scores already stored):
#   npm install && npm test
```
