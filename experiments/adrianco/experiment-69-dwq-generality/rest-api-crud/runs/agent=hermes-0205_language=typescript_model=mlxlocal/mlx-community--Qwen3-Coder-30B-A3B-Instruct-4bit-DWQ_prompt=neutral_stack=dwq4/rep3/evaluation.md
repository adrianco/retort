# Evaluation: agent=hermes-0205 · language=typescript · model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ · prompt=neutral · stack=dwq4 · rep 3

## Summary

- **Factors:** language=typescript, agent=hermes-0205, model=mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ, prompt=neutral, stack=dwq4, framework=unknown
- **Task type:** REPAIR — `TASK.md` is the repair variant; a prior attempt failed at requirement_coverage 0.92 (`FEEDBACK.md`). `_meta.json` records `succeeded: true`.
- **Status:** ok — build and tests succeeded (`defect_rate=1.0`, `test_coverage=0.8481` from `scores.json`)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned checklist from `REQUIREMENTS.json`)
- **Tests:** 14 declared, 0 skipped (14 effective); jest coverage 84.81%
- **Build:** pass — not re-run; `defect_rate=1.0` in `scores.json` means build+test succeeded
- **Lint:** not re-run — `code_quality=0.3999…` in `scores.json`
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 7 items in `findings.jsonl` (0 critical, 1 high, 4 medium, 2 low)

The pinned 12-requirement checklist is fully met, so the repair achieved what it was
asked to. The headline problem is orthogonal to the checklist: **the run declares
`language=typescript` and delivers plain CommonJS JavaScript**, which `REQUIREMENTS.json`
does not police but `TASK.md`'s technical constraints do. The mechanical scorers already
register it — `idiomatic=0.0`, `code_quality=0.40`, `maintainability=0.26`.

## Requirements

Checklist source: `REQUIREMENTS.json` (pinned, 12 entries, used verbatim). No `P*`
entries — `prompt=neutral` adds no extra checkable instructions beyond TASK.md.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.js:38-68` — destructures all four fields, parameterized INSERT at `:48-49`, re-reads by `this.lastID` and returns 201. Test `test.js:26-45`. |
| R2 | GET /books lists all books | ✓ implemented | `server.js:71-91` — `SELECT * FROM books`, `res.json(rows)` at `:89`. Test `test.js:77-98`. |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `server.js:72,77-80` — `WHERE author = ?` bound from `req.query.author`. Test `test.js:100-121` exists but is non-discriminating (see finding `test-weak-1`); the code itself is correct. |
| R4 | GET /books/{id} returns one book, 404 if absent | ✓ implemented | `server.js:94-113` — `db.get` by id, 404 at `:105-109`. Tests `test.js:125-147` and `:149-156`. |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.js:116-153` — parameterized UPDATE at `:127-128`, `this.changes === 0` → 404 at `:136-140`, returns the re-read row. Tests `test.js:160-191`, `:193-207`. |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.js:156-176` — parameterized DELETE, `this.changes === 0` → 404 at `:168-172`. Tests `test.js:238-259`, `:261-268`. |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `server.js:2,12-19` — `sqlite3.Database('./books.db')`, file-backed (not in-memory); schema at `:22-30`. `sqlite3@5.1.7` in `package-lock.json`. |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 `server.js:65`; 200 `:34,:89,:111,:150,:174`; 400 `:43,:122`; 404 `:106,:137,:169,:180`; 500 `:51,:60,:84,:99,:130,:146,:162,:188`. All bodies are `res.json(...)`. |
| R9 | Validation: title and author required | ✓ implemented | `server.js:42-46` (POST) and `:121-125` (PUT) return 400 before any DB access. Tests `test.js:47-59`, `:61-73`, `:209-234`. |
| R10 | GET /health health check | ✓ implemented | `server.js:33-35` — `200 {status:'healthy'}`. Test `test.js:15-22`. |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — endpoint list, `npm install`, `npm start`, `npm run dev`, `npm test`, database and Node-version notes. |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test.js` — 14 `it()` cases across 8 `describe` blocks; `test_coverage=0.8481 > 0` confirms they executed. |

**Enhancements beyond spec** (not deductions): a catch-all `404` for undefined routes
(`server.js:179-183`), an Express error-handling middleware (`:186-192`), the
import-safe `require.main === module` guard (`:195-199`) that makes supertest possible,
and 404-path tests for `GET`/`PUT`/`DELETE` that the spec never asked for.

**Not on the pinned checklist but required by TASK.md:** "Use the specified language and
framework". Express satisfies the framework half; the language half is not met — see
finding `lang-1`.

## Build & Test

Not re-run, per the skill's Step 2 — the scorers already ran the toolchain and stored
the results:

```text
$ cat scores.json
{"code_quality": 0.39999999999999997,
 "token_efficiency": 0.007171413026537097,
 "test_coverage": 0.8481000000000001,
 "defect_rate": 1.0,
 "maintainability": 0.26497967781863374,
 "idiomatic": 0.0}
```

Reading (`src/retort/scoring/scorers/test_coverage.py`): `test_coverage` is the parsed
coverage percentage — **84.81%** — with a pass-rate fallback only when no percentage is
emitted. A percentage was emitted, so jest ran to completion. `defect_rate=1.0` confirms
build+test succeeded. `idiomatic=0.0` is consistent with a `typescript` cell containing no
TypeScript.

Skip scan (Step 5):

```text
$ grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" --include="*.js" . | grep -v node_modules | wc -l
0
```

No skipped or disabled tests. `effective_tests = 14`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only: `server.js` + `test.js`) | 480 (200 + 280) |
| Files (excl. `node_modules/`, `.git/`) | 21 (5 authored source/doc, rest harness artifacts) |
| Dependencies | 4 (express 4.22.2, sqlite3 5.1.7, jest 29.7.0, supertest 6.3.4) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Coverage | 84.81% |
| Build duration | not measured (not re-run) |
| Agent API calls / total tokens | 30 / 1,045,819 (`.hermes_usage.json`) |

## Findings

All 7 in `findings.jsonl`; top 5 by severity:

1. **[high] `lang-1`** — `language=typescript` but the deliverable is plain CommonJS JavaScript (`server.js`, `test.js`); no `typescript` in `package-lock.json`, no tsconfig. TASK.md requires "Use the specified language". Sibling cells of this task did emit `.ts`, so this is the model's choice, not a harness limitation. `idiomatic=0.0` reflects it.
2. **[medium] `doc-1`** — `SUMMARY.md:5` claims TypeScript and `:22`/`:39` claim an in-memory database; `FINAL_SUMMARY.md:63` claims the specified language was used. All three are false against `server.js:1-3,12`.
3. **[medium] `test-iso-1`** — `test.js:9-12` `beforeEach` is a no-op and `server.js:12` uses a fixed `./books.db`, so rows accumulate across cases and across `npm test` runs.
4. **[medium] `test-weak-1`** — the `?author=` test (`test.js:100-121`) seeds only one author, so it passes even if the `WHERE` clause were removed.
5. **[medium] `leak-1`** — `db.prepare()` per request at `server.js:48,:127,:159` with no `finalize()` anywhere and no `db.close()`.

Also: `[low] id-validate-1` (unvalidated `:id` → 404 instead of 400) and `[low] db-path-1`
(hard-coded relative DB path; unused `path` import at `server.js:3`).

No security concerns: every statement is parameterized (`server.js:48,58,78,97,127,143,159`),
so there is no SQL-injection surface.

## Reproduce

```bash
cd "experiments/adrianco/experiment-69-dwq-generality/rest-api-crud/runs/agent=hermes-0205_language=typescript_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ_prompt=neutral_stack=dwq4/rep3"

cat stack.json _meta.json scores.json _effective_stack.json
cat REQUIREMENTS.json                      # pinned 12-requirement checklist (copied into the run dir)
grep -cE "^\s*(it|test)\(" test.js         # 14
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" --include="*.js" . | grep -v node_modules | wc -l   # 0
wc -l server.js test.js                    # 200 / 280
node -e "const p=require('./package.json');console.log(Object.keys({...p.dependencies,...p.devDependencies}).length)"  # 4
python3 -c "import json;d=json.load(open('package-lock.json'));print(d['packages'].get('node_modules/typescript','ABSENT'))"  # ABSENT
```

Build/test/lint were deliberately **not** re-run; the scores above come from
`scores.json`, written by retort's scorers during the run.
