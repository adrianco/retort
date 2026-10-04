# Evaluation: agent=codex effort=low language=typescript model=gpt-6-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — not re-run (test_coverage=1.0 ⇒ `npm run build && node --test` succeeded)
- **Lint:** n/a — `code_quality=0.7333` (scores.json)
- **Architecture:** single-module HTTP handler (`app.ts`) + entrypoint (`server.ts`) + tests (`app.test.ts`); run-summary skipped (2-source-file codebase fully covered here)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `app.ts:87-93` INSERT + 201 + Location header |
| R2 | GET /books lists all | ✓ implemented | `app.ts:82-83` `SELECT * ... ORDER BY id` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.ts:81-84` bound `WHERE author = ?`; tested `app.test.ts:62` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `app.ts:107-108`; 404 tested `app.test.ts:86` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.ts:109-114` UPDATE + 200 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.ts:116-117` DELETE + 200 |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `app.ts:2,57-69` `node:sqlite` DatabaseSync + schema; persistence tested `app.test.ts:98-109` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `app.ts:15-18` `json()`; 201/200/404/400/405/413/415 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.ts:38-42` non-empty string check → 400; tested `app.test.ts:70` |
| R10 | GET /health | ✓ implemented | `app.ts:75-78` returns `{status:'ok'}` after DB probe |
| R11 | README with setup/run instructions | ✓ implemented | `README.md:6-19` setup, run, test, endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 `test(...)` in `app.test.ts`; `test_coverage=1.0` |

No requirements partial or missing. Enhancements beyond spec (415/413 handling, SQL-injection-as-data, DB-probing health check, cross-restart persistence test) noted as info findings.

## Build & Test

Not re-run per skill Step 2 — mechanical scores already computed and stored.

```text
# scores.json
{"code_quality": 0.7333, "token_efficiency": 0.0180, "test_coverage": 1.0,
 "defect_rate": 1.0, "maintainability": 0.7096, "idiomatic": 0.67}
```

`test_coverage=1.0` ⇒ `npm test` (`tsc` build + `node --test dist/app.test.js`) built and passed all tests. `defect_rate=1.0` ⇒ build+test succeeded. No skips detected (`grep .skip/xit/xdescribe/it.todo` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 263 (app.ts 130, app.test.ts 120, server.ts 13) |
| Files | 15 (incl. lockfile, tsconfig, caches) |
| Dependencies | 2 (both devDependencies: @types/node, typescript — no runtime deps) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`) — all info-level, no defects:

1. [info] Content-Type enforcement and 64 KiB body cap beyond spec (`app.ts:21-28`)
2. [info] Parameterized queries; SQL-injection treated as data (`app.ts:84`, `app.test.ts:63`)
3. [info] Cross-restart persistence explicitly tested (`app.test.ts:98-109`)
4. [info] Health check probes the database (`app.ts:76`)
5. [info] Relies on experimental `node:sqlite` — documented in README (`app.ts:2`, `README.md:3`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=typescript_model=gpt-6-astra_prompt=neutral/rep1"
cat scores.json                      # stored mechanical scores (test_coverage=1.0)
grep -rE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" . --include="*.ts"   # 0 skips
grep -cE "^test\(" app.test.ts       # 6 tests
# build/test NOT re-run — test_coverage=1.0 already proves npm test passed
```
