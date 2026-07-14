# Evaluation: language=typescript · model=sonnet-5 · prompt=none · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet-5, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — `tsc` (defect_rate=1.0 in scores.json)
- **Lint:** n/a — code_quality=0.73 (scores.json); no separate linter configured
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.ts:14` INSERT + `201`; test `books.test.ts:26` |
| R2 | GET /books lists all | ✓ implemented | `app.ts:35` SELECT *; `books.test.ts:53` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.ts:32-33` WHERE author=?; test `books.test.ts:53` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.ts:40-49`; tests `books.test.ts:40,93` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.ts:52-81` partial-merge UPDATE; tests `books.test.ts:64,75` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.ts:83-94` `204`; test `books.test.ts:80` |
| R7 | Data stored in SQLite | ✓ implemented | `db.ts` uses `node:sqlite` DatabaseSync + `books` table |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/204/400/404 across `app.ts` |
| R9 | Validation: title & author required | ✓ implemented | `validation.ts:19-38`; test `books.test.ts:45` |
| R10 | GET /health | ✓ implemented | `app.ts:10-12` `{status:'ok'}`; test `books.test.ts:20` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup/run/test/API docs |
| R12 | ≥3 tests | ✓ implemented | 8 tests in `tests/books.test.ts` |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.8913   # build + tests passed; 89.13% line/branch coverage
defect_rate   = 1.0      # tsc build + test suite succeeded
code_quality  = 0.7333
maintainability = 0.6673
idiomatic     = 0.68
token_efficiency = 1.0
```

Agent self-report (`_agent_stdout.log`): "8 Jest+Supertest integration tests pass, `tsc` build succeeds ... manually verified the built server serves `/health` and `/books`."

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 298 |
| Files (excl. node_modules/.git) | 19 |
| Dependencies (prod + dev) | 10 |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build | pass (`tsc`) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Validation error branches untested (coverage 89.13%) — non-integer id / mistyped field 400 paths lack tests.
2. [info] `?author=` filter is exact-match only (per spec — noted, not a deduction).
3. [info] Relies on experimental `node:sqlite` (Node 22.5+).

No critical/high/medium findings. Clean, spec-complete run with parameterized queries, DI-friendly app factory, and full endpoint coverage.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=typescript_model=sonnet-5_prompt=none/rep1
cat scores.json                 # mechanical scores (build/test/quality) — not re-run
npm install && npm test         # 8 Jest+Supertest tests
npm run build                   # tsc
```
