# Evaluation: language=typescript · model=sonnet-4.6 · prompt=tdd · rep 1

## Summary

- **Factors:** language=typescript, model=sonnet-4.6, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (2 implemented reqs carry accuracy caveats — see findings R10, brfootball-season)
- **Tests:** 134 passed / 0 failed / 0 skipped (134 effective) — per `_agent_stdout.log`; corroborated by `test_coverage=0.9`, `defect_rate=1.0` in `scores.json`
- **Build:** pass — `defect_rate=1.0` (build + tests succeeded); not re-run
- **Lint:** pass — `code_quality=0.733` from `scores.json`; not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

## Requirements

Checklist is the pinned `experiment-15-sonnet5/brazil/REQUIREMENTS.json` (12 reqs, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/server.ts:852` `new Server(...)` + `StdioServerTransport`; 8 tools registered `src/server.ts:867` |
| R2 | Loads provided CSVs in data/kaggle/ | ✓ implemented | `src/dataLoader.ts:127` `loadAllData` reads all 6 CSVs; `data/kaggle/` has all 6 files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/matchQueries.ts:344` `findMatches` filters via `teamsMatch(home/away, team)` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/matchQueries.ts:352` season filter; `MatchFilter` has dateFrom/dateTo (season path tested) |
| R5 | Filter by competition | ✓ implemented | `src/matchQueries.ts:351` competition filter; enum in `search`/tool schemas `src/server.ts:878` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/teamQueries.ts:461` `getTeamRecord` returns played/wins/draws/losses/goalsFor/Against |
| R7 | Player search by name | ✓ implemented | `src/playerQueries.ts:562` `searchPlayers` name substring; tool `search_players` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `src/playerQueries.ts:565-567` nationality/club filters; returns overall/potential |
| R9 | Season standings computed from matches | ✓ implemented | `src/teamQueries.ts:505` `getStandings` computes points/rank from match results |
| R10 | Aggregate statistics | ✓ implemented | `src/matchQueries.ts:411` `getBiggestWins`, `:424` `getAverageGoals` (accuracy caveat — see findings) |
| R11 | Head-to-head between two teams | ✓ implemented | `src/matchQueries.ts:378` `getHeadToHead` returns W/L/D between two teams |
| R12 | Automated tests for query capabilities | ✓ implemented | 6 `*.test.ts` files, 28 describe / 67+ it blocks; `test_coverage=0.9`, all pass |

### Prompt-factor conformance (prompt=tdd)

TDD discipline is a process instruction (`prompts/tdd.md`) — not directly verifiable from the final tree, but consistent with the artifacts: a dedicated test file exists per module (`teamNormalizer`, `dataLoader`, `matchQueries`, `teamQueries`, `playerQueries`, `handlers`), tests are behavior-focused, and the agent log reports a red/green cycle. No evidence contradicts TDD.

## Build & Test

Not re-run (per skill: use stored scores). Signals from `scores.json` + agent log:

```text
build: tsc — pass (defect_rate=1.0)
```

```text
test: jest (ts-jest ESM) — 12 suites, 134 tests, all passing
test_coverage=0.9, defect_rate=1.0
skipped/disabled tests: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test) | 1092 |
| Lines of code (tests) | 675 |
| Files (excl. node_modules/.git/summary) | 32 |
| Dependencies | 3 runtime + 5 dev |
| Tests total | 134 |
| Tests effective | 134 |
| Skip ratio | 0% |
| Build | pass (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [medium] R10 — Aggregate stats double-count BR-Football-Dataset matches in unfiltered queries (overlap with Brasileirao/Libertadores CSVs; no de-dup for unfiltered path).
2. [low] BR-Football matches silently excluded from all season-filtered queries (`getMatchSeason` returns 0 — no season parsed).
3. [low] Team-name alias table covers only 3 full-name variants.
4. [info] `getTopScoringTeams` / `getPlayersByClub` implemented + tested but not exposed as MCP tools.

## Reproduce

```bash
cd experiment-15-sonnet5/brazil/runs/language=typescript_model=sonnet-4.6_prompt=tdd/rep1
# scores already computed — read them:
cat scores.json
# to re-verify from scratch (not required):
npm install && npm run build && npm test
# skip scan:
grep -rEn "\.skip\(|xit\(|xdescribe\(|it\.todo\(" src --include="*.ts"
```
