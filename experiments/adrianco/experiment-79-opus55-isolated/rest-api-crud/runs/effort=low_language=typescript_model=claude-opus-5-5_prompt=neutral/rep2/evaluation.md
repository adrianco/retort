# Evaluation: rest-api-crud · effort=low language=typescript model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + all tests passed)
- **Lint:** pass — `code_quality=0.733` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/app.ts:24`, `src/db.ts:25` |
| R2 | GET /books lists all books | ✓ implemented | `src/app.ts:34`, `src/db.ts:32` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/app.ts:35-40`, `src/db.ts:36` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `src/app.ts:43-52` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/app.ts:54-68`, `src/db.ts:48` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/app.ts:70-78`, `src/db.ts:55` |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `src/db.ts:1` `node:sqlite` DatabaseSync, real table |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404 throughout `src/app.ts` |
| R9 | Validation: title and author required | ✓ implemented | `src/validation.ts:24-28` |
| R10 | GET /health health-check | ✓ implemented | `src/app.ts:20` returns `{status:"ok"}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` (setup/run/test/API/curl) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/books.test.ts` — 12 tests, `test_coverage=1.0` |

No prompt-factor requirements: `prompt=neutral` maps to the neutral instruction, which adds no additional checkable constraints beyond TASK.md.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2):

```text
test_coverage = 1.0   -> build succeeded + all tests passed
defect_rate   = 1.0   -> build + test succeeded
code_quality  = 0.733 -> lint/quality signal
maintainability = 0.780
idiomatic     = 0.88
```

Agent's own run log (`_agent_stdout.log`) confirms: type-checks, compiles, 12 integration tests pass, live smoke test of the compiled server answered `/health` and created a book.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, src/) | 224 |
| Lines of code (tests) | 150 |
| Files (excl. node_modules/.git) | 18 |
| Dependencies (deps + devDeps) | 5 |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | not separately timed (scores from archive) |

## Findings

All findings are info-level; the run is complete and correct.

1. [info] POST /books sets a `Location` header on 201 — `src/app.ts:31`
2. [info] Malformed JSON and unknown routes handled explicitly — `src/app.ts:80,84-90`
3. [info] `?author=` filter is exact + case-insensitive (documented choice) — `src/db.ts:36`
4. [info] PUT is a full replace requiring title+author (documented choice) — `src/app.ts:54-68`

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=typescript_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                  # mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json                   # pinned 12-requirement checklist
grep -rEn "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests   # skip scan (0 real)
# optional re-verify: npm install && npm run typecheck && npm test
```
