# Evaluation: rest-api-crud · agent=codex effort=low language=typescript model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build+tests ran and passed)
- **Lint:** n/a — `code_quality=0.717` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session; see inline notes below
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.ts:60,68-70` INSERT, returns 201 with created row |
| R2 | GET /books lists all | ✓ implemented | `app.ts:42-47` SELECT all ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.ts:43-46` filters `WHERE author = ?`; test `api.test.ts:37` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `app.ts:52-54` returns row or 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.ts:60,72-73` UPDATE; 404 if missing (`:61`) |
| R6 | DELETE /books/{id} | ✓ implemented | `app.ts:56-58` DELETE, 404 if no rows changed |
| R7 | SQLite / embedded DB | ✓ implemented | `app.ts:2,34-35` `node:sqlite` `DatabaseSync`, real table |
| R8 | JSON responses + status codes | ✓ implemented | `app.ts:28-31` `send()`; 201/200/400/404/413/500 used |
| R9 | Validation: title & author required | ✓ implemented | `app.ts:9-10` reject blank/non-string → 400; test `:42-43` |
| R10 | GET /health | ✓ implemented | `app.ts:41` returns `{status:'ok'}`; test `:30` |
| R11 | README with setup/run | ✓ implemented | `README.md` documents install/build/start/test, env vars |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 `test(...)` blocks in `test/api.test.ts`; `test_coverage=1.0` |

No requirement is partial or missing. Enhancements beyond spec (not deductions): 1 MiB body-size guard (`app.ts:22`), PORT range validation (`server.ts:4`), DB closed on server close (`app.ts:82`), year/isbn type validation (`app.ts:11-12`).

## Build & Test

Build and tests were not re-run — stored mechanical scores are authoritative (per skill Step 2):

```text
scores.json: test_coverage=1.0, defect_rate=1.0  → `npm test` (tsc build + node --test) passed
             code_quality=0.717, maintainability=0.882, idiomatic=0.42
```

Test suite (`test/api.test.ts`), 3 tests, in-memory SQLite (`:memory:`), driven by a hand-rolled
request/response harness over `server.emit('request', …)`:
1. health + create + retrieve-by-id + author filter + list count
2. validation (missing title, blank author, bad year type, malformed JSON) → 400
3. update replaces fields, delete makes book 404, double-delete/PUT-after-delete → 404

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 149 (app 84, server 6, test 59) |
| Files | 14 |
| Dependencies | 2 (both devDependencies: `@types/node`, `typescript`) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | not separately measured (see `scores.json`) |

## Findings

None. All 12 pinned requirements implemented, build + tests pass (`test_coverage=1.0`),
no skipped/disabled tests, no build/test failures. `findings.jsonl` is empty.

## Reproduce

```bash
cd "experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=typescript_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json            # test_coverage=1.0 ⇒ build+tests passed (do not re-run)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts" | grep -v node_modules   # 0 skips
# Optional full re-run: npm install && npm test
```
