# Evaluation: language=typescript_model=opus-4.8_prompt=bdd · rep 1

## Summary

- **Factors:** language=typescript, model=opus-4.8, prompt=bdd (framework=Express, chosen by agent)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `REQUIREMENTS.json` R1–R12)
- **Prompt (bdd):** followed — Given/When/Then structure, behaviour-named tests (P1–P4 all met)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — `tsc` (per `test_coverage=1.0`; not re-run)
- **Lint:** n/a — no linter configured; `code_quality=0.7333` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.ts:22`, `repository.ts:10` INSERT |
| R2 | GET /books lists all | ✓ implemented | `app.ts:32`, `repository.ts:23` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.ts:33-35`, `repository.ts:24-27` (exact match) |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `app.ts:40-50`; test `tests/books.test.ts:115` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.ts:53-67`, `repository.ts:40` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.ts:70-80`, `repository.ts:53` |
| R7 | SQLite / embedded DB | ✓ implemented | `db.ts:32` `node:sqlite` DatabaseSync + schema |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/204/400/404 across `app.ts` |
| R9 | Validation: title & author required | ✓ implemented | `validation.ts:26-31`; tests `:53`,`:65` |
| R10 | GET /health | ✓ implemented | `app.ts:17`; test `:27` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, endpoints, curl examples) |
| R12 | >= 3 tests | ✓ implemented | `tests/books.test.ts` — 12 tests, `test_coverage=1.0` |

Prompt-factor (bdd) instructions:

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Given/When/Then sections | ✓ | `tests/books.test.ts` uses `// Given/When/Then` comments throughout |
| P2 | Behaviour-named tests | ✓ | e.g. `given a missing title when created then it returns 400` (`:53`) |
| P3 | One assertion per scenario where practical | ✓ | Scenarios focus on a single observable outcome (1–2 assertions) |
| P4 | Descriptive `given…when…then` names | ✓ | All 12 `it()` names follow the pattern |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage = 1.0   → tsc build + vitest all passed (12/12)
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.7333
maintainability = 0.7305
idiomatic     = 0.88
token_efficiency = 1.0
```

Test suite (`tests/books.test.ts`): 12 `it()` cases across health, POST, GET list/filter, GET by id, PUT, DELETE. 0 `.skip`/`.only`/`xit`/`it.todo`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, src/) | 260 |
| Files (src + tests) | 6 |
| Dependencies (prod + dev) | 8 |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl` (no high/critical):

1. [low] Persistence relies on experimental `node:sqlite` builtin (Node ≥22.5) — `db.ts:8`
2. [low] No test covers the 400 invalid-id branch on id routes — `app.ts:42/55/72`
3. [info] `?author=` filter is exact-equality, not substring/case-insensitive — `repository.ts:26`

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=typescript_model=opus-4.8_prompt=bdd/rep1
cat scores.json                       # mechanical scores (build/test not re-run)
grep -rEc "\bit\(" tests              # 12 tests
grep -rEn "\.skip\(|xit\(|it\.todo\(|\.only\(" src tests   # 0 skips
npm install && npm test               # optional: requires Node >=22.5 for node:sqlite
```
