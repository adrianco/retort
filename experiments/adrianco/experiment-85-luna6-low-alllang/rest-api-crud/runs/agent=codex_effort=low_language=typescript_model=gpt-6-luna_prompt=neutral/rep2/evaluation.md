# Evaluation: agent=codex effort=low language=typescript model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown (Node built-in `http` + `node:sqlite`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `scores.json` (`test_coverage=1.0`, `defect_rate=1.0`); agent log shows `npm run build` exit 0
- **Lint:** n/a — no linter configured; quality proxy `code_quality=0.733` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session; summary not generated. Structure is 2 source files + 1 test file (see Metrics).
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:49-56` INSERT + 201 with persisted row |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:41-46` `SELECT * FROM books ORDER BY id` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:42-44` `WHERE author LIKE ? COLLATE NOCASE`; test `books.test.ts:51-53` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/app.ts:61-63`; test `books.test.ts:54-55` (999 → 404) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:65-71` UPDATE, 404 on no change; test `books.test.ts:63-65` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:73-78` DELETE → 204, 404 on no change; test `books.test.ts:66-67` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/app.ts:2,15-21` `node:sqlite` `DatabaseSync`, real table |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `sendJson` `src/app.ts:104-107`; 201/200/204/400/404/500 used throughout |
| R9 | Input validation: title and author required | ✓ implemented | `parseBook` `src/app.ts:83-97` → 400; test `books.test.ts:37` (missing author → 400) |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/app.ts:38` → `{status:'ok'}`; test `books.test.ts:29-32` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:5-20` Setup/Run/Tests sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 tests in `tests/books.test.ts`; `test_coverage=1.0` |

## Build & Test

```text
npm run build   # node --experimental-strip-types --check src/{server,app}.ts
exit 0  (agent stdout log, item_33)
```

```text
npm test        # node --experimental-strip-types --test tests/*.test.ts
✔ health endpoint reports healthy
✔ creates books and validates required title and author
✔ lists books with an author filter and fetches one by ID
✔ updates and deletes a book
ℹ tests 4   ℹ pass 4   ℹ fail 0   ℹ skipped 0
```

Scores read from `scores.json` (not re-run): `test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.733`, `maintainability=0.880`, `idiomatic=0.62`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 208 (app.ts 120, server.ts 19, tests 69) |
| Files (excl. node_modules/.git) | 14 (incl. config/lock/README) |
| Source files | 3 (2 src + 1 test) |
| Dependencies | 2 (both devDeps: @types/node, typescript); 0 runtime deps |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build | pass (exit 0) |

## Findings

Full list in `findings.jsonl`. No critical/high/medium/low findings. Both are informational:

1. [info] PUT performs full replacement, not partial update (spec-conformant for R5)
2. [info] ?author= filter is a case-insensitive substring (LIKE) match (satisfies R3)

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=typescript_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json            # stored mechanical scores (no re-run)
npm test                   # 4/4 pass
npm run build              # exit 0
grep -rnE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests --include="*.ts"   # 0 real skips
```

Note: the `xit\(` pattern matches `process.exit(` in `src/server.ts:14`; that is a false positive, not a skipped test.
