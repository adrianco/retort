# Evaluation: rest-api-crud · effort=low language=typescript model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + all tests passed)
- **Lint:** pass — `code_quality=0.733` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `scores.json` (inline gate output): `test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.733`, `maintainability=0.843`, `idiomatic=0.8`. Build/tests were NOT re-run per skill guidance.

## Requirements

Pinned checklist from `../../../REQUIREMENTS.json` (12 requirements, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/app.ts:84-89` → `repository.ts:39-44` INSERT, 201 |
| R2 | GET /books lists all | ✓ implemented | `src/app.ts:80-82` → `repository.ts:52-57` findAll |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:81`; `repository.ts:53-54` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `src/app.ts:97-99`; `repository.ts:46-49` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/app.ts:101-106` → `repository.ts:60-73`, 404 on missing |
| R6 | DELETE /books/{id} | ✓ implemented | `src/app.ts:107-108` → `repository.ts:75-78`, 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/repository.ts:1` `node:sqlite` `DatabaseSync`, real table |
| R8 | JSON responses + status codes | ✓ implemented | `src/app.ts:13-29` send/sendError; 201/200/204/400/404/405/413/500 |
| R9 | Validation: title+author required | ✓ implemented | `src/book.ts:40-47`; test `tests/books.test.ts:34-38` |
| R10 | GET /health | ✓ implemented | `src/app.ts:68-77` → `repository.ts:80-83` ping; test:73-77 |
| R11 | README with setup/run | ✓ implemented | `README.md` setup/run/test/API sections |
| R12 | >= 3 tests | ✓ implemented | `tests/books.test.ts` — 13 tests, `test_coverage=1.0` |

## Build & Test

```text
npm test  (npm run build && node --test dist/tests/books.test.js)
Not re-run — scores.json: test_coverage=1.0 (build succeeded, all tests passed), defect_rate=1.0
```

13 tests, 0 skipped. (A naive skip grep reported 1, but it matched `process.exit(` in `src/server.ts:17` via the `xit(` pattern — a false positive, not a disabled test.)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 441 (src 299 + tests 142) |
| Files | 5 TS source + package.json/tsconfig/README |
| Dependencies | 2 (both dev: typescript, @types/node) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| code_quality | 0.733 |
| maintainability | 0.843 |

## Findings

No correctness, build, or test findings. 4 info-level items (full list in `findings.jsonl`):

1. [info] E1 — Defensive extras beyond spec (1 MB body cap, malformed-JSON 400, 405 on wrong method)
2. [info] E2 — Year/ISBN format validation beyond the required title/author check
3. [info] E3 — Graceful shutdown on SIGINT/SIGTERM
4. [info] N1 — `?author=` filter is exact case-insensitive match, not substring (spec unspecified)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                       # build/test scores (do not re-run)
cat ../../../REQUIREMENTS.json        # pinned 12-requirement checklist
# To re-run tests manually (not required): npm install && npm test
```
