# Evaluation: language=java model=sonnet prompt=TDD · rep 1

## Summary

- **Factors:** language=java, model=sonnet, prompt=TDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 27 passed / 0 failed / 0 skipped (27 effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 3 low, 1 info)

Mechanical scores read from `experiment-14/runs/.../rep1/scores.json` (not re-run, per skill):
`test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.641`, `idiomatic=0.58`, `token_efficiency=0.047`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `BrazilianSoccerMcpServer.java` — `McpServer.sync(...)` registers 6 tools |
| R2 | Loads provided datasets in data/kaggle/ | ✓ implemented | `MatchLoader.loadAll()` reads 5 CSVs; `PlayerLoader.loadAll()` reads `fifa_data.csv` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `MatchService.findByTeam` via `TeamNameNormalizer.matches` on home & away |
| R4 | Filter by date range and/or season | ✓ implemented | `MatchService.findBySeason` + `find_matches` season filter (season satisfies and/or; no calendar range — see finding `date-range`) |
| R5 | Filter by competition | ✓ implemented | Loaders tag `competition`; `find_matches` filters on it |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `StatisticsService.getTeamRecord` → `get_team_stats` tool |
| R7 | Player search by name | ✓ implemented | `PlayerService.findByName` → `find_players` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `findByNationality` / `findByClub`; output includes overall/potential |
| R9 | Standings computed from match results | ✓ implemented | `StatisticsService.getStandings` computes points from W/D/L |
| R10 | Aggregate statistics | ✓ implemented | `getAverageGoalsPerMatch`, `getBiggestWins` |
| R11 | Head-to-head between two teams | ✓ implemented | `StatisticsService.getHeadToHead` → `get_head_to_head` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 27 JUnit 5 tests across loaders/services; `test_coverage=1.0` |

**Prompt factor (TDD):** test-first structure is consistent with the prompt — 6 dedicated test files thoroughly cover the loader and service layers with concrete value assertions (e.g. `StatisticsServiceTest.testGetTeamRecord` checks exact W/D/L and goals). Gap: the MCP tool-handler layer in `BrazilianSoccerMcpServer` is not directly tested (finding `handler-tests`).

## Build & Test

Not re-run — mechanical scores were read from `scores.json` per the evaluate-run skill (re-running the JVM toolchain is pure duplication).

```text
scores.json: test_coverage=1.0  →  build + all tests passed
             code_quality=1.0   →  lint clean
27 @Test methods, 0 @Disabled/@Ignore/assume → 27 effective tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, source only) | 794 |
| Lines of code (test) | 213 |
| Files (src) | 15 |
| Dependencies (pom `<dependency>`) | 3 (mcp sdk, opencsv, junit-jupiter) |
| Tests total | 27 |
| Tests effective | 27 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] MCP tool-handler layer has no unit tests — handlers in `BrazilianSoccerMcpServer.java` carry untested arg/filter/format logic.
2. [medium] Blank/NaN goals and seasons parse to 0 (`MatchLoader.java:30`), conflating missing data with 0-0 and skewing aggregates.
3. [low] Match filtering supports season only, not a calendar date range (`MatchService.java`).
4. [low] Several public service methods unused by the server (dead code).
5. [low] Competition filter requires an exact `equalsIgnoreCase` name.

## Reproduce

```bash
cd experiment-14/runs/language=java_model=sonnet_prompt=TDD/rep1
cat scores.json                                  # mechanical scores (build/test/lint)
grep -rE "@Test" src/test | wc -l                # 27
grep -rEn "@Disabled|@Ignore|assume" src/test    # 0 skips
# Optional re-run (not required; slow): mvn -q test
```
