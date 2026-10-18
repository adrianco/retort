# Evaluation: effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=typescript, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 53 passed / 0 failed / 0 skipped (53 effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (build + all tests passed; not re-run)
- **Lint:** n/a — `code_quality=0.733` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

All twelve pinned requirements (from the experiment's `REQUIREMENTS.json`) are implemented
with clear evidence and exercised by an end-to-end vitest suite. `test_coverage=1.0`
(scores.json) confirms the build succeeded and every test passed. This is a clean,
idiomatic, well-factored implementation; the only noted issue is a low-severity data-model
nuance in cross-source de-duplication.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/server.ts:38` `createServer()` registers 8 tools on `McpServer`; `src/index.ts` stdio transport |
| R2 | Load & use data/kaggle CSVs | ✓ implemented | `src/dataset.ts:88-141` reads all 6 CSVs; `data/kaggle/` present (6 files) |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/queries.ts:106 searchMatches` + `involves()` with `venue` home/away/any |
| R4 | Filter by date range and/or season | ✓ implemented | `src/queries.ts:48 matchFilter` season/seasonFrom/seasonTo/dateFrom/dateTo |
| R5 | Filter by competition (3 comps) | ✓ implemented | `src/dataset.ts:22 COMPETITION` + `queries.ts:44 competitionFilter`; all three mapped |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/queries.ts:162 teamStats` → `tally()` |
| R7 | Player search by name | ✓ implemented | `src/queries.ts:284 searchPlayers` (`name` filter) |
| R8 | Players by nationality/club with ratings | ✓ implemented | `src/queries.ts:284` nationality/club/position/minOverall; returns overall/potential |
| R9 | Season standings from match results | ✓ implemented | `src/queries.ts:212 standings` computes points (3/1) from matches |
| R10 | Aggregate statistics | ✓ implemented | `src/queries.ts:256 aggregateStats` (avg goals, home/draw/away); `biggestWins` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/queries.ts:185 headToHead` returns W/L/D + meetings |
| R12 | Automated tests of query capabilities | ✓ implemented | 53 tests across 5 files; `test_coverage=1.0`; `server.test.ts` end-to-end via MCP client |

## Build & Test

Not re-run — stored scores used per skill policy:

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.733
             maintainability=0.751  idiomatic=0.6  token_efficiency=0.0134
test_coverage=1.0 ⇒ `npm test` built and all 53 tests passed.
```

Skipped-test scan: 0 skips (the single grep hit was `process.exit(` in `src/index.ts:24`
matching the `xit(` pattern — a false positive, not a disabled test).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src, .ts) | 1149 |
| Lines of code (tests, .ts) | 518 |
| Files (excl. node_modules/.git/data) | 30 |
| Dependencies | 3 runtime (@modelcontextprotocol/sdk, csv-parse, zod) + 3 dev |
| Tests total | 53 |
| Tests effective | 53 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Cross-source de-dup keys on (season,competition,teams,score) excluding date — can merge distinct two-legged ties with identical scores (`src/dataset.ts:202`)
2. [info] Coverage exceeds spec: cross-file player↔match club join + state-suffix team disambiguation
3. [info] End-to-end MCP tests via a real in-memory client transport

## Reproduce

```bash
cd experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=typescript_model=claude-haiku-5-5_prompt=neutral/rep3
cat scores.json                 # stored mechanical scores (build/test not re-run)
cat ../../REQUIREMENTS.json      # pinned 12-requirement checklist
grep -rnE "\.skip\(|xit\(|xdescribe\(|it\.todo\(" tests src --include="*.ts"
```
