# Evaluation: rest-api-crud · agent=codex model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, agent=codex, model=gpt-6-luna, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests ran)
- **Lint:** n/a — no linter configured; code_quality=0.69 (mechanical) from scores.json
- **Architecture:** single-module HTTP service (see below — codebase is 2 files, no separate summary)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/server.ts:70-78` INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/server.ts:63-69` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `src/server.ts:64-67` `WHERE author = ?` (exact) |
| R4 | GET /books/{id} single book | ✓ implemented | `src/server.ts:79-83` 200 / 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/server.ts:84-92` UPDATE + 200 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/server.ts:93-97` DELETE + 204 |
| R7 | Data stored in SQLite | ✓ implemented | `src/server.ts:2,17-24` `node:sqlite` DatabaseSync, CREATE TABLE |
| R8 | JSON responses + HTTP status codes | ✓ implemented | `src/server.ts:26-29` content-type json; 201/200/204/400/404/500 |
| R9 | Validation: title + author required | ✓ implemented | `src/server.ts:44-51,72,86` `validBook`, 400 on fail |
| R10 | GET /health endpoint | ✓ implemented | `src/server.ts:62` returns `{status:'ok'}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — install/build/start, endpoints, env vars |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test/server.test.ts:22,35,40` 3 tests, test_coverage=1.0 |

## Architecture (inline)

Single module `src/server.ts` (112 lines). `createApp(databasePath)` opens a `node:sqlite`
`DatabaseSync`, ensures the `books` table, and returns a `node:http` `Server`. Routing is a
regex `^/books(?:/(\d+))?$` plus a `/health` special-case; body parsing is a promise over
request chunks with a 1MB cap and JSON-error → 400. `validBook` type-guards the input
(title/author non-empty strings; year integer-or-null; isbn string-or-null). No external
web framework or ORM — stdlib only. Tests (`test/server.test.ts`) spin the server on an
ephemeral port over a temp SQLite file and exercise CRUD, validation, filter, and health.

## Build & Test

Not re-run — stored mechanical scores used (per evaluate-run skill):

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.6889
             maintainability=0.9163  idiomatic=0.77  token_efficiency=0.00797
```

`test_coverage=1.0` ⇒ `tsx --test test/*.test.ts` built and ran with all tests passing.
Skip scan (`.skip(`/`xit(`/`it.todo(`): 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 159 (server 112, test 47) |
| Files (excl. node_modules/dist) | 13 |
| Dependencies | 3 (all devDependencies: @types/node, tsx, typescript; 0 runtime deps) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R3 — `?author=` filter is exact, case-sensitive equality (`src/server.ts:66`). Meets spec; noted for cross-run comparison.

No critical/high/medium/low findings. Clean run: 12/12 requirements, all tests pass, no skips, zero runtime dependencies.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores (build/test)
grep -rE "\.skip\(|xit\(|it\.todo\(" test/        # skip scan -> 0
wc -l src/server.ts test/server.test.ts           # LOC
# to actually run: npm install && npm test
```
