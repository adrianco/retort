# Evaluation: language=typescript, model=claude-fable-5, prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=claude-fable-5, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass — code_quality=0.733 from scores.json (no lint gate run separately)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:14` INSERT + 201; test `test/books.test.ts:22` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:30`; test `test/books.test.ts:77` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:33` WHERE author=?; test `test/books.test.ts:86` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/app.ts:43`, 404 at :52; tests `:104`,`:113` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:59` UPDATE; test `test/books.test.ts:125` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:83`, 204/404; tests `:161`,`:171` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts:1` node:sqlite DatabaseSync, `books` table |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404 across `src/app.ts`; parseId 400 at :44 |
| R9 | Input validation: title and author required | ✓ implemented | `src/validation.ts:23-28`; test `test/books.test.ts:45` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:10`; test `test/books.test.ts:14` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` Setup/Run/Test sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 18 tests in `test/books.test.ts`; test_coverage=1.0 |

## Build & Test

```text
# Not re-run — scores read from scores.json (inline gate)
test_coverage = 1.0   ⇒ npm test (vitest run) built + passed all tests
defect_rate   = 1.0   ⇒ build+test succeeded
code_quality  = 0.733
idiomatic     = 0.88
maintainability = 0.778
```

```text
# vitest run — 18 tests across 6 describe blocks, 0 skipped
GET /health (1), POST /books (6), GET /books (3),
GET /books/:id (3), PUT /books/:id (3), DELETE /books/:id (2)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 200 (src) + 175 (test) = 375 |
| Files (src + test) | 5 |
| Dependencies | 8 (1 runtime: express; 7 dev) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from inline gate) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both are info-level:

1. [info] Relies on experimental `node:sqlite` module — keeps deps minimal, no native build.
2. [info] PUT requires a full valid body (full-replace semantics) — correct per spec.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-48-fable5-gaps/bookshop/runs/language=typescript_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                       # stored mechanical scores (build/test gate)
grep -rE "^\s*(it|test)\(" test/      # 18 tests
grep -rE "\.skip\(|xit\(|it\.todo\(" test/   # 0 skips
npm install && npm test               # (optional) vitest run
```
