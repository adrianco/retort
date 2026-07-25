# Evaluation: typescript · gpt-oss-20b (neutral/gptoss) · rep 2

## Summary

- **Factors:** language=typescript, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (R7 satisfied via SQLite but uses `:memory:` mode — noted, not deducted)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass (test_coverage=0.9558, defect_rate=1.0 from scores.json)
- **Lint:** pass (code_quality=0.6889 from scores.json)
- **Architecture:** single-file Express app (`src/index.ts`), sqlite3 in-memory store; run-summary skill not invoked (trivial single-module codebase)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/index.ts:32` INSERT + returns 201 with row |
| R2 | GET /books lists all | ✓ implemented | `src/index.ts:50,58` `SELECT * FROM books` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/index.ts:52-56` `WHERE author = ?` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `src/index.ts:66-72` 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/index.ts:76-93` UPDATE, 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/index.ts:96-106` DELETE, 204 |
| R7 | Data in SQLite/embedded DB | ✓ implemented | `src/index.ts:9` `sqlite3.Database(':memory:')` — real SQLite engine (in-memory mode; see finding) |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/204 across routes |
| R9 | title & author required (400) | ✓ implemented | `src/index.ts:24-29,33-36` `validateBook` → 400 |
| R10 | GET /health | ✓ implemented | `src/index.ts:109` returns `{status:'ok'}` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup/run/test/endpoints (minor `pm run dev` typo) |
| R12 | ≥3 tests | ✓ implemented | `__tests__/api.test.ts` — 7 tests, 0 skipped |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.9558   (build + jest suite passed; ~95.6% coverage)
defect_rate   = 1.0      (build+test succeeded)
code_quality  = 0.6889
maintainability = 0.5465
idiomatic     = 0.38
token_efficiency = 0.0053
```

7 tests cover health, create, list, author-filter, get-by-id, update, delete (incl. 404-after-delete).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 118 (src) + 64 (tests) = 182 |
| Files | 2 source/test (+ README, package.json, tsconfig, jest.config) |
| Dependencies | 10 (2 runtime, 8 dev) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=0.9558) |

## Findings

Full list in `findings.jsonl`:

1. [low] R7 — SQLite runs in `:memory:` mode; no persistence across restarts (`src/index.ts:9`). Spec satisfied (real embedded DB engine) but volatile.
2. [low] README run command typo `pm run dev` should be `npm run dev` (`README.md:20`).

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep2
cat scores.json          # stored build/test/lint scores
npm install && npm test  # optional re-verification (7 tests)
```
