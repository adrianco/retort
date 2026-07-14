# Evaluation: language=java_model=sonnet_prompt=ATDD · rep 1

## Summary

- **Factors:** language=java, model=sonnet, prompt=ATDD (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 51 passed / 0 failed / 0 skipped (51 effective) — from test_coverage=1.0
- **Build:** pass (test_coverage=1.0 from scores.json / retort.db ⇒ build + all tests passed)
- **Lint:** pass — code_quality=1.0 from scores.json / retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low)

Mechanical scores (from `scores.json`, cross-checked against `experiment-14/retort.db`): test_coverage=1.0, code_quality=1.0, defect_rate=1.0, maintainability=0.705, idiomatic=0.78, token_efficiency=0.095. Build/tests were **not** re-run — stored scores used per skill policy.

## Requirements

Checklist is the pinned `experiment-14/REQUIREMENTS.json` (12 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `BrazilianSoccerMcpServer.java:194` `startMcpServer()` registers 6 `SyncToolSpecification` tools on `StdioServerTransportProvider` |
| R2 | Loads datasets in data/kaggle/ | ✓ implemented | `DataLoader.java:41-53` loads 5 match CSVs + fifa_data.csv via Apache Commons CSV |
| R3 | Match query by team (home/away/either) | ✓ implemented | `MatchService.java:28` `findMatches`; tests `MatchQueriesAcceptanceTest.findMatchesByTeamOnEitherSide`, `findMatchesByHomeAndAwayTeam` |
| R4 | Match query by date range / season | ✓ implemented | `MatchService.java:36-38` season+date filters; tests `findMatchesBySeason`, `findMatchesByDateRange` |
| R5 | Match query by competition | ✓ implemented | `MatchService.java:246` `matchesCompetition` aliasing; tests `findMatchesForLibertadores`, `findMatchesForCopaDoBrasil` |
| R6 | Team query: W/L/D + goals for/against | ✓ implemented | `MatchService.java:46` `getTeamStats`; tests `TeamQueriesAcceptanceTest.getTeamStatsReturnsWinDrawLoss`, `getTeamStatsIncludesGoals` |
| R7 | Player search by name | ✓ implemented | `PlayerService.java:35` `matchesName`; test `PlayerQueriesAcceptanceTest.findPlayersByNameNeymar` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `PlayerService.java:40-48`; tests `findPlayersByNationalityBrazil`, `findPlayersByClub`, `findPlayersByNeymarHasOverallRating` |
| R9 | Standings computed from match results | ✓ implemented | `MatchService.java:65` `getStandings` accumulates points/GD; tests `CompetitionQueriesAcceptanceTest.getStandingsShowsPoints`, `getStandingsShowsWinsDrawsLosses` |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `MatchService.java:151` `getStatistics`; tests `StatisticsAcceptanceTest.getStatisticsBiggestWins`, `getStatisticsAvgGoals`, `getStatisticsHomeRecord` |
| R11 | Head-to-head between two teams | ✓ implemented | `MatchService.java:99` `getHeadToHead`; tests `StatisticsAcceptanceTest.getHeadToHeadFlamengVsFluminense`, `getHeadToHeadContainsWinRecord` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 51 tests across 5 acceptance + 1 unit suite; test_coverage=1.0 |

### Prompt factor (ATDD) conformance

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Acceptance test per requirement as executable spec | ✓ implemented | 5 acceptance suites map 1:1 to query categories; 39 acceptance tests total |
| P2 | Exercise SUT only through public interface, no back-door access | ✓ implemented | Tests call only public tool methods (`server.findMatches(...)`); no reflection/internal access |
| P3 | Assert WHAT not HOW, in domain language | ✓ implemented | e.g. `getTeamStatsReturnsWinDrawLoss`, `findMatchesByTeamOnEitherSide` assert on output content |
| P4 | Atomic & independent, each scenario from an empty system | ~ partial | Shared static server over full dataset (`MatchQueriesAcceptanceTest.java:17`); independent but not empty-per-scenario — see findings |
| P5 | Finer-grained unit TDD underneath | ✓ implemented | `TeamNameNormalizerTest.java` — 12 unit tests on the normalizer |

## Build & Test

Not re-run (per skill policy — stored scores authoritative).

```text
scores.json: test_coverage=1.0  code_quality=1.0  defect_rate=1.0
⇒ Maven build succeeded; all 51 JUnit 5 tests passed; 0 skipped.
```

retort.db cross-check (experiment-14/retort.db, status=completed) matched scores.json exactly.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main java) | 1271 |
| Lines of code (test java) | 528 |
| Files (excl. data/, target/) | 24 |
| Tests total | 51 |
| Tests effective | 51 |
| Skip ratio | 0% |
| code_quality | 1.0 |
| maintainability | 0.705 |
| idiomatic | 0.78 |
| token_efficiency | 0.095 |

## Findings

Full list in `findings.jsonl` (2 items, both low):

1. [low] P4 — acceptance tests share a static server over the full dataset, not an empty-per-scenario system (`MatchQueriesAcceptanceTest.java:17`)
2. [low] data-dedup-1 — novo_campeonato dedup uses a hardcoded 2012 cutoff coupled to Brasileirao_Matches.csv coverage (`DataLoader.java:100-121`)

No critical/high/medium findings. All 12 spec requirements implemented and tested; ATDD methodology clearly followed.

## Reproduce

```bash
cd experiment-14/runs/language=java_model=sonnet_prompt=ATDD/rep1
# Mechanical scores (do not re-run toolchain):
cat scores.json
sqlite3 -readonly ../../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id=(SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='java' AND json_extract(er.run_config_json,'\$.model')='sonnet' AND json_extract(er.run_config_json,'\$.prompt')='ATDD' AND er.replicate=1 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
# Test/skip inventory:
grep -rc '@Test' src/test --include='*.java'
grep -rnE '@Disabled|@Ignore|assumeTrue' src/test --include='*.java'
```
