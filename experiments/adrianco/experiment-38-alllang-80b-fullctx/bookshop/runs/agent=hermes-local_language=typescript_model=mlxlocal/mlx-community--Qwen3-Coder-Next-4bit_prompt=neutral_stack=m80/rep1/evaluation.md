# Evaluation: agent=hermes-local language=typescript model=Qwen3-Coder-Next-4bit prompt=neutral stack=m80 · rep 1

## Summary

- **Factors:** language=typescript, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok — full pass. All 12 pinned requirements implemented; build + tests pass.
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 35 passed / 0 failed / 0 skipped (35 effective) — `defect_rate=1.0`, `test_coverage=0.8724` from `scores.json`
- **Build:** pass — `tsc` (test gate ran build+tests; `defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.7333` from `scores.json`
- **Architecture:** run-summary skill unavailable in this session — layered Express app (server → controllers → services → database) with validation middleware; see file list below.
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/controllers/BookController.ts:33` → `src/database.ts:createBook`, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `BookController.getAllBooks` → `database.getAllBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookController.ts:29` reads `req.query.author`; `database.ts:getAllBooks` adds `WHERE author = ?` |
| R4 | GET /books/{id} single | ✓ implemented | `BookController.getBookById`, 404 when absent |
| R5 | PUT /books/{id} update | ✓ implemented | `BookController.updateBook` → `database.updateBook`, 404 when absent |
| R6 | DELETE /books/{id} | ✓ implemented | `BookController.deleteBook`, returns 204, 404 when absent |
| R7 | SQLite/embedded DB | ✓ implemented | `src/database.ts` uses `sqlite3`, `CREATE TABLE books`, file-backed `./books.db` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/204 across controllers; error middleware 500 |
| R9 | Validation: title & author required | ✓ implemented | `src/middleware/validation.ts:validateCreateBook` (rejects missing title/author with 400) — note: also mandates year/isbn, stricter than spec (see findings) |
| R10 | GET /health | ✓ implemented | `src/controllers/HealthController.ts` returns `{status:'healthy'}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — install/build/run/test + curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 35 `it()` across unit/integration/validation test files; `test_coverage=0.8724` |

## Build & Test

Scores read from `scores.json` (mechanical scorers already ran the toolchain — not re-run):

```text
test_coverage   = 0.8724   (build + tests executed; jest coverage fraction)
defect_rate     = 1.0      (build + test succeeded)
code_quality    = 0.7333
token_efficiency= 1.0
maintainability = 0.5951
idiomatic       = 0.42
```

Test files: `tests/unit.test.ts` (11 `it`), `tests/integration.test.ts` (12 `it`), `tests/validation.test.ts` (12 `it`). No `.skip`/`xit`/`it.todo` present (the `xit(` grep hit is a false positive on `process.exit(` in `src/server.ts:48`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+tests .ts) | 1014 |
| Files (excl. node_modules/dist) | 27 |
| Dependencies (deps+devDeps) | 13 |
| Tests total | 35 |
| Tests effective | 35 |
| Skip ratio | 0% |
| Build | pass |

## Findings

Full list in `findings.jsonl`. None are high or critical.

1. [medium] Integration-test DB-swap is dead code — `app.get('bookService')` returns undefined (server never calls `app.set`), so integration tests run against the shared file DB `./books.db` with no per-test isolation (`tests/integration.test.ts:20`).
2. [medium] Create validation is stricter than spec — requires `year` and `isbn`, though TASK.md only mandates title/author (`src/middleware/validation.ts:26-37`).
3. [low] README project-structure diagram references `src/database/database.ts`, which does not exist.
4. [low] Unused express type imports in `src/services/BookService.ts:1`.

## Reproduce

```bash
cd experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1
cat scores.json                       # stored mechanical scores (no re-run)
cat ../../../../REQUIREMENTS.json      # pinned 12-requirement checklist
grep -rnE "\.skip\(|xit\(|it\.todo\(" tests   # skip audit
find src tests -name '*.ts' | xargs wc -l     # LOC
```
