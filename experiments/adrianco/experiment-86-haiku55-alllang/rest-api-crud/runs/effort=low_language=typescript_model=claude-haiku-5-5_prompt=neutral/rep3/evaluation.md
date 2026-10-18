# Evaluation: rest-api-crud · effort=low language=typescript model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** pass — code_quality=0.733 from scores.json (no linter re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Clean, complete implementation. Dependency-free TypeScript on Node's built-in
`http` + `node:sqlite`. Every pinned requirement is satisfied with test coverage,
and the integration suite drives the real server. No defects found.

## Requirements

Checklist from the pinned `REQUIREMENTS.json` (fixed denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:52` → `repo.create`, `src/db.ts:35` INSERT; test `books.test.ts:42` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:47` → `repo.findAll`, `src/db.ts:47`; test `books.test.ts:64` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:48` reads `author`, `src/db.ts:50` `WHERE author = ?`; test `books.test.ts:69` |
| R4 | GET /books/{id} + 404 | ✓ implemented | `src/app.ts:65` `findOr404`, `src/app.ts:97` throws 404; test `books.test.ts:53,59` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/app.ts:69` → `repo.update`, `src/db.ts:54`; test `books.test.ts:77` |
| R6 | DELETE /books/{id} | ✓ implemented | `src/app.ts:77` → `repo.delete` (204), `src/db.ts:62`; test `books.test.ts:91` |
| R7 | SQLite / embedded DB | ✓ implemented | `src/db.ts:1` `node:sqlite` `DatabaseSync`, table created `src/db.ts:24` |
| R8 | JSON responses + status codes | ✓ implemented | `src/app.ts:122` `sendJson`; codes 201/200/204/400/404/405/413/500 across `app.ts` |
| R9 | Validation: title & author required | ✓ implemented | `src/validation.ts:18-22` reject empty/blank; test `books.test.ts:101,110` |
| R10 | GET /health | ✓ implemented | `src/app.ts:40` returns `{status:'ok',database:...}`; test `books.test.ts:34` |
| R11 | README with setup & run | ✓ implemented | `README.md` — Setup/Run/Test/API sections |
| R12 | ≥ 3 tests | ✓ implemented | 11 tests in `test/books.test.ts`; test_coverage=1.0 |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill.

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.733
             maintainability=0.851  idiomatic=0.82
test_coverage=1.0 ⇒ `npm test` (tsc build + node --test) built and passed all tests.
```

Test inventory (static): 1 health + 5 CRUD + 5 validation/routing = 11 tests,
0 `.skip`/`xit`/`todo` (the lone grep hit was `process.exit(0)` in server.ts, a
false positive). All 11 effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 298 (src) + 134 (test) = 432 |
| Files | 5 |
| Dependencies | 2 (both devDependencies: typescript, @types/node — zero runtime deps) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

No defects. Two info-level enhancements (full list in `findings.jsonl`):

1. [info] Error handling beyond spec — 405/413/malformed-JSON mapping (`src/app.ts`)
2. [info] Graceful shutdown + configurable DB path (`src/server.ts`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                      # stored build/test/quality scores
grep -cE "[^.]test\(" test/books.test.ts   # test count
# build+test (optional, not required — scores.json already authoritative):
npm test
```
