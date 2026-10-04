# Evaluation: agent=codex effort=default language=typescript model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default, framework=unknown (express+better-sqlite3)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from scores.json (build + all tests passed)
- **Build:** pass — from `test_coverage=1.0` (scores.json); not re-run per skill
- **Lint:** n/a — `code_quality=0.733` from scores.json
- **Architecture:** summary skill unavailable (run-summary not registered); see inline notes below
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:29-35` INSERT + returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:37-43` SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:38-41` WHERE author = ?; test `tests/books.test.ts:21` |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `src/app.ts:45-48` findBook → 200/404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:50-59` UPDATE → 200/404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:61-66` DELETE → 204/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/app.ts:2,14-22` better-sqlite3, CREATE TABLE books |
| R8 | JSON responses with correct status codes | ✓ implemented | 201/200/404/400/204 across `src/app.ts:27-66` |
| R9 | Validation: title and author required | ✓ implemented | `src/app.ts:75-87` parseBookInput; test `tests/books.test.ts:26-30` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:27` returns `{status:'ok'}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` Setup/Run/Build-and-test sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 tests in `tests/books.test.ts`; `test_coverage=1.0` |

No prompt-factor requirements: `prompt=neutral` is the neutral baseline (no extra checkable instructions beyond TASK.md).

## Build & Test

Not re-run — stored mechanical scores are authoritative per the evaluate-run skill.

```text
scores.json
test_coverage = 1.0   (build succeeded + all tests passed; test gate)
defect_rate   = 1.0   (build+test succeeded)
code_quality  = 0.7333
maintainability = 0.8614
idiomatic     = 0.76
token_efficiency = 0.0143
```

```text
vitest run  (as configured in package.json "test")
4 tests, 0 skipped — supertest integration tests over an in-memory better-sqlite3 DB
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 144 (app 95, server 4, tests 45) |
| Files (excl. node_modules) | 14 |
| Dependencies (prod+dev) | 10 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 pinned requirements are implemented with test evidence, no tests are skipped, and the build+test gate passed (`test_coverage=1.0`). `findings.jsonl` is empty.

## Notes

- Clean, idiomatic Express 5 + better-sqlite3 implementation. `createApp(db)` dependency injection makes the app testable with an in-memory DB (`tests/books.test.ts:8-11`).
- Input validation trims and rejects blank title/author, and type-checks optional `year`/`isbn` (`src/app.ts:75-87`).
- PUT is a full-field replace (requires title+author, 400 otherwise) — a reasonable REST PUT semantics, not a defect.
- Error middleware maps malformed JSON bodies to 400 (`src/app.ts:68-71`).

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (test_coverage=1.0)
grep -rEc "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests --include="*.ts"   # 0 skips
# Optional full re-run (not required; slow):
# npm install && npm run build && npm test
```
