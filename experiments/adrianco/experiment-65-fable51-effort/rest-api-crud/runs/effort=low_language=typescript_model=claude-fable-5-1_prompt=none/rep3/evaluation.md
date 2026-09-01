# Evaluation: effort=low_language=typescript_model=claude-fable-5-1_prompt=none · rep 3

## Summary

- **Factors:** language=typescript, model=claude-fable-5-1, prompt=none, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — from test_coverage=1.0 in scores.json
- **Build:** pass — from test_coverage=1.0 (build+test gate) in scores.json (not re-run)
- **Lint:** pass — code_quality=0.733 in scores.json
- **Architecture:** run-summary skill not available in this session — see Architecture note below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:20` POST route → `repo.create`; `src/db.ts:47` INSERT with 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:15` → `repo.list`; `src/db.ts:39` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:16` reads query.author; `src/db.ts:34` WHERE author = ? |
| R4 | GET /books/{id} single book (404 absent) | ✓ implemented | `src/app.ts:28` returns 404 when `repo.get` empty |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:41` → `repo.update`; `src/db.ts:53` UPDATE, 404 on 0 changes |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:63` → `repo.delete` returns 204/404 |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `src/db.ts:1` `node:sqlite` DatabaseSync; file DB via DB_PATH (default books.db) |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/204/400/404/500 across `src/app.ts`; error middleware `src/app.ts:80` |
| R9 | Validation: title and author required | ✓ implemented | `src/validation.ts:22-27` reject empty title/author → 400 |
| R10 | GET /health | ✓ implemented | `src/app.ts:11` returns `{status:'ok'}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` has Requirements/Setup/Run/Endpoints/Layout |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 10 `it` cases, all pass (test_coverage=1.0) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage = 1.0   → build succeeded + all tests passed
code_quality  = 0.733
defect_rate   = 1.0    → build+test succeeded
maintainability = 0.621
idiomatic     = 0.81
```

Test command (for reference): `npm test` (vitest run), 10 cases in `tests/books.test.ts`
covering health, create (+validation, +non-integer year, +malformed JSON), list+filter,
get-by-id (200/404/400), update (200/404/400), delete (204→404).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 350 |
| Source files | 5 (src/) + 1 (tests/) |
| Dependencies | 7 (1 runtime: express; 6 dev) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`. No critical/high/medium/low findings — clean run.

1. [info] Persistence uses Node's experimental `node:sqlite` module (satisfies R7 without native deps)
2. [info] Full JSON status-code coverage including 400 for malformed JSON and invalid ids (exceeds spec)

## Architecture

The `run-summary` skill was not available in this session, so `summary/` was not generated.
Structure (from source read): `db.ts` (BookRepository over node:sqlite), `validation.ts`
(validateBook + parseId), `app.ts` (Express factory `createApp(repo)` wiring all routes +
error middleware), `server.ts` (entry point, DB path/port from env, graceful shutdown).
Clean separation of persistence / validation / routing; app is injected with the repo,
enabling in-memory DB per test.

## Reproduce

```bash
cd "experiments/adrianco/experiment-65-fable51-effort/rest-api-crud/runs/effort=low_language=typescript_model=claude-fable-5-1_prompt=none/rep3"
cat scores.json                                   # mechanical scores (build/test/lint)
npm install && npm test                           # re-run tests (vitest, 10 cases)
grep -rEn "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests --include="*.ts"   # skip check
```
