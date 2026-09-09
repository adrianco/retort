# Evaluation: rest-api-crud · agent=codex effort=low language=typescript model=gpt-6-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (implied by `test_coverage=1.0`; test script runs `tsc` then `node --test`)
- **Lint:** n/a — no linter configured; `code_quality=0.7167` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.ts:38-41` → `store.create` (`store.ts:38-42`); test `app.test.ts:62` |
| R2 | GET /books lists all books | ✓ implemented | `app.ts:42-48` → `store.list` (`store.ts:28-32`); test `app.test.ts:61,78` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.ts:43-47`; `store.ts:31` `WHERE author = ?`; test `app.test.ts:81-84` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.ts:56-60`; test `app.test.ts:66,106` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.ts:61-65` → `store.update` (`store.ts:44-48`); test `app.test.ts:67-70` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.ts:66-71` → `store.delete` (`store.ts:50-52`); test `app.test.ts:71-72` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.ts:1` `node:sqlite` `DatabaseSync`; persistence test `app.test.ts:124-145` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400/413/415/500 across `app.ts:35-84` |
| R9 | Validation: title and author required | ✓ implemented | `validateBook` `app.ts:6-28`; DB `CHECK` `store.ts:20-21`; test `app.test.ts:89-99` |
| R10 | GET /health health check | ✓ implemented | `app.ts:35-37`; test `app.test.ts:103-104` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` — setup, run, env vars, API table, curl examples, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 tests in `app.test.ts`; `test_coverage=1.0` |

## Build & Test

Build/test not re-run — stored scores used per skill (`test_coverage=1.0` ⇒ build + all tests passed).

```text
# package.json test script
npm run build && node --test dist/app.test.js
# scores.json: {"test_coverage": 1.0, "defect_rate": 1.0, "code_quality": 0.7167, ...}
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, 4 .ts files) | 308 |
| Files (excl. node_modules/logs) | 14 |
| Dependencies (prod + dev) | 4 |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] One test binds `fixture(t)` without `await`, inconsistent with sibling tests (`app.test.ts:115`) — harmless (fixture is synchronous)
2. [info] Error handling exceeds spec: 413/415/parse-failure mapping, `x-powered-by` disabled (`app.ts:32,73-84`)
3. [info] Parameterized queries + explicit SQL-injection-as-data test (`store.ts:31`, `app.test.ts:85`)
4. [info] `?author=` filter is exact case-sensitive equality — documented in README, spec-compliant

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=typescript_model=gpt-6-astra_prompt=neutral/rep1"
cat scores.json            # stored mechanical scores (build/test not re-run)
cat ../../REQUIREMENTS.json # pinned 12-requirement checklist
# to actually run: npm ci && npm test
```
