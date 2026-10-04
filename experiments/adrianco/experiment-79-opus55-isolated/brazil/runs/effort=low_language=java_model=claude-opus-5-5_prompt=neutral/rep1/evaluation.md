# Evaluation: effort=low_language=java_model=claude-opus-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=claude-opus-5-5, prompt=neutral, effort=low (agent/framework: unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`)
- **Tests:** 42 passed / 0 failed / 0 skipped (42 effective) — from `test_coverage=1.0`
- **Build:** pass — from `scores.json` (`test_coverage=1.0`, `defect_rate=1.0`); toolchain not re-run per skill
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Denominator is the fixed 12-entry checklist in `brazil/REQUIREMENTS.json` (used verbatim).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `McpServer.java:44` serve/handle (JSON-RPC 2.0 stdio), `:130` tools/list, `:142` tools/call, `:235` 15 tools registered; tests `McpServerTest` initialize/toolsList/errors/stdio |
| R2 | Load & use datasets in data/kaggle/ | ✓ implemented | `DataStore.java:28-33,163-230` reads all 6 CSVs via `Csv.read`; `:64` defaults to `data/kaggle`; test `NormalizationTest.csvParsing`, `McpServerTest.allFilesLoaded` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `QueryService.java:456` filter() with `venue` home/away/either; `:517` searchMatches; test `QueryServiceTest.byTeamAndSeason`, `betweenTwoTeams` |
| R4 | Filter by date range and/or season | ✓ implemented | `QueryService.java:472-473` season + from/to date predicate; test `byDateRangeAndVenue` |
| R5 | Filter by competition (Serie A/B/C, Copa, Libertadores) | ✓ implemented | `QueryService.java:443` resolveCompetition; `DataStore` loads Brasileirão/Cup/Libertadores/Extended; tests `cupFinals`, `libertadoresFinal`, `serieB` |
| R6 | Team match history W/L/D + goals for/against | ✓ implemented | `QueryService.java:353` Rec.add, `:574` teamStats; tests `seasonStats`, `homeRecord` |
| R7 | Player search by name | ✓ implemented | `QueryService.java:885` findPlayers, `:911` searchPlayers; test `QueryServiceTest.byName` |
| R8 | Filter players by nationality/club with ratings | ✓ implemented | `QueryService.java:900-903` nationality/club/position filters, sorts by `overall`; tests `brazilians`, `byClubAndPosition`, `byClub` |
| R9 | Season standings computed from match results | ✓ implemented | `QueryService.java:630` standingsTable, `:644` standings (3pts/win, computed); test `tablesConsistent` |
| R10 | Aggregate statistics | ✓ implemented | `QueryService.java:746` aggregate, `:756` aggregateLines (avg goals, home/away/draw rates), `:731` biggestWins; tests `averages`, `biggestWins`, `compareSeasons` |
| R11 | Head-to-head between two teams | ✓ implemented | `QueryService.java:539` headToHead, `:532` h2hLine; tests `headToHead`, `betweenTwoTeams` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 42 `@Test` across 3 test classes; `test_coverage=1.0` (all execute & pass) |

Enhancements beyond spec (not deductions): 15 tools including `team_rankings`, `derbies`,
`knockout_stages`, `compare_seasons`, `players_by_club`, `club_profile`; accent/suffix-insensitive
team-name normalization (`TeamNames`, `NormalizationTest`).

## Build & Test

Not re-run — the mechanical scorers already ran the toolchain and stored results.

```text
scores.json (this run's archive):
  test_coverage = 1.0   -> mvn build + all tests passed (42 tests, JUnit 5)
  defect_rate   = 1.0   -> build + test succeeded
  code_quality  = 1.0   -> lint/quality gate clean
  maintainability = 0.5754
  idiomatic     = 0.7
  token_efficiency = 0.0353
```

Skip detection: `grep` for `@Disabled|@Ignore|assumeTrue|assumeFalse` in `src/test` → none.
No `@ParameterizedTest`/`@RepeatedTest`. 42 static `@Test` methods, all effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, source only) | 1747 |
| Lines of code (test) | 672 |
| Source files (excl. data/, build) | 24 |
| Dependencies (pom.xml) | 1 (junit-jupiter, test scope) |
| Tests total | 42 |
| Tests effective | 42 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] QueryService.java is a single 691-line class — `QueryService.java:334` (maintainability=0.5754)
2. [info] MCP protocol and JSON are hand-rolled, not via an SDK — `McpServer.java:44`, `Json.java:1`
3. [info] Implementation exceeds the spec with 15 tools — `McpServer.java:235`

No critical, high, or medium findings. The run passes the conformance gate and the test gate.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-79-opus55-isolated/brazil/runs/effort=low_language=java_model=claude-opus-5-5_prompt=neutral/rep1
cat scores.json                                   # stored mechanical scores (do not re-run toolchain)
cat ../../../REQUIREMENTS.json                     # pinned 12-requirement checklist
grep -rE "@Test" src/test | wc -l                  # 42
grep -rnE "@Disabled|@Ignore|assumeTrue|assumeFalse" src/test   # none
# Optional full re-run: mvn -q test
```
