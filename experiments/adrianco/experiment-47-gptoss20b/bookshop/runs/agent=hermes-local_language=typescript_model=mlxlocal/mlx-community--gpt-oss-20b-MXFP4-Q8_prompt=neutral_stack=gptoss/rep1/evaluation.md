# Evaluation: typescript · gpt-oss-20b-MXFP4-Q8 · neutral · gptoss · rep 1

## Summary

- **Factors:** language=typescript, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok (repair task — the previous attempt was already correct; agent made no changes and reported "No further changes needed")
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (build+test gate succeeded; not re-run)
- **Lint:** pass — `code_quality=0.733` in scores.json
- **Architecture:** inline below (3-file codebase; run-summary not spawned)
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/index.ts:24-39` INSERT with 4 fields, 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/index.ts:42-53` `SELECT * FROM books` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/index.ts:47-50` `WHERE author = ?` (untested — see findings) |
| R4 | GET /books/{id} single book | ✓ implemented | `src/index.ts:56-64` 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/index.ts:67-88` UPDATE, 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/index.ts:91-100` DELETE, 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `src/database.ts:1-18` sqlite3 + sqlite `open()` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204 across `src/index.ts` |
| R9 | Validation: title & author required | ✓ implemented | `src/index.ts:26-28,70-72` 400 when missing |
| R10 | GET /health | ✓ implemented | `src/index.ts:19-21` returns `{status:'ok'}` |
| R11 | README with setup/run | ✓ implemented | `README.md` install/start/test sections |
| R12 | ≥3 tests | ✓ implemented | `src/index.test.ts` 3 tests, all pass (`defect_rate=1.0`) |

## Build & Test

Not re-run — stored scores from `scores.json` stand in for the toolchain (per evaluate-run skill step 2):

```text
scores.json: test_coverage=0.8939  defect_rate=1.0  code_quality=0.7333
             maintainability=0.6696  idiomatic=0.55  token_efficiency=0.0051
_agent_stdout.log: "All tests pass. ... No further changes needed."
```

`defect_rate=1.0` ⇒ build compiled and all 3 tests passed. `test_coverage=0.8939` is the
jest coverage fraction (not the 0/1 execution gate).

## Architecture (inline)

- `src/database.ts` — `getDb(path='./books.db')` opens a sqlite connection via the `sqlite`
  promise wrapper over `sqlite3` and ensures the `books` table (id/title/author/year/isbn).
- `src/index.ts` — Express app; lazy-initializes one shared db promise (`initDb`), defines the
  6 routes + `/health`, exports `app` and only `listen`s when run as main (enables supertest).
- `src/index.test.ts` — supertest suite: health, validation-400, and a full create→get→list→
  update→delete→404 CRUD flow.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, excl. test) | 127 (index 108 + database 19) |
| Test LOC | 67 |
| Files (src) | 3 |
| Dependencies (package.json) | 13 |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build/test | pass (from scores.json) |

## Findings

Top items (full list in `findings.jsonl`):

1. [medium] Tests don't isolate the DB — app uses `./books.db`, test setup clears `./test-books.db`; the app under test never touches the reset DB (`src/index.test.ts:7` vs `src/database.ts:4`).
2. [low] `?author=` filter (R3) implemented but not exercised by any test.
3. [low] Running app/tests writes `books.db` into the workspace root (relative default path, no gitignore).
4. [info] README omits an endpoint reference (R11 still satisfied).

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep1
cat scores.json          # stored build/test/lint scores (not re-run)
grep -rnE "\.skip\(|xit\(" src   # 0 skips
# tests: npm install && npm test   (would rebuild — avoided; defect_rate=1.0 already recorded)
```
