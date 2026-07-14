# Evaluation: agent=hermes-local language=typescript prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-local, framework=unknown (Express), prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass — from scores.json (defect_rate=1.0, test_coverage=0.7837 ⇒ build + all tests ran green)
- **Lint:** pass — code_quality=0.7333 (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Pinned checklist `REQUIREMENTS.json` (12 requirements) used as the complete, fixed list. Prompt factor is `neutral` (`prompts/neutral.md` prescribes no methodology, only that tests demonstrate the requirements) — no additional `P*` requirements.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title,author,year,isbn) | ✓ implemented | `src/app.ts:21` → `db.createBook` `src/database.ts:67`; test `should create a new book with all fields` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:50`; `db.getAllBooks` `src/database.ts:85`; test `should return all books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:52-53`; `WHERE author = ?` `src/database.ts:87`; test `should filter books by author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/app.ts:61`, 404 at `:69`; tests `should return a book by ID`, `404 for non-existent book` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:79`; `db.updateBook` `src/database.ts:99`; test `should update a book partially` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:136`; `db.deleteBook` `src/database.ts:139`; test `should delete a book` |
| R7 | Data stored in SQLite | ✓ implemented | `src/database.ts:1,15` uses `sqlite3`; disk-backed `DB_PATH` `src/app.ts:7` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/400/404/409/500 throughout `src/app.ts`; all handlers `res.json` |
| R9 | Validation: title and author required | ✓ implemented | `src/app.ts:26-31`; tests `400 when title missing`, `400 when author missing` |
| R10 | GET /health endpoint | ✓ implemented | `src/app.ts:16`; test `should return health status` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — stack, install, run, API reference, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 17 tests in `tests/integration.test.ts` (test_coverage=0.7837 > 0) |

## Build & Test

Scores read from `scores.json` (inline gate — no `retort.db` row for this cell); build/test not re-run per skill guidance.

```text
scores.json
{"code_quality": 0.7333, "token_efficiency": 1.0, "test_coverage": 0.7837,
 "defect_rate": 1.0, "maintainability": 0.5269, "idiomatic": 0.82}
```

```text
defect_rate=1.0  ⇒ build succeeded and the test suite executed green
test_coverage=0.7837 ⇒ ~78% line coverage; 17 tests, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, src/) | 343 |
| Lines of code (tests) | 238 |
| Files (source + tests) | 3 |
| Dependencies (prod + dev) | 12 |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`) — none at or above `high`:

1. [low] POST /books requires year and isbn, stricter than the spec (`src/app.ts:32-37`)
2. [info] ?author= filter is exact, case-sensitive equality (`src/database.ts:87`)
3. [info] Line coverage ~78%; 500 error-handler branch unexercised (`src/app.ts:154-157`)

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=typescript_prompt=neutral/rep2
cat scores.json                                   # stored build/test/lint scores
grep -rEc "\b(it|test)\(" tests/ --include="*.ts" # 17 tests
npm install && npm run build && npm test          # optional: re-verify (scores already stored)
```
