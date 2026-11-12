# Evaluation: rest-api-crud · effort=low language=typescript model=claude-fable-5-2 prompt=none · rep 1

## Summary

- **Factors:** language=typescript, model=claude-fable-5-2, effort=low, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `tsc` compiled (test gate `test_coverage=1.0` ⇒ build + all tests ran)
- **Lint:** pass — `code_quality=0.733` from `scores.json`
- **Architecture:** `run-summary` skill not available in this session; summarized inline below.
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:43-47` → `BookStore.create` `src/db.ts:27-32`; test `src/../tests/api.test.ts:36` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:49-52` → `store.list()` `src/db.ts:34-39`; test `tests/api.test.ts:63` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:50`; `src/db.ts:37` `WHERE author = ? COLLATE NOCASE`; test `tests/api.test.ts:68` |
| R4 | GET /books/{id} returns a single book (404 if absent) | ✓ implemented | `src/app.ts:54-59`; 404 at `:57`; test `tests/api.test.ts:43,85` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:61-67` → `store.update` `src/db.ts:45-50`; test `tests/api.test.ts:72` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:69-73` → `store.delete` `src/db.ts:52-54`; test `tests/api.test.ts:82` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts:1,16-25` `node:sqlite` `DatabaseSync` + persistent `books.db` default `src/server.ts:5` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 `:46`, 200 json `:51,58`, 404 `:57,63,71`, 400 `:45,65,80`, 204 `:72` |
| R9 | Input validation: title & author required | ✓ implemented | `src/app.ts:11-12` (rejects empty/whitespace); test `tests/api.test.ts:48-56` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:39-41` returns `{status:"ok"}`; test `tests/api.test.ts:30` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — setup, run, env vars, endpoints, example |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 tests in `tests/api.test.ts`; `test_coverage=1.0` |

## Build & Test

Not re-run — stored mechanical scores used per skill step 2.

```text
scores.json
test_coverage = 1.0   → build (tsc) + all tests passed
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.733 → lint/quality (Lint: pass)
```

Skip scan (`.skip(`/`xit(`/`xdescribe(`/`it.todo(`): 0 skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 242 (src 154 + tests 88) |
| Files | 16 (incl. package-lock, tsconfig) |
| Dependencies | 4 (express + 3 dev: @types/express, @types/node, typescript) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Architecture (inline)

Three small modules, clean separation:
- `src/db.ts` — `BookStore` wraps `node:sqlite` `DatabaseSync` with parameterized prepared statements for CRUD; `:memory:` for tests, file-backed in production.
- `src/app.ts` — `createApp(store)` builds the Express 5 app: `validateBook` normalizer, the 6 routes + `/health`, a JSON 404 fallthrough, and a JSON-parse/error middleware.
- `src/server.ts` — thin entrypoint; wires `BookStore` to `createApp().listen()`, configurable via `PORT`/`DB_PATH`.
- `tests/api.test.ts` — `node:test` integration tests over a random-port server + in-memory store.

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Robust JSON-parse + 404 fallthrough error handling beyond spec — `src/app.ts:75-83`
2. [info] Uses Node built-in `node:sqlite` (no native add-on) for persistence — `src/db.ts:1`

No requirement gaps, build/test failures, or skipped tests. A clean, fully-conformant run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-94-fable52-screen/rest-api-crud/runs/effort=low_language=typescript_model=claude-fable-5-2_prompt=none/rep1"
cat scores.json                       # stored mechanical scores (no re-run)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts" | grep -v node_modules | wc -l
# Full re-run (optional): npm install && npm test
```
