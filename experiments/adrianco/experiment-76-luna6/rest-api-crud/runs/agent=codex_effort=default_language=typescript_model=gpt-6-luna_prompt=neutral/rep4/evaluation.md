# Evaluation: agent=codex language=typescript model=gpt-6-luna prompt=neutral · rep 4

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.7333` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/app.ts:59-67` INSERT + 201 re-select |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:52-57` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:53-56` WHERE author = ? COLLATE NOCASE; test `books.test.ts:55` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `src/app.ts:72-74` returns book or 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/app.ts:76-85` UPDATE, 404 if absent; test `books.test.ts:56` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/app.ts:86-89` DELETE, 204/404; test `books.test.ts:58` |
| R7 | Data in SQLite/embedded DB | ✓ implemented | `src/app.ts:2,40` `node:sqlite` DatabaseSync, real table |
| R8 | JSON responses + status codes | ✓ implemented | `src/app.ts:7-12` json() helper; 201/200/204/400/404/500 |
| R9 | Validation: title & author required | ✓ implemented | `src/app.ts:24-25` parseInput; test `books.test.ts:47-50` |
| R10 | GET /health | ✓ implemented | `src/app.ts:51` returns {status:"ok"}; test `books.test.ts:62-66` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, endpoints, tests sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/books.test.ts` 4 tests; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (inline gate); toolchain not re-run per skill guidance.

```text
test_coverage = 1.0   → build succeeded + all tests passed
defect_rate   = 1.0   → build+test success
code_quality  = 0.7333
maintainability = 0.8968 · idiomatic = 0.78
```

Test command (for reference): `node --experimental-strip-types --test tests/*.test.ts` — 4 tests, node:test, in-memory SQLite via `createHandler(db)`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 173 (app 96, server 11, tests 66) |
| Files | 3 |
| Dependencies | 0 (stdlib only) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (scores from cache) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Zero-dependency Node implementation using built-in node:http + node:sqlite
2. [info] ?author= filter is case-insensitive exact match, not substring
3. [info] Consistent status codes and top-level error handling

No requirement gaps, no skipped/disabled tests, no build/lint failures.

## Reproduce

```bash
cd experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep4
cat scores.json                 # test_coverage=1.0 → build+tests pass
grep -rnE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts"   # 0 real skips
wc -l src/*.ts tests/*.ts
```
