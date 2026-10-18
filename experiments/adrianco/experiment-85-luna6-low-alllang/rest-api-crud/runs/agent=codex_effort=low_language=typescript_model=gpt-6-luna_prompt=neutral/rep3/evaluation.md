# Evaluation: agent=codex effort=low language=typescript model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests ran green; not re-run)
- **Lint:** pass — code_quality=0.733 from scores.json (not re-run)
- **Architecture:** `run-summary` skill unavailable in this session — see inline notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 low, 2 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant denominator, 12 total).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/server.ts:36-42`, `src/books.ts:45-49` — INSERT with all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/server.ts:35`, `src/books.ts:34-39` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/server.ts:35` passes `author` param; `src/books.ts:36` `WHERE author = ?` |
| R4 | GET /books/{id} single by id (404 if absent) | ✓ implemented | `src/server.ts:46-49` — 200 or 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/server.ts:50-57`, `src/books.ts:51-55` — 404 on miss |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/server.ts:58`, `src/books.ts:57-59` — 200/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/books.ts:1,22` — `node:sqlite` `DatabaseSync`, persisted table |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `src/server.ts:6-9` JSON writer; 201/200/400/404/413/500 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `src/server.ts:23-24` — 400 on missing/blank title or author |
| R10 | GET /health health-check | ✓ implemented | `src/server.ts:34` — returns `{status:'ok'}` 200 |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Setup, Run, Endpoints, Tests sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test/books.test.ts` — 3 `test()` blocks; test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (gate ran during `retort run`); toolchain not re-run per skill guidance.

```text
scores.json
test_coverage = 1.0   (build + all tests passed)
defect_rate   = 1.0   (build+test succeeded)
code_quality  = 0.733
maintainability = 0.828
idiomatic     = 0.6
```

```text
npm test  -> tsx --test test/*.test.ts
3 tests, 0 skipped — health check; full CRUD + author filter round-trip; validation + 404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 132 (src/books.ts 62 + src/server.ts 70) |
| Test LOC | 48 |
| Files (source + test) | 3 |
| Dependencies | 3 (all devDependencies: @types/node, tsx, typescript — zero runtime deps) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`. No critical/high findings.

1. [low] ?author= filter is only weakly tested — single-book length assertion would pass even for a no-op filter (`test/books.test.ts:36`)
2. [info] PUT /books/{id} 404 path is untested (`test/books.test.ts`)
3. [info] Redundant year type guard — `typeof input.year !== 'number'` is dead after `Number.isInteger` (`src/server.ts:25`)

Notable strengths: zero runtime dependencies (Node built-in HTTP + `node:sqlite`), clean separation of store (`books.ts`) and routing (`server.ts`), parameterized SQL, body-size guard, testable `createApp(bookStore)` injection seam.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=typescript_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                         # build/test/lint scores (not re-run)
grep -rEc "\.skip\(|xit\(|it\.todo\(" test src   # skip count = 0
wc -l src/*.ts test/*.ts                # LOC
# to actually re-run: npm install && npm test
```
