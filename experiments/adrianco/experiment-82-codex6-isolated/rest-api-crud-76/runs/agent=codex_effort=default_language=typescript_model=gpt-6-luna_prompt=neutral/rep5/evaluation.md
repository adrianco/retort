# Evaluation: agent=codex effort=default language=typescript model=gpt-6-luna prompt=neutral · rep 5

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default, framework=Express + node:sqlite
- **Status:** ok (repair task — previous attempt's failure was fixed)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from `test_coverage=1.0`
- **Build:** pass — `test_coverage=1.0` in scores.json (tsc + vitest ran; tests would not execute if build failed)
- **Lint:** n/a — `code_quality=0.7333` (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:30-38` INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:40-46` SELECT all |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:41-43` `WHERE author = ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/app.ts:48-52` 404 branch |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:54-62` UPDATE, 404 on no change |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:64-68` DELETE, 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts:1,11-20` `node:sqlite` DatabaseSync |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400/204/500 across `src/app.ts` |
| R9 | Validation: title & author required | ✓ implemented | `src/app.ts:7-22,32` `validateBook` → 400 |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:28` returns `{status:'ok'}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` setup, run, API, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/api.test.ts` 4 `it()` cases, all pass |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: {"code_quality": 0.7333, "token_efficiency": 0.00555,
              "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.8725, "idiomatic": 0.75}
```

`test_coverage=1.0` ⇒ `tsc` build + `vitest run` all passed (tests cannot execute
if the build fails). `defect_rate=1.0` corroborates build+test success.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 156 (app 75, db 21, server 6, tests 54) |
| Files (excl. node_modules) | 17 |
| Dependencies (prod + dev) | 8 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

No correctness, build, test, or requirement findings. Both items are info-level
observations (full list in `findings.jsonl`):

1. [info] PUT /books/:id is a full replace, not a partial patch — conformant with spec + README
2. [info] Error middleware maps malformed JSON → 400, other errors → 500 (defensive, beyond spec)

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep5"
cat scores.json                                   # mechanical scores (do not re-run build/test)
grep -rE "\.skip\(|xit\(|it\.todo\(" tests/       # skip check → 0
grep -rcE "^\s*it\(" tests/api.test.ts            # test count → 4
```
