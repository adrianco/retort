# Evaluation: agent=hermes-local language=typescript model=Qwen3-Coder-Next-4bit prompt=neutral stack=m80 · rep 3

## Summary

- **Factors:** language=typescript, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json; all functionally satisfied, one path-prefix deviation noted)
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass (test_coverage=1.0 ⇒ `tsc` build + jest passed, from scores.json)
- **Lint:** n/a — code_quality=0.73, idiomatic=0.42, maintainability=0.92 (from scores.json)
- **Architecture:** clean layered Express app — `server` → `routes` → `middleware`/`controllers` → `models` → `database` (sqlite3). run-summary skill not invocable in this session; summarized inline below.
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/routes/books.ts:15` → `controllers/books.ts:createBookHandler` → `models/book.ts:createBook` INSERT |
| R2 | GET /books lists all books | ✓ implemented | `routes/books.ts:13` → `getAllBooks` `SELECT * FROM books` (`models/book.ts:17`) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `controllers/books.ts:7` reads `req.query.author`; `models/book.ts:9` `WHERE author = ?` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `controllers/books.ts:15-33`; 404 path at :24; test at `books.test.ts:139` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `routes/books.ts:16` → `updateBook` (`models/book.ts:61`); 404 when `changes===0` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `routes/books.ts:17` → `deleteBook` (`models/book.ts:82`); 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `src/database.ts:17` `new sqlite3.Database('./books.db')`, real table DDL |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 create, 200 get/list, 204 delete, 400 invalid, 404 not-found across controllers |
| R9 | Validation: title and author required | ✓ implemented | `src/middleware/validation.ts:7-13`; tests `validation.test.ts:6,26` |
| R10 | GET /health health check | ✓ implemented | `routes/books.ts:8-10` returns `{status:'ok', timestamp}` (served at `/api/health`) |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — install/build/dev/start/test sections (endpoint paths inaccurate, see findings) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 17 tests across `tests/books.test.ts` (12) + `tests/validation.test.ts` (5); test_coverage=1.0 |

Deviation (not a missing requirement): all routes are namespaced under `/api` (`server.ts:13`), so the live paths are `/api/books`, `/api/health` rather than the spec's bare `/books`, `/health`. The pinned `how_to_verify` criteria (route exists and functions) are met and all 17 tests pass against the `/api/*` paths, so requirements count as implemented — but the prefix deviates from the literal spec and the README documents the unprefixed paths.

## Build & Test

```text
# Not re-run — read from scores.json (inline eval gate)
test_coverage = 1.0   ⇒ tsc build succeeded AND all jest tests passed
defect_rate   = 1.0   ⇒ build+test succeeded
```

```text
tests: 17 passed, 0 failed, 0 skipped
  tests/books.test.ts       — 12 integration tests (in-memory sqlite, supertest)
  tests/validation.test.ts  —  5 unit tests (validation middleware)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src + tests, .ts) | 606 |
| Files (excl. node_modules/.git) | 23 |
| Dependencies (package.json) | 13 |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] All endpoints mounted under `/api`, deviating from spec paths — `src/server.ts:13`
2. [medium] README documents `/books`/`/health` but implementation serves `/api/*` — `README.md:6-12` vs `src/server.ts:13`
3. [info] Year range validation (0–9999) added beyond spec — `src/middleware/validation.ts:15-20`

## Reproduce

```bash
cd "experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep3"
cat scores.json                         # stored build/test/quality scores (not re-run)
grep -rEc "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests/   # skip count = 0
grep -rEo "\bit\(" tests/ | wc -l        # 17 tests
grep -n "app.use('/api'" src/server.ts   # confirms /api prefix
```
