# Evaluation: agent=codex effort=default language=typescript model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, effort=default, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `test_coverage=1.0` in `scores.json` (`npm test` = `tsc` build + `node --test`)
- **Lint:** unavailable — no linter configured; `code_quality=0.7333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/books.ts:72` INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/books.ts:65` SELECT * ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/books.ts:66-68` WHERE author = ? COLLATE NOCASE; test `books.test.ts:35` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/books.ts:88-90` (200/404); test `books.test.ts:44` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/books.ts:92-99` UPDATE, 404 on 0 changes; test `books.test.ts:49` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/books.ts:104-106`; test `books.test.ts:53` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/books.ts:2,50` `node:sqlite` DatabaseSync + CREATE TABLE |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `src/books.ts:14` json() writes app/json; 201/200/400/404 throughout |
| R9 | Input validation: title and author required | ✓ implemented | `src/books.ts:35-36` reject non-string/empty → 400; test `books.test.ts:41` |
| R10 | GET /health endpoint | ✓ implemented | `src/books.ts:64` → 200 {status:'ok'}; test `books.test.ts:26` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` (setup, run, API, tests sections) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `src/books.test.ts` — 4 `node:test` tests, all pass (test_coverage=1.0) |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage = 1.0   → npm test (tsc build + node --test dist/*.test.js) built and all tests passed
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.7333
maintainability = 0.7864
idiomatic     = 0.87
```

Test suite (`src/books.test.ts`, node:test): health; create/read/filter-by-author; validation + 404; update + delete. 4 tests, 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 176 (books.ts 113, books.test.ts 55, server.ts 8) |
| Files | 3 source (.ts) |
| Dependencies | 3 (all devDeps: typescript, tsx, @types/node) — 0 runtime |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (read from stored scores) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] GET /books/0 and non-positive ids fall through to generic 404 "Not found" rather than a 400 invalid-id (id regex `^/books/([1-9]\d*)$` makes the `Number.isSafeInteger` guard at books.ts:87 unreachable)
2. [info] Zero runtime dependencies — SQLite requirement met with the built-in `node:sqlite` module
3. [info] Testable factory (`:memory:` in tests) plus 1 MB body cap and JSON-parse guard — hardening beyond spec

No critical/high/medium findings. All 12 spec requirements implemented; build and all tests pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                              # stored mechanical scores (test_coverage=1.0)
cat ../../REQUIREMENTS.json                  # pinned 12-item checklist
grep -rnE "\.skip\(|xit\(|it\.todo\(" src    # skip detection (0 real skips)
wc -l src/*.ts                               # LOC
# To actually build/test (not required for eval): npm install && npm test
```
