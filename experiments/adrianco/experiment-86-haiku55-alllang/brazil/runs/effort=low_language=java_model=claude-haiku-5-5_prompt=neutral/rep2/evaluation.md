# Evaluation: effort=low_language=java_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=java, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 40 passed / 0 failed / 0 skipped (40 effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (build + all tests passed)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Clean run. Build and tests pass (`test_coverage=1.0`, `defect_rate=1.0`), quality is maximal (`code_quality=1.0`), and every pinned requirement is implemented and exercised by tests — including real-dataset checks (2019 Brasileirão champion, a performance bound). No skipped or disabled tests.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `mcp/McpServer.java:61-83` (JSON-RPC lifecycle + tools/call); 7 tools `mcp/SoccerTools.java:180-241` |
| R2 | Load & use data/kaggle datasets | ✓ implemented | `data/DataRepository.java:33-40` loads all 6 CSVs; `data/DataLoader.java` converts rows |
| R3 | Match query by team (home/away/either) | ✓ implemented | `query/SoccerQueries.java:540-545,696-709` + `Venue`; tested `SoccerQueriesTest:27,53` |
| R4 | Filter by date range and/or season | ✓ implemented | `MatchFilter` from/to/season `SoccerQueries.java:514,687-694`; tested `SoccerQueriesTest:40` |
| R5 | Filter by competition | ✓ implemented | competition filter `SoccerQueries.java:683-685`; Série A/Cup/Libertadores loaded `DataLoader.java:32-75` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `SoccerQueries.teamRecord:548-560` + `TeamTally`; tested `SoccerQueriesTest:66` |
| R7 | Player search by name | ✓ implemented | `SoccerQueries.searchPlayers:663-676` name filter; tested `SoccerQueriesTest:151` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `PlayerFilter` nationality/club/min_overall `SoccerQueries.java:667-672`; tested `SoccerQueriesTest:138` |
| R9 | Season standings from match results | ✓ implemented | `SoccerQueries.standings:593-608` computes points table; tested `SoccerQueriesTest:99,163` (2019 champion) |
| R10 | Aggregate statistics | ✓ implemented | `SoccerQueries.leagueStats:632-661` (avg goals, home/draw/away %, biggest wins); tested `SoccerQueriesTest:113` |
| R11 | Head-to-head between two teams | ✓ implemented | `SoccerQueries.headToHead:562-590`; tested `SoccerQueriesTest:83` |
| R12 | Automated tests for query capabilities | ✓ implemented | 40 `@Test` across 6 files; `test_coverage=1.0` (all pass) |

## Build & Test

Scores read from `scores.json` (computed by retort's scorers during the run — not re-run here):

```text
test_coverage = 1.0   # build succeeded and all tests passed
defect_rate   = 1.0   # build + test success
code_quality  = 1.0   # lint/quality maximal
maintainability = 0.850
idiomatic     = 0.600
```

Test inventory (static): 40 `@Test` methods, 0 `@Disabled`/`assumeTrue`/`@Ignore` → 40 effective, 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, src/ *.java) | 1988 |
| Files (main Java / test Java) | 11 / 7 |
| Dependencies (pom.xml) | 2 (jackson-databind, junit-jupiter) |
| Tests total | 40 |
| Tests effective | 40 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=1.0) |

## Findings

All 3 findings are informational (strengths / a minor semantic nuance); none affect scoring:

1. [info] Full MCP lifecycle over stdio JSON-RPC 2.0 with 7 tools (R1)
2. [info] All 6 CSVs loaded and cross-source de-duplicated (R2)
3. [info] `competition_standings` builds a points table for any competition, including knockout cups where standings are not meaningful

## Reproduce

```bash
cd experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=java_model=claude-haiku-5-5_prompt=neutral/rep2
cat scores.json                                   # stored build/test/lint scores (do not re-run)
find src -name '*.java' | xargs wc -l | tail -1   # LOC
grep -rE "@Test" src/test --include='*.java' | wc -l            # test count (40)
grep -rnE "@Disabled|assumeTrue|@Ignore" src/test --include='*.java' | wc -l   # skips (0)
```
