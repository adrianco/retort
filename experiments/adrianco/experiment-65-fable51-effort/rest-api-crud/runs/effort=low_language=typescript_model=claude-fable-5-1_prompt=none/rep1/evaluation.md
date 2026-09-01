# Evaluation: effort=low_language=typescript_model=claude-fable-5-1_prompt=none · rep 1

## Summary

- **Factors:** language=typescript, model=claude-fable-5-1, effort=low, prompt=none, agent=unknown, framework=unknown (Express + node:sqlite)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — from test_coverage=1.0
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** unavailable — no linter configured; code_quality=0.733 from scores.json
- **Architecture:** summary skill unavailable — see below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:13-17`, `src/db.ts:38-44` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:19-22`, `src/db.ts:52` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:20`, `src/db.ts:47-51` (WHERE author=?) |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/app.ts:24-29` returns 404 when not found |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:31-39`, `src/db.ts:61-67` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:41-47` (204/404), `src/db.ts:69-71` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts:5` node:sqlite, real table at `src/db.ts:27-35` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400/204 across `src/app.ts` |
| R9 | Validation: title & author required | ✓ implemented | `src/validation.ts:14-18`, test `tests/books.test.ts:33-37` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:9-11`, test `tests/books.test.ts:17-22` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` (Requirements/Setup/Run sections) |
| R12 | >= 3 unit/integration tests | ✓ implemented | 10 `it(...)` in `tests/books.test.ts`; test_coverage=1.0 |

## Build & Test

```text
# Not re-run — stored scores read from scores.json
test_coverage = 1.0   ⇒ npm build + `vitest run` succeeded, all tests passed
defect_rate   = 1.0   ⇒ build+test success
code_quality  = 0.733
maintainability = 0.757
idiomatic     = 0.70
```

Skip scan (`grep .skip(|xit(|xdescribe(|it.todo(`) → 0 skipped tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 297 |
| Files (src + tests) | 5 |
| Dependencies (prod + dev) | 8 |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both are informational:

1. [info] SQLite via built-in node:sqlite (no native dep) — satisfies R7
2. [info] Server uses on-disk books.db; tests use :memory: — clean prod/test separation

## Architecture

`run-summary` skill not available in this session. Structure is small and self-evident:
`src/db.ts` (BookRepository over node:sqlite) → `src/app.ts` (Express routes + validation +
error middleware) → `src/server.ts` (bootstrap). `src/validation.ts` isolates input checks;
`tests/books.test.ts` exercises every route via supertest against an in-memory DB.

## Reproduce

```bash
cd "experiments/adrianco/experiment-65-fable51-effort/rest-api-crud/runs/effort=low_language=typescript_model=claude-fable-5-1_prompt=none/rep1"
cat scores.json            # stored build/test/quality scores (test_coverage=1.0)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests src --include="*.ts" | wc -l   # 0
npm install && npm test    # optional re-verify: vitest run
```
