# Evaluation: effort=low_language=typescript_model=claude-fable-5-1_prompt=none · rep 3

## Summary

- **Factors:** language=typescript, model=claude-fable-5-1, prompt=none, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — `tsc` compiles; tests ran (test_coverage=1.0, defect_rate=1.0)
- **Lint:** not separately run — `code_quality=0.733` (scores.json)
- **Architecture:** 2-file Express app (`src/app.ts` factory + `src/server.ts` bootstrap); summary skill not invoked (trivial 2-file codebase, analyzed inline)
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `src/app.ts:60-67` INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `src/app.ts:69-76` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/app.ts:70-74` WHERE author = ? |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `src/app.ts:78-83` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/app.ts:85-98` (full replace) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/app.ts:100-105` 204 / 404 |
| R7 | Data stored in SQLite/embedded | ✓ implemented | `src/app.ts:2,41-48` `node:sqlite` DatabaseSync |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/400/404/204/500 across routes |
| R9 | Validation: title & author required | ✓ implemented | `src/app.ts:14-34,60-62` → 400 |
| R10 | GET /health | ✓ implemented | `src/app.ts:56-58` `{status:"ok"}` |
| R11 | README.md with setup/run | ✓ implemented | `README.md` — Setup/Run/Test/Endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 7 tests, all pass |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 1.0    # build + all tests passed
defect_rate     = 1.0    # build+test succeeded
code_quality    = 0.7333
maintainability = 0.8204
idiomatic       = 0.78
token_efficiency= 0.0513
```

Test file drives an in-memory app over real HTTP (`createApp(":memory:").listen(0)`),
covering health, create+get, validation (missing fields + bad year type), malformed
JSON → 400, list+author filter, PUT update (200/400/404), DELETE (204/404).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 214 (app 120, server 8, tests 86) |
| Files | 3 source (src/app.ts, src/server.ts, tests/books.test.ts) |
| Dependencies | 5 (express + 4 dev) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. No defects at or above `info`. The implementation satisfies every pinned
requirement, uses an embedded SQLite DB, validates input, returns correct status
codes, and ships 7 passing tests plus a complete README.

Notes (non-deductions):
- PUT is a full replace (validates required fields, so a partial PUT is rejected 400).
  Documented as "Replace" in the README — consistent, not a defect.
- Numeric-id guard (`parseId`) returns 404 for non-numeric ids — sensible.

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=typescript_model=claude-fable-5-1_prompt=none/rep3"
cat scores.json                       # mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json        # pinned checklist
grep -rnE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests/   # 0 skips
```
