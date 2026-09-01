# Evaluation: hermes-0205 · Qwen3.6-35B-A3B · m35-verify-on · rep 2

## Summary

- **Factors:** language=typescript, agent=hermes-0205, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35-verify-on
- **Status:** ok — builds and all tests pass; two medium spec/factor deviations
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (R1 met functionally but at a non-spec path — see findings)
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective)
- **Build:** pass (defect_rate=1.0, scores.json)
- **Lint / quality:** code_quality=0.40, idiomatic=0.0 (not actually TypeScript)
- **Architecture:** app.js (express + middleware) → routes.js (validation + handlers) → db.js (better-sqlite3 layer); server.js entry with graceful shutdown
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/routes.js:54` POST + `src/db.js:37` createBook (path is /api/books) |
| R2 | GET /books lists all | ✓ implemented | `src/routes.js:78` + `src/db.js:23` getAllBooks |
| R3 | GET /books ?author= filter | ✓ implemented | `src/db.js:24-27` filters by author param |
| R4 | GET /books/{id} + 404 | ✓ implemented | `src/routes.js:84-96` returns 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/routes.js:98` + `src/db.js:45` updateBook |
| R6 | DELETE /books/{id} | ✓ implemented | `src/routes.js:122` + `src/db.js:80` deleteBook (204) |
| R7 | SQLite / embedded DB | ✓ implemented | `src/db.js:1-6` better-sqlite3 at books.db |
| R8 | JSON + proper status codes | ✓ implemented | 201/200/404/400/409/204 across routes.js |
| R9 | Validation: title+author required | ✓ implemented | `src/routes.js:11-16` (also requires year/isbn — see val-1) |
| R10 | GET /health | ✓ implemented | `src/app.js:9` returns `{status:'ok'}` at /health |
| R11 | README with setup/run | ✓ implemented | `README.md` install/build/run/test sections |
| R12 | ≥3 tests | ✓ implemented | `src/__tests__/api.test.js` 18 `it()` cases, 0 skipped |

## Build & Test

Scores read from `scores.json` (inline gate) — not re-run per skill guidance:

```text
test_coverage = 0.8794   # build + tests ran; coverage fraction
defect_rate   = 1.0      # build + test succeeded
code_quality  = 0.40
idiomatic     = 0.0      # sources are plain JS, not TypeScript
maintainability = 0.863
```

Agent self-report (`_agent_stdout.log`): "Build succeeds and all 18 tests pass."

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, excl. tests) | 273 |
| Test LOC | 320 |
| Files (src) | 5 |
| Dependencies | 11 |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| .ts files | 0 |

## Findings

Top items (full list in `findings.jsonl`):

1. [medium] CRUD routes mounted under `/api`, not the spec's `/books` (src/app.js:13) — spec clients hitting `/books` get 404.
2. [medium] TypeScript cell produced plain CommonJS JS, no `.ts`/types (idiomatic=0.0) — language factor not exercised.
3. [low] Validation stricter than spec: year and isbn also required (src/routes.js:17-27).
4. [info] Build + all 18 tests pass.

## Reproduce

```bash
cd "runs/agent=hermes-0205_language=typescript_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35-verify-on/rep2"
cat scores.json                 # stored build/test/quality scores
grep -c "\bit(" src/__tests__/api.test.js   # 18 tests
find src -name "*.ts" | wc -l   # 0 — not TypeScript
```
