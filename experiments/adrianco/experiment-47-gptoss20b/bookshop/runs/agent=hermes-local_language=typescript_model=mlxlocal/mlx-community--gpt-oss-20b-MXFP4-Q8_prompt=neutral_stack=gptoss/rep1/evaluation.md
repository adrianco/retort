# Evaluation: typescript · gpt-oss-20b-MXFP4-Q8 · hermes-local · rep 1

## Summary

- **Factors:** language=typescript, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok (REPAIR task — the prior attempt's build/tests did not pass; this attempt builds and all tests pass)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** n/a — no linter configured; code_quality=0.7333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/index.ts:24` INSERT then re-select, 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/index.ts:42` `SELECT * FROM books` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/index.ts:47` appends `WHERE author = ?` |
| R4 | GET /books/{id} single book | ✓ implemented | `src/index.ts:56` get-by-id, 404 if absent (`:60`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/index.ts:67` UPDATE, 404 if missing (`:75`) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/index.ts:91` DELETE, 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/database.ts:4` opens SQLite file, `books` table |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/204/400/404 across `src/index.ts` |
| R9 | Input validation: title & author required | ✓ implemented | `src/index.ts:26,70` return 400; test `:24` asserts it |
| R10 | GET /health endpoint | ✓ implemented | `src/index.ts:19` returns `{status:'ok'}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — install/start/test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `src/index.test.ts` — 3 tests; test_coverage=0.8939 |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run policy):

```text
test_coverage = 0.8939   # tests executed and passed (>0)
defect_rate   = 1.0      # build + test succeeded
code_quality  = 0.7333
maintainability = 0.6696
idiomatic     = 0.55
```

Test suite (`src/index.test.ts`, supertest against the Express app):
- `health endpoint returns ok`
- `create book validates required fields` (400 path)
- `full CRUD flow` (create → get → list → update → delete → verify 404)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 194 (index.ts 108, test 67, database.ts 19) |
| Files (excl. node_modules, lockfile) | 18 |
| Dependencies | 13 (4 runtime + 9 dev) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Full list in `findings.jsonl`:

1. [low] Tests seed `./test-books.db` but app defaults to `./books.db` — the app under test persists to `books.db`, so the seeding is effectively a no-op (`src/index.test.ts:7` vs `src/database.ts:4`).
2. [low] Integration tests persist to an on-disk SQLite file with no teardown — state can leak between runs (`src/index.ts:13`).

No critical/high/medium findings. This is a clean, spec-complete repair: all 12 requirements met, all tests pass.

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep1
cat scores.json                       # stored mechanical scores (build/test/quality)
grep -rEc "^\s*(test|it)\(" src/index.test.ts   # test count
grep -rE "\.skip\(|xit\(|xdescribe\(" src       # skip detection (0)
# build/test intentionally NOT re-run — see scores.json (defect_rate=1.0)
```
