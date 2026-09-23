# Evaluation: agent=codex effort=default language=typescript model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — from `test_coverage=1.0` in scores.json
- **Build:** pass — `npm run build` (tsc) succeeded (test_coverage=1.0 ⇒ build+tests ran)
- **Lint:** unavailable — no linter configured; `code_quality=0.6889` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/server.ts:72-79` INSERT with UUID, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/server.ts:65-70` SELECT * ORDER BY rowid |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/server.ts:66-68` WHERE author = ?; test `?author=Nobody` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/server.ts:83-85` returns 404 when not found |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/server.ts:91-96` UPDATE, 404 if no rows changed |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/server.ts:87-89` DELETE, 200/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/server.ts:2,52-58` node:sqlite DatabaseSync + books table |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `src/server.ts:18-21` json() helper; 201/200/400/404/500 used |
| R9 | Input validation: title and author required | ✓ implemented | `src/server.ts:36-44` validateBook rejects empty title/author → 400; test line 38 |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/server.ts:64` returns {status:"ok"}; test line 17 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — setup, run, endpoints, tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/server.test.ts` 3 tests; test_coverage=1.0 |

Prompt factor (`prompt=neutral`) prescribes no methodology and adds no discrete checkable instruction — TASK.md is the whole spec.

## Build & Test

```text
npm run build   # tsc -p tsconfig.json
(compiled clean — inferred from scores.json test_coverage=1.0; not re-run per skill Step 2)
```

```text
npm test   # npm run build && node --test dist/tests/*.test.js
3 tests passed, 0 failed, 0 skipped  (test_coverage=1.0, defect_rate=1.0 from scores.json)
```

Scores were read from `scores.json` (inline gate output); build/test/lint were NOT re-run.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 155 (server.ts 113 + test 42) |
| Files | 2 source (+ README, package.json, tsconfig, lockfile) |
| Dependencies | 3 (all devDependencies: @types/node, tsx, typescript) — 0 runtime |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

Stored scores (scores.json): code_quality=0.6889, maintainability=0.8502, idiomatic=0.87, token_efficiency=0.0060, test_coverage=1.0, defect_rate=1.0.

## Findings

All findings are info-level (penalty-neutral); no defects. Full list in `findings.jsonl`:

1. [info] E1 — Zero-dependency implementation using Node 22.5+ built-ins (node:http/node:sqlite/node:crypto)
2. [info] E2 — Validation stricter than spec (year 0–9999 integer, isbn required)
3. [info] E3 — Request body size cap (413) and malformed-JSON handling (400)

## Reproduce

```bash
cd "experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=typescript_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json                        # stored mechanical scores (test_coverage=1.0)
grep -rE "^\s*test\(" tests/           # 3 tests
grep -rE "\.skip\(|xit\(|it\.todo\(" . --include="*.ts"   # 0 skips
# npm test   # only if re-verifying; requires Node >=22.5 (node:sqlite)
```
