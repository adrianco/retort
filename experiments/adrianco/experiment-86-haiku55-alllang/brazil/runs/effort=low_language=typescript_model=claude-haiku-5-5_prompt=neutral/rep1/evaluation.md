# Evaluation: effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 48 passed / 0 failed / 0 skipped (48 effective)
- **Build:** pass — from `test_coverage=1.0`, `defect_rate=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=0.733` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Checklist from the pinned `REQUIREMENTS.json` (12 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/server.ts:43` `createServer` registers 7 tools; `src/index.ts:21` stdio transport; `tests/server.test.ts:27` asserts the 7-tool surface |
| R2 | Load/use data/kaggle CSVs | ✓ implemented | `src/loader.ts:44` `MATCH_SOURCES` + `:181` `loadPlayers` read all 6 CSVs; `tests/loader.test.ts:5` loads the real files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/queries.ts:64` `matchFits` matches home OR away; `tests/queries.test.ts:78` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/queries.ts:55-57` season + start/end date; `tests/queries.test.ts:84,96` |
| R5 | Filter by competition (Brasileirão/Copa/Libertadores) | ✓ implemented | `src/queries.ts:54` competition filter; loader tags all three competitions; `tests/queries.test.ts:90` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/queries.ts:118` `teamRecord`; `tests/queries.test.ts:109,115` |
| R7 | Player search by name | ✓ implemented | `src/queries.ts:215` `searchPlayers` name filter; `tests/queries.test.ts:165` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `src/queries.ts:221-225` nationality/club/overall; `tests/queries.test.ts:154,160` |
| R9 | Standings computed from results | ✓ implemented | `src/queries.ts:168` `standings` (3-1-0 from matches); `tests/queries.test.ts:141`, `tests/server.test.ts:52` |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `src/queries.ts:259` `matchStatistics`; `tests/queries.test.ts:181,192` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/queries.ts:141` `headToHead`; `tests/queries.test.ts:126`, `tests/server.test.ts:46` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 48 tests across 5 files; `test_coverage=1.0` (tests executed and passed) |

## Build & Test

Not re-run — stored scores read from `scores.json` (per evaluate-run step 2):

```text
{"code_quality": 0.733, "test_coverage": 1.0, "defect_rate": 1.0,
 "maintainability": 0.766, "idiomatic": 0.86, "token_efficiency": 0.0128}
```

`test_coverage=1.0` ⇒ `tsc` build + `vitest run` all passed. `vitest` test files: csv(5), queries(20), normalize(8), loader(7), server(8) = 48 `it()` blocks. `grep` for `.skip(`/`xit(`/`it.todo(` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src only) | 1018 |
| Files (excl. node_modules/dist/data/.git) | 27 |
| Dependencies (prod+dev) | 5 |
| Tests total | 48 |
| Tests effective | 48 |
| Skip ratio | 0% |
| Build/test | pass (from scores.json) |

## Findings

Full list in `findings.jsonl`. No defects — both items are informational:

1. [info] Player-level top scorers not provided — optional spec item, not inferable from the FIFA data; not in REQUIREMENTS.json.
2. [info] Cross-file fixture de-duplication is heuristic — reasonable tradeoff, guarded by `loader.test.ts:36`.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores (not re-run)
grep -rcE '\bit\(' tests/*.ts                      # test counts per file
grep -rnE '\.skip\(|xit\(|it\.todo\(' tests/       # skip detection (0)
# optional: npm install && npm test               # would re-run tsc build + vitest
```
