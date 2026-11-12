# Evaluation: holo4 · typescript · hermes-0230 · rep 2

## Summary

- **Factors:** language=typescript, model=llamacpp/Holo4-35B-A3B, agent=hermes-0230, prompt=neutral, stack=holo4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass (defect_rate=1.0 from scores.json ⇒ build+test succeeded)
- **Lint/Quality:** code_quality=0.733, maintainability=0.778, idiomatic=0.55 (from scores.json)
- **Coverage:** test_coverage=0.8839 (from scores.json — tests executed and passed)
- **Architecture:** Express app (`src/index.ts`) + promisified sqlite3 layer (`src/db.ts`) + shared types (`src/types.ts`); supertest integration suite (`tests/book.test.ts`)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/index.ts:15` INSERT + 201 return |
| R2 | GET /books lists all books | ✓ implemented | `src/index.ts:47` returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `src/index.ts:52` WHERE author = ? |
| R4 | GET /books/{id} single book | ✓ implemented | `src/index.ts:65` 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/index.ts:76` partial-field update |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/index.ts:123` 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.ts:55` books table via sqlite3 |
| R8 | JSON + appropriate codes | ✓ implemented | 201/200/204/400/404/409 across routes |
| R9 | Validation: title & author required | ✓ implemented | `src/index.ts:18` 400 when missing (also requires year/isbn — see finding) |
| R10 | GET /health | ✓ implemented | `src/index.ts:9` returns `{status:'OK'}` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup/run/test + endpoint docs |
| R12 | ≥3 tests | ✓ implemented | 13 `it(` tests in `tests/book.test.ts` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.8839   # tests executed and passed
defect_rate   = 1.0      # build + test succeeded
code_quality  = 0.7333
maintainability = 0.7783
idiomatic     = 0.55
```

Agent log (`_agent_stdout.log`): "All 13 tests pass. The code builds cleanly."

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, src+tests) | 372 |
| Files (src+tests) | 4 |
| Dependencies | 12 |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [low] POST /books over-validates — year and isbn also required, though R9 asks only for title/author (`src/index.ts:22`)
2. [info] Each DB query opens/closes its own sqlite3 connection (`src/db.ts:7`)

No high or critical findings — a clean, spec-complete run.

## Reproduce

```bash
cd experiments/adrianco/experiment-96-holo4-remeasure/rest-api-crud/runs/agent=hermes-0230_language=typescript_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4/rep2
cat scores.json              # stored mechanical scores (do not re-run build/test)
grep -rEc "\bit\(" tests/*.ts      # 13 tests
grep -rEc "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests/ src/   # 0 skips
```
