# Evaluation: language=typescript_model=sonnet_prompt=TDD · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet, prompt=TDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (R8 has a minor low-severity robustness note but is functionally satisfied)
- **Tests:** 66 passed / 0 failed / 0 skipped (66 effective) — from `test_coverage=1.0`
- **Build:** pass — `test_coverage=1.0` (build + all tests passed; no re-run)
- **Lint:** pass — `code_quality=0.733` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/server.ts:7` McpServer + 6 `server.tool(...)`; entrypoint `src/index.ts:9` stdio transport |
| R2 | Load & use data/kaggle/ datasets | ✓ implemented | `src/loader.ts:94-206` reads all 6 CSVs; `data/kaggle/` holds all 6 files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/queries.ts:28-32` filters home OR away via `teamsMatch` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/queries.ts:39-49` season + dateFrom/dateTo filters |
| R5 | Filter by competition (Brasileirão/Copa do Brasil/Libertadores) | ✓ implemented | `src/queries.ts:34-37`; competitions tagged `src/loader.ts:237,251,265` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/queries.ts:68-122` getTeamStats aggregates W/D/L, GF/GA, points |
| R7 | Player search by name | ✓ implemented | `src/players.ts:20-23` name `includes` filter |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `src/players.ts:25-38` nationality/club filters; returns `overall`/`potential` (low note: exact-match nationality) |
| R9 | Standings computed from match results | ✓ implemented | `src/queries.ts:159-225` getStandings tallies points/GD/position from matches |
| R10 | Aggregate statistics | ✓ implemented | `src/queries.ts:242-300` avg_goals, biggest_wins, home_win_rate, top_scorers |
| R11 | Head-to-head between two teams | ✓ implemented | `src/queries.ts:124-147` headToHead W/L/D; tool `src/tools.ts:184` |
| R12 | Automated tests covering queries | ✓ implemented | 5 `*.test.ts`, 66 tests, `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (computed during scoring — not re-run per skill guidance):

```text
test_coverage = 1.0   → build succeeded + all tests passed
code_quality  = 0.733 → lint/quality
defect_rate   = 1.0   → build+test succeeded
maintainability = 0.729   idiomatic = 0.78   token_efficiency = 1.0
```

```text
vitest run  (npm test)
66 tests across loader/queries/players/normalizer/tools — all pass, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test) | 1232 |
| Lines of code (tests) | 599 |
| Files (excl node_modules) | 31 |
| Dependencies (deps + devDeps) | 6 |
| Tests total | 66 |
| Tests effective | 66 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] R8 player nationality/position filters use exact equality, not partial match (`src/players.ts:27,37`)
2. [low] Cup match round parsed as string but assigned to numeric NormalizedMatch.round (`src/loader.ts:116,253`)
3. [info] TDD prompt satisfied — thorough test-first coverage (66 tests)
4. [info] Statistical analysis exceeds single-aggregate minimum (4 stat types)
5. [info] Competition coverage spans all three named competitions with dedup/source-priority merge

## Reproduce

```bash
cd experiment-14/runs/language=typescript_model=sonnet_prompt=TDD/rep1
cat scores.json                      # build/test/lint scores (no re-run)
npm install && npm test              # vitest run — 66 tests
grep -rE "\.skip\(|xit\(|it\.todo\(" src --include="*.ts"   # skip check (0 real)
```
