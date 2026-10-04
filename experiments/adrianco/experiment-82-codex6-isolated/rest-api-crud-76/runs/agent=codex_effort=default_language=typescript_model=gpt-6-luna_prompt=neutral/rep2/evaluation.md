# Evaluation: agent=codex model=gpt-6-luna language=typescript prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — `test_coverage=1.0` implies build+test succeeded (not re-run)
- **Lint:** pass — `code_quality=0.733` (scores.json); no blocking issues
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `src/app.ts:39` POST handler → `BookStore.create` `src/books.ts:39` inserts all four fields |
| R2 | GET /books lists all | ✓ implemented | `src/app.ts:37` → `store.list()` `src/books.ts:26` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/books.ts:29` `WHERE author = ?`; wired via `url.searchParams.get('author')` `src/app.ts:37` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/app.ts:48` → `store.get`, returns 404 when undefined |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/app.ts:53` → `store.update` `src/books.ts:44`, 404 when no row changed |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/app.ts:60` → `store.delete` `src/books.ts:49`, 204 / 404 |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `src/books.ts:2` `node:sqlite` `DatabaseSync`, `CREATE TABLE books`, default file `books.db` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `send()` `src/app.ts:6` sets JSON content-type; 201/200/404/400/204 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `validate()` `src/app.ts:18-20` rejects missing/blank title or author with 400; test at `test/api.test.ts:37` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:36` returns `{status:'ok'}` 200; test `test/api.test.ts:17` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Setup/run, endpoints, tests sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 3 `test(...)` blocks in `test/api.test.ts`; `test_coverage=1.0` |

## Build & Test

Build and tests were **not re-run** — stored mechanical scores are authoritative:

```text
scores.json: {"test_coverage": 1.0, "defect_rate": 1.0, "code_quality": 0.733,
              "maintainability": 0.800, "idiomatic": 0.76, "token_efficiency": 0.0106}
test_coverage=1.0  => `npm test` (tsx --test test/*.test.ts) built and passed all tests.
```

Test suite (`test/api.test.ts`, node:test against in-memory SQLite):
1. health check responds with JSON
2. creates, retrieves, filters, updates, and deletes books (full CRUD + author filter)
3. rejects missing required fields and reports unknown books (400 + 404)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 156 (src 116, test 40) |
| Files | 4 (3 src, 1 test) |
| Dependencies | 3 (all devDependencies: @types/node, tsx, typescript; 0 runtime deps) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; test_coverage=1.0) |

## Findings

Full list in `findings.jsonl` (both info-level, no deductions):

1. [info] Redundant year type guard in `validate()` — `src/app.ts:22` second clause unreachable
2. [info] No external runtime dependencies — self-contained on Node ≥22.5 (`node:sqlite`, `node:http`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                                    # stored mechanical scores (build+test not re-run)
cat ../../REQUIREMENTS.json                         # pinned 12-requirement checklist
grep -rE "\.skip\(|xit\(|it\.todo\(" test src       # skip detection -> 0
# to actually run: npm install && npm test
```
