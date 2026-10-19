# Evaluation: agent=hermes-0222_language=typescript_model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ_prompt=neutral_stack=tcap · rep 3

## Summary

- **Factors:** language=typescript, model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ, agent=hermes-0222, prompt=neutral, stack=tcap
- **Status:** ok (`_meta.json` succeeded=true)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`); prompt factor `neutral` adds P1 (include tests demonstrating the requirements) — implemented
- **Tests:** 41 defined / 0 skipped; test_coverage=1.0 from `scores.json` ⇒ build + all tests passed (41 effective)
- **Build:** pass (derived from test_coverage=1.0 / defect_rate=1.0; not re-run)
- **Lint:** code_quality=0.733 (scorer value; not re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books (title, author, year, isbn) | ✓ implemented | `src/app.ts:36` → `store.createBook` (`src/db.ts:76`); test "creates a book with all fields and returns 201" |
| R2 | GET /books lists all | ✓ implemented | `src/app.ts:47`, `src/db.ts:54`; test "lists all created books" |
| R3 | ?author= filter | ✓ implemented | `src/db.ts:57` `lower(author) = lower(?)`; tests "filters by author", "case-insensitive" |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `src/app.ts:67-76`; tests "returns the book by id", "404 for a non-existent id" |
| R5 | PUT /books/{id} | ✓ implemented | `src/app.ts:79-93`, `src/db.ts:90`; tests in `PUT /books/:id` block (partial semantics — see findings) |
| R6 | DELETE /books/{id} | ✓ implemented | `src/app.ts:96-105` (204/404); test "deletes a book (204) and it is gone afterwards" |
| R7 | SQLite storage | ✓ implemented | `src/db.ts:1,24-37` `node:sqlite` DatabaseSync, file `books.db` (`src/server.ts:7`) |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/204/400/404/500 across `src/app.ts`; JSON 404 fallback `:108`, JSON parse error handler `:113` |
| R9 | title/author required | ✓ implemented | `src/validation.ts:35-57`; tests "rejects a missing title/author with 400" |
| R10 | GET /health | ✓ implemented | `src/app.ts:15`; test "GET /health returns 200 with status ok" |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup / Run / Tests / Endpoints sections |
| R12 | ≥3 tests | ✓ implemented | 41 tests in `tests/books.test.ts` (28) + `tests/validation.test.ts` (13); test_coverage=1.0 |
| P1 | Tests demonstrate requirements (neutral prompt) | ✓ implemented | every route has supertest integration coverage |

Enhancements beyond spec: ISBN-10/13 format validation, year range checks, length limits, `GET /` service info, positive-integer id validation, malformed-JSON 400 handler, DB-handle injection for `:memory:` tests.

## Build & Test

```text
(not re-run — per skill, stored scores used)
scores.json: {"code_quality": 0.7333, "token_efficiency": 0.0104, "test_coverage": 1.0,
              "defect_rate": 1.0, "maintainability": 0.8386, "idiomatic": 0.8}
```

```text
test command: npm test  (vitest run)
41 tests defined, 0 skip/todo/xit markers (grep of tests/*.ts)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 370 (src/*.ts) |
| Lines of test code | 360 |
| Files (excl. harness/_judge/summary) | 12 |
| Dependencies | 8 (1 runtime: express; 7 dev) |
| Tests total | 41 |
| Tests effective | 41 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`:

1. [low] ISBN validation checks shape only, not the check digit (`src/validation.ts:81-83`)
2. [low] Mechanical code_quality score 0.733 (`scores.json`)
3. [info] PUT has PATCH (partial-update) semantics (`src/app.ts:82`)

## Reproduce

```bash
cd <run_dir>
cat scores.json
grep -nE "^\s*(it|test)\(|\.skip\(|xit\(|\.todo\(" tests/*.ts
npm install && npm test   # optional; not run for this evaluation
```
