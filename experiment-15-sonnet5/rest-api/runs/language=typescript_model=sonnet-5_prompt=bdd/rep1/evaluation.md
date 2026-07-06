# Evaluation: language=typescript · model=sonnet-5 · prompt=bdd · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet-5, prompt=bdd (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass (test_coverage=0.939, defect_rate=1.0 from scores.json — build + all tests passed)
- **Lint:** pass (code_quality=0.733 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

A clean, complete implementation. TypeScript + Express REST API with SQLite persistence via Node's built-in `node:sqlite`. Every task requirement is implemented and exercised by tests. Tests follow the requested BDD (Given/When/Then) style with behaviour-named cases. No skipped or disabled tests. Findings are minor polish items only.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:14` INSERT + 201; test `given valid book data...` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:37,45`; test `...when listing all books, then all are returned` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:40-43`; test `...when filtering by author...` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/app.ts:50-61`; tests for found + 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:63-97`; tests for update + 404 + 400 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:99-110` (204); tests for delete + 404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts` uses `node:sqlite` DatabaseSync + `books` table |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/400/404/204 across `src/app.ts` |
| R9 | Input validation: title and author required | ✓ implemented | `src/validation.ts:15-25`; missing-title/author 400 tests |
| R10 | GET /health health-check | ✓ implemented | `src/app.ts:10-12` returns `{status:"ok"}`; health test |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` (setup, run, env vars, full API reference) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 14 tests, test_coverage=0.939 |

Prompt factor (bdd): tests use Given/When/Then structure and behaviour-oriented names (e.g. `given valid book data, when creating a book, then it is persisted...`) — the BDD instruction is followed. REQUIREMENTS.json is the pinned, complete checklist; the BDD prompt adds a style constraint, not new scored requirements.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill step 2):

```text
test_coverage = 0.939   (build + all 14 tests passed; ~94% coverage)
defect_rate   = 1.0     (build + test succeeded)
code_quality  = 0.733
idiomatic     = 0.88
maintainability = 0.726
token_efficiency = 1.0
```

Agent's own summary (`_agent_stdout.log`): "Everything builds and all 14 tests pass."

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src + tests) | 412 |
| Source files (src/) | 5 |
| Test files | 1 |
| Dependencies (deps + devDeps) | 10 |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build | pass (scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Some validation/error branches lack dedicated tests (coverage 93.9%) — `src/validation.ts:27-37`, non-integer `:id` paths.
2. [info] PUT /books/:id with an empty body is a silent no-op returning 200 — `src/app.ts:76,81-96`.
3. [info] GET /books?author= (empty value) filters to an empty result rather than returning all — `src/app.ts:40`.

No critical, high, or medium findings.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=typescript_model=sonnet-5_prompt=bdd/rep1
cat scores.json                       # mechanical scores (build/test/lint) — not re-run
npm install && npm run build          # tsc
npm test                              # jest + supertest, 14 tests
```
