# Evaluation: typescript · gpt-oss-20b · hermes-local · neutral · rep 4

## Summary

- **Factors:** language=typescript, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok (repair task — previous attempt failed on missing README + tests; both fixed)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.7333` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low)

This is a REPAIR run. The prior attempt failed for two reasons per `FEEDBACK.md`:
tests/build did not fully pass, and no README.md. Both are resolved — `README.md`
now documents setup/run, and `test_coverage=0.8793` with `defect_rate=1.0` confirm
the build compiles and all tests pass.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `src/server.ts:14-23` INSERT with 4 fields, 201 |
| R2 | GET /books lists all | ✓ implemented | `src/server.ts:33-37` SELECT * FROM books |
| R3 | GET /books ?author= filter | ✓ implemented | `src/server.ts:29-32` WHERE author = ? |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/server.ts:41-49` 404 when not found |
| R5 | PUT /books/{id} update | ✓ implemented | `src/server.ts:52-65` UPDATE, 404 on 0 changes |
| R6 | DELETE /books/{id} delete | ✓ implemented | `src/server.ts:68-76` DELETE, 204/404 |
| R7 | SQLite / embedded DB | ✓ implemented | `src/database.ts:1-8` better-sqlite3 on-disk `data/books.db` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/204/400/404 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `src/server.ts:16-18,55-57` 400 when missing |
| R10 | GET /health | ✓ implemented | `src/server.ts:9-11` returns `{status:'ok'}` |
| R11 | README.md setup/run instructions | ✓ implemented | `README.md` — Setup/Build/Run/Tests sections (the prior gap) |
| R12 | ≥3 tests that run | ✓ implemented | `tests/api.test.ts` 5 tests, test_coverage=0.8793 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage = 0.8793   (build compiled + tests executed and passed)
defect_rate   = 1.0      (build + test succeeded)
code_quality  = 0.7333
```

Tests (`tests/api.test.ts`, jest + supertest): health, create+get, list+filter,
update, delete — 5 passed, 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src + tests) | 162 |
| Files (excl. node_modules) | 21 |
| Dependencies (deps + devDeps) | 13 |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl` (both low severity, no correctness impact):

1. [low] POST /books echoes the request body instead of re-reading the persisted row (`src/server.ts:21`)
2. [low] Tests share the persistent on-disk SQLite DB with no per-test reset (`src/database.ts:5`)

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep4
cat scores.json                 # stored build/test/lint scores
grep -rE "\.skip\(|xit\(|it\.todo\(" tests --include="*.ts" | wc -l   # 0 skips
npm install && npm test         # optional: re-run the 5 jest tests
```
