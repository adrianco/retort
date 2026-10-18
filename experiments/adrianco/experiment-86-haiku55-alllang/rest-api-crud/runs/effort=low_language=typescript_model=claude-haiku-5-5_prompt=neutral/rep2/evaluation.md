# Evaluation: rest-api-crud (effort=low, typescript, claude-haiku-5-5, prompt=neutral) · rep 2

## Summary

- **Factors:** language=typescript, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 19 passed / 0 failed / 0 skipped (19 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + tests ran and passed)
- **Lint:** pass — `code_quality=0.733` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (inline gate output): `test_coverage=1.0`, `defect_rate=1.0`,
`code_quality=0.733`, `maintainability=0.895`, `idiomatic=0.82`, `token_efficiency=0.040`.
Per the skill, build/test/lint were NOT re-run — these stored scores are the signal.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:76-80`, `src/db.ts:47-52` (insert all four fields) |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:72-74`, `src/db.ts:61-70` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:73` reads `author` param; `src/db.ts:67-69` filters |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/app.ts:88-92` (404 branch), `src/db.ts:54-59` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:93-99`, `src/db.ts:72-78` (404 on no-change) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:100-103`, `src/db.ts:80-83` (204 / 404) |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/db.ts:1,20-34` — `node:sqlite` DatabaseSync, real table |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `src/app.ts:17-33` JSON helper; 201/200/204/400/404/405/413/500 used |
| R9 | Validation: title and author required | ✓ implemented | `src/validation.ts:25-26`; test `src/app.ts`→`test/api.test.ts:66-72` |
| R10 | GET /health health check | ✓ implemented | `src/app.ts:66-69` returns `{status:'ok'}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Setup/Run/Test/env-var sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test/api.test.ts` — 19 `it()` cases; `test_coverage=1.0` |

## Build & Test

Not re-run (per skill step 2). Stored gate scores stand in:

```text
scores.json: test_coverage=1.0  -> build succeeded + all tests passed
             defect_rate=1.0    -> build+test success
             code_quality=0.733 -> lint/quality
```

Test runner: `node --test` over 19 cases in `test/api.test.ts`, covering health, POST
(incl. optional-field, missing-field, bad-year, malformed-JSON), GET list + author filter +
empty, GET-by-id (200/404/400), PUT (200/400/404), DELETE (204/404), and routing (404/405).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 485 |
| Files (src + test) | 5 |
| Dependencies | 2 (both devDependencies: typescript, @types/node) — 0 runtime |
| Tests total | 19 |
| Tests effective | 19 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

Note: the step-5 skip grep reported 1 hit, a false positive — `process.exit(0)` in
`src/server.ts:17` matches the `xit(` pattern. No tests are skipped or disabled.

## Findings

Top findings (full list in `findings.jsonl`) — all informational:

1. [info] Error handling well beyond spec (413/405/400/404 in addition to required codes)
2. [info] Zero runtime dependencies via Node built-ins (node:sqlite, node:http)
3. [info] node:sqlite requires recent Node and is experimental — documented in README

No critical/high/medium/low findings. All 12 pinned requirements implemented; tests pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                 # stored gate scores (build/test/lint signal)
cat ../../REQUIREMENTS.json     # pinned 12-item checklist
# build+test (optional; already scored):  npm test
```
