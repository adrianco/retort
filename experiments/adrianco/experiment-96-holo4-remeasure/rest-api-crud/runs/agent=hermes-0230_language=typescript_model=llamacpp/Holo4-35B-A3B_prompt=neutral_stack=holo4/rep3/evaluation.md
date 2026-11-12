# Evaluation: agent=hermes-0230 language=typescript model=llamacpp/Holo4-35B-A3B prompt=neutral stack=holo4 · rep 3

## Summary

- **Factors:** language=typescript, model=llamacpp/Holo4-35B-A3B, agent=hermes-0230, prompt=neutral, stack=holo4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from `test_coverage=1.0`
- **Build:** pass — `tsc` compiles cleanly (scores.json, not re-run)
- **Lint:** pass — `code_quality=0.73` from scores.json
- **Architecture:** `run-summary` skill not invoked (not available this session); structure summarized inline below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 0 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/index.ts:14-44`, persists via `db.run INSERT`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/index.ts:47-51`, `src/database.ts:58-69` getBooks |
| R3 | GET /books ?author= filter | ✓ implemented | `src/index.ts:48`; `src/database.ts:60` `WHERE author = ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/index.ts:54-62`, 404 at line 59 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/index.ts:65-118`, partial-field update + 404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/index.ts:121-132`, 204 on success, 404 if absent |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `src/database.ts:1,18` sql.js Database, file persistence at `books.db` (export/writeFileSync) |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400/409/204 throughout `src/index.ts` |
| R9 | Validation: title and author required | ✓ implemented | `src/index.ts:17-22` reject 400 when title/author empty (also rejects year/isbn — see finding) |
| R10 | GET /health | ✓ implemented | `src/index.ts:9-11` returns `{status:'ok'}` 200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — endpoints, setup, run, test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `src/tests/run.ts` — 13 `it()` tests, supertest + node:test |

## Build & Test

Scores read from `scores.json` (gate-inline; not re-run per evaluate-run step 2):

```text
test_coverage = 1.0   → tsc build succeeded AND all tests passed
defect_rate   = 1.0   → build+test success
code_quality  = 0.733
maintainability = 0.816
idiomatic     = 0.62
```

```text
npm test  (ts-node src/tests/run.ts, node:test + supertest)
13 integration tests across /health, POST/GET/GET:id/PUT/DELETE — all passing, 0 skipped
(agent stdout claims "15 tests"; actual it() blocks = 13 — tests pass either way)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, non-test) | 237 |
| Lines of code (tests) | 140 |
| Files (excl. node_modules) | 19 |
| Dependencies (deps + devDeps) | 9 |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] POST /books validation stricter than spec — `src/index.ts:23-28` also requires `year` and `isbn` (400), but TASK.md only mandates title/author. Required validation still correct.

No build, test, skipped-test, or missing-requirement findings. Clean run.

## Architecture (inline)

- `src/index.ts` — Express app, all 6 CRUD routes + `/health`, inline validation, UNIQUE-isbn → 409 handling.
- `src/database.ts` — sql.js (embedded SQLite) wrapper: `init()` loads/creates `books.db`, `save()` exports to disk, `getBook`/`getBooks` query helpers.
- `src/types.ts` — `Book`, `CreateBookInput`, `UpdateBookInput` interfaces.
- `src/tests/run.ts` — 13 supertest integration tests over the Express app.

## Reproduce

```bash
cd "experiments/adrianco/experiment-96-holo4-remeasure/rest-api-crud/runs/agent=hermes-0230_language=typescript_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4/rep3"
cat scores.json                 # test_coverage=1.0 → build+tests passed
grep -rEc "\bit\(" src/tests/run.ts        # 13
grep -rEc "\.skip\(|xit\(|xdescribe\(" src # 0 skips
```
