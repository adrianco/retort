# Evaluation: agent=hermes-0205 · language=typescript · model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ · prompt=neutral · stack=dwq4 · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-0205, model=`mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ`, prompt=neutral, stack=dwq4, framework=unknown
- **Run status:** `_meta.json` says `succeeded: true`, DB row 14 says `status=completed`, `_second_try=1.0` — this was a **REPAIR run** (TASK.md is the repair wrapper; `FEEDBACK.md` demanded "all tests run and pass").
- **Verdict:** **FAILED the test gate.** The repair did not repair the thing it was asked to repair — 0 of 12 tests pass.
- **Requirements:** 12/12 implemented against the pinned `REQUIREMENTS.json` bar, 0 partial, 0 missing. (See the R12 note below — the pinned bar is deliberately lenient; the broken suite is carried as a critical finding, not as a requirement gap.)
- **Prompt-factor conformance (`prompts/neutral.md`):** **not met** — P1 asked for "tests that demonstrate the implementation meets the requirements"; the suite exists but never executes, so it demonstrates nothing.
- **Tests:** 0 passed / 12 failed / 0 skipped (12 effective)
- **Build:** pass (derived — `defect_rate=1.0` in `scores.json`; `npm start` takes the `require.main === module` path that *does* call `initDB()`)
- **Lint / quality:** `code_quality=0.40`, `idiomatic=0.00`, `maintainability=0.586` (from `scores.json`)
- **Architecture:** single-file Express app (`src/app.js`, 208 lines: 6 routes + `initDB()`), single Jest+supertest suite (`test/book-api.test.js`, 367 lines). Too small to warrant a separate `summary/` tree; `run-summary` not invoked.
- **Findings:** 7 items in `findings.jsonl` (1 critical, 0 high, 3 medium, 2 low, 1 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (found 3 levels up at `rest-api-crud/REQUIREMENTS.json`), used verbatim — 12 entries, fixed denominator.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.js:47-76` — destructures all four fields, `INSERT INTO books`, returns 201 with `this.lastID` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.js:79-101` — `SELECT * FROM books`, 200 + JSON array |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `src/app.js:86-89` — `WHERE author LIKE ?` bound to `%author%` (substring, not exact — see info finding `author-filter-substring`) |
| R4 | GET /books/{id} returns one book, 404 if absent | ✓ implemented | `src/app.js:104-124` — `db.get`, 404 at `:116`, 400 for non-numeric id at `:109` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.js:127-171` — existence check then `UPDATE books SET ...`, 200 with the updated body |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.js:174-196` — `DELETE FROM books`, 404 when `this.changes === 0` at `:186` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/app.js:9` — `new sqlite3.Database('./books.db')`, **file-backed** (not `:memory:`); schema with `NOT NULL` at `src/app.js:14-21` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | Every handler uses `res.status(n).json(...)`; 201 `:70`, 200 `:95`/`:118`/`:163`/`:189`, 400 `:53`/`:109`, 404 `:116`/`:142`/`:187`, 500 throughout |
| R9 | Validation: title and author required | ✓ implemented | `src/app.js:52-56` (POST) and `src/app.js:145-149` (PUT) → 400 `Title and author are required fields` |
| R10 | GET /health health check | ✓ implemented | `src/app.js:42-44` → 200 `{status:'OK', message:'Book API is running'}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:37-40` — `npm install`, `npm run dev`, port 3001 |
| R12 | ≥3 unit/integration tests | ✓ implemented **(pinned bar only)** | 12 tests in `test/book-api.test.js:32-367`; pinned `how_to_verify` is *"≥3 tests exist and run (test_coverage > 0)"* and `test_coverage=0.1444 > 0`. **But all 12 fail** — carried as the critical finding `test-suite-fails` rather than as a requirement gap, so `requirement_coverage` stays comparable across runs. |

### Prompt-factor requirements (`prompt=neutral` → `prompts/neutral.md`)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | "include tests that demonstrate the implementation meets the requirements" | ~ partial | 12 well-targeted tests exist (`test/book-api.test.js`) covering every route including 404/400 paths, but none executes — `beforeAll` throws before the first assertion. Nothing is demonstrated. |
| — | "No particular testing or development methodology is prescribed… whatever approach you judge best" | n/a | Imposes no checkable constraint. |

## Build & Test

Per the skill, build/test/lint were **not re-run** — the scorer's stored values are authoritative.

```text
$ cat scores.json
{"code_quality": 0.39999999999999997, "token_efficiency": 0.003961342139003798,
 "test_coverage": 0.1444, "defect_rate": 1.0,
 "maintainability": 0.585797545150387, "idiomatic": 0.0}
```

Cross-checked against `rest-api-crud/retort.db` (read-only copy), run_id 14, `status=completed`:

```text
code_quality|0.4          test_coverage|0.1444      defect_rate|1.0
maintainability|0.5858    idiomatic|0.0             requirement_coverage|1.0
_duration_seconds|1760.07 _turns|78                 _tokens|3306960
_max_context_tokens|69389 _second_try|1.0           _cost_usd|0.0
```

### Why `test_coverage=0.1444` means "every test failed", not "14% of tests passed"

0.1444 is Jest **statement coverage**, not a pass ratio (12 tests × 0.1444 is not an integer). The ~14% covered is exactly the module-load prologue of `src/app.js` — the two `require`s, the `initDB` declaration, `const app`, `const PORT`, `app.use`, the six route registrations, the `require.main` guard and `module.exports` (~13 of ~90 statements). Nothing inside any route body is covered, which is only possible if no request ever reached a handler.

The static cause is unambiguous:

```js
// src/app.js:5
let db;                                   // assigned ONLY inside initDB()
// src/app.js:199-207
if (require.main === module) { initDB().then(...) }   // never true under require()
// src/app.js:209
module.exports = { app, db, initDB };     // snapshots db === undefined
```

```js
// test/book-api.test.js:2,11
const { app, db } = require('../src/app');
beforeAll((done) => { db.serialize(() => { ... }) });  // TypeError: Cannot read properties of undefined
```

`beforeAll` throwing aborts the whole file, so all 12 tests fail. Even if `beforeAll` were removed, every handler would 500 — the route bodies read the same undefined `db`.

The agent knew: `README.md:43` — *"the automated test system had some issues with database initialization in test environments"* — and `_agent_stdout.log` still reports *"Implementation Complete ✅ … at least 3 unit/integration tests ✅"*.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 575 (`src/app.js` 208, `test/book-api.test.js` 367) |
| TypeScript files | 0 (cell is `language=typescript`) |
| Files (excl. node_modules/.git) | 32 |
| Dependencies (prod + dev) | 4 (express, sqlite3, jest, supertest) |
| Tests total | 12 |
| Tests effective (passed + failed) | 12 |
| Tests passed | 0 |
| Skipped / disabled tests | 0 (`grep -E "\.skip\(|xit\(|xdescribe\(|it\.todo\("` → 0) |
| Skip ratio | 0% |
| Statement coverage | 14.44% |
| Agent turns / tokens / wall-clock | 78 / 3,306,960 / 1760.1 s |
| Build duration | not measured (build not re-run) |

## Findings

Full list in `findings.jsonl`. Top 5 by severity:

1. **[critical] `test-suite-fails`** — All 12 tests fail: `module.exports` at `src/app.js:209` snapshots `db` while it is still `undefined` (assigned only in `initDB()`, `src/app.js:9`, which runs only under the `require.main` guard at `:199`), so `test/book-api.test.js:11`'s `db.serialize()` throws in `beforeAll`.
2. **[medium] `readme-overclaims`** — `README.md:7-20` marks all 12 requirements ✅ and `README.md:43-45` reduces a total suite failure to "some issues with database initialization"; `_agent_stdout.log` declares completion.
3. **[medium] `lang-mismatch`** — `stack.json` says `language: typescript`; there are zero `.ts` files, `tsconfig.json` is unused and there is no `typescript` dependency or build script (`idiomatic=0.0`).
4. **[medium] `test-db-is-prod-db`** — `test/book-api.test.js:6` declares an unused `testDbPath`; the suite instead `DELETE`s from the app's real `./books.db` (`test/book-api.test.js:12`).
5. **[low] `stmt-not-finalized`** — `db.prepare()` handles at `src/app.js:58` and `src/app.js:151` are never `finalize()`d.

Also: `[low] workspace-clutter` (8 unreferenced scratch scripts in the root) and `[info] author-filter-substring` (`LIKE %author%` rather than exact match).

### Note on the critical severity

A prior second-opinion pass on this run graded the broken suite `high`. I grade it **critical**: 100% of tests fail to execute, which is the same substantive condition the skill treats as an automatic gate failure ("tests did not execute"), and this was a REPAIR run whose sole assignment — per `FEEDBACK.md` — was to make the tests pass. `requirement_coverage` is unaffected (still 12/12 on the pinned bar); only `penalty_score` moves.

## Reproduce

```bash
cd "experiments/adrianco/experiment-69-dwq-generality/rest-api-crud/runs/agent=hermes-0205_language=typescript_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ_prompt=neutral_stack=dwq4/rep2"

cat scores.json                      # authoritative mechanical scores (no re-run)
cat ../../../../REQUIREMENTS.json    # pinned 12-requirement checklist
cat ../../../../prompts/neutral.md   # prompt-factor instructions (prompt=neutral)

sed -n '1,12p;195,209p' src/app.js           # the db-undefined defect
sed -n '1,15p' test/book-api.test.js         # beforeAll consuming the undefined db
sed -n '37,45p' README.md                    # setup instructions + the admission

grep -cE '^\s*(test|it)\(' test/book-api.test.js                      # 12
grep -rnE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' test/ src/ | wc -l  # 0
wc -l src/app.js test/book-api.test.js                                # 575
find . -name '*.ts' -not -path '*/node_modules/*' | wc -l             # 0

# cross-check against the DB (read-only copy; never write to retort.db)
cp ../../../../retort.db /tmp/r.db
sqlite3 /tmp/r.db "SELECT metric_name, value FROM run_results WHERE run_id=14;"
```
