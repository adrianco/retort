# Evaluation: effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** build + all tests pass (defect_rate=1.0 from scores.json); ~40 xUnit Fact/Theory cases (19 InlineData rows), 0 skipped
- **Build:** pass (defect_rate=1.0, test_coverage=0.83 from scores.json — not re-run)
- **Lint:** pass — code_quality=0.9833 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Clean run. All 12 pinned requirements implemented with a well-layered, hand-rolled MCP server
(`McpServer` JSON-RPC ↔ `SoccerTools` ↔ pure `SoccerQueries` ↔ `DataLoader` over all 6 CSVs),
backed by a test suite exercising every query capability and the full protocol loop.

## Requirements

Checklist from pinned `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `McpServer.cs` initialize/tools/list/tools/call over stdio; 7 tools in `SoccerTools.cs:14` |
| R2 | Loads provided data/kaggle datasets | ✓ implemented | `DataLoader.Load` reads all 6 CSVs (`DataLoader.cs:46`); `Program.cs` resolves `data/kaggle` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `SoccerQueries.SearchMatches` + `TeamInvolved`/`Venue` (`SoccerQueries.cs:58`) |
| R4 | Filter by date range / season | ✓ implemented | `SearchMatches` Season/From/To filters (`SoccerQueries.cs:63-65`) |
| R5 | Filter by competition | ✓ implemented | `CompetitionMatches` substring (`SoccerQueries.cs`); Brasileirão/Copa do Brasil/Libertadores normalized in `DataLoader` |
| R6 | Team W/L/D record + goals | ✓ implemented | `GetTeamRecord` → `TeamRecord` (`SoccerQueries.cs:70`); `team_record` tool |
| R7 | Player search by name | ✓ implemented | `SearchPlayers(name:…)` (`SoccerQueries.cs:160`); `search_players` tool |
| R8 | Players by nationality/club + ratings | ✓ implemented | `SearchPlayers` nationality/club/position/min_overall filters |
| R9 | Season standings from match results | ✓ implemented | `GetStandings` win 3/draw 1 computed table (`SoccerQueries.cs:117`); test asserts Flamengo 90 pts 2019 |
| R10 | Aggregate statistics | ✓ implemented | `GetMatchStatistics` avg goals/home-away rates/biggest wins (`SoccerQueries.cs:140`) |
| R11 | Head-to-head between two teams | ✓ implemented | `GetHeadToHead` → W/L/D + match list (`SoccerQueries.cs:95`); `head_to_head` tool |
| R12 | Automated tests for query capabilities | ✓ implemented | `SoccerQueriesTests` (16) + `McpServerTests` (9) + loader/csv/teamname tests; all pass, 0 skipped |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate; run not yet in retort.db):

```text
scores.json: defect_rate=1.0 (build + tests passed), test_coverage=0.83,
             code_quality=0.9833, maintainability=0.8078, idiomatic=0.62
```

Test inventory (grep, read-only):

```text
~40 [Fact]/[Theory] + 19 [InlineData] across 6 test files
0 skipped/ignored (no Skip=, [Fact(Skip, Ignore, or Assert.True(true))
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src, .cs excl obj/bin) | 1084 |
| Lines of code (tests) | 517 |
| Source files (excl data/obj/bin/logs) | 25 |
| Dependencies (test-only NuGet) | 4 (xunit, xunit.runner.visualstudio, Microsoft.NET.Test.Sdk, coverlet.collector) |
| Tests total (Fact/Theory attrs) | ~40 (+19 InlineData cases) |
| Tests effective | all (0 skipped) |
| Skip ratio | 0% |
| test_coverage (stored) | 0.83 |

Production code has zero external dependencies — MCP protocol and CSV parsing are hand-rolled on the BCL.

## Findings

Full list in `findings.jsonl` (none at high/critical):

1. [low] Fixture de-dup key (comp, year, homeKey, awayKey, goals) could merge two distinct same-season same-score fixtures — `DataLoader.cs:140`
2. [info] MCP server hand-rolled rather than official SDK — valid, honors 2024-11-05 contract — `McpServer.cs:12`
3. [info] Extended BR-Football columns (corners/shots/attacks) not surfaced in stats — `DataLoader.cs:72`

## Reproduce

```bash
cd experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral/rep1
cat scores.json                                   # stored mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json                    # pinned 12-item checklist
grep -rnE 'Skip=|\[Fact\(Skip|Ignore' tests/      # skip detection (none)
find src -name '*.cs' -not -path '*/obj/*' -not -path '*/bin/*' | xargs wc -l
```
