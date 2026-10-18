# Evaluation: effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=csharp, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `brazil/REQUIREMENTS.json`)
- **Tests:** build + all tests pass (`test_coverage=1.0` from `scores.json`); 36 test methods across 6 files, 0 skipped
- **Build:** pass — `test_coverage=1.0 ⇒ build succeeded` (not re-run; read from `scores.json`)
- **Lint:** pass — `code_quality=0.9833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Stored scores (`scores.json`): test_coverage=1.0, defect_rate=1.0, code_quality=0.9833, maintainability=0.8175, idiomatic=0.90, token_efficiency=0.0167.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `Mcp/McpServer.cs` JSON-RPC 2.0 over stdio (initialize/ping/tools/list/tools/call); `Program.cs:21` wires 6 tools |
| R2 | Loads provided `data/kaggle/` datasets | ✓ implemented | `Data/DatasetLoader.cs:31` reads all 6 CSVs via `Csv/CsvReader.cs`; `Program.cs:9` defaults to `./data/kaggle` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `search_matches` tool `Mcp/SoccerTools.cs:23`; `SoccerDatabase.FindMatches` venue filter `SoccerDatabase.cs:62` |
| R4 | Filter by date range and/or season | ✓ implemented | `SoccerDatabase.cs:80` `From`/`To`; season via `InCompetition` `SoccerDatabase.cs:242` |
| R5 | Filter by competition | ✓ implemented | `InCompetition` substring match `SoccerDatabase.cs:234`; competitions labelled in `DatasetLoader.cs:11-21` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `get_team_stats` `SoccerTools.cs:41`; `GetTeamStats`/`Summarize` `SoccerDatabase.cs:87,246` |
| R7 | Player search by name | ✓ implemented | `search_players` name filter `SoccerDatabase.cs:183` (accent-folded via `TextNormalizer`) |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `SoccerDatabase.cs:189-206` nationality/club/position/min_overall; ratings in `Domain/Models.cs` Player |
| R9 | Season standings from match results | ✓ implemented | `get_standings` `SoccerTools.cs:67`; `GetStandings` computes 3-1-0 points `SoccerDatabase.cs:122` |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `get_league_stats` `SoccerTools.cs:79`; `GetLeagueSummary` `SoccerDatabase.cs:137` |
| R11 | Head-to-head between two teams | ✓ implemented | `head_to_head` tool `SoccerTools.cs:55`; `GetHeadToHead` `SoccerDatabase.cs:95` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 6 xUnit files incl. `SoccerDatabaseTests.cs`, `McpServerTests.cs`, `SampleQuestionTests.cs`; `test_coverage=1.0` |

## Build & Test

Not re-run — scores read from `scores.json` (per evaluate-run skill step 2):

```text
test_coverage = 1.0   ⇒ build succeeded and all tests passed
defect_rate   = 1.0   ⇒ build+test success
code_quality  = 0.9833 (lint/quality)
```

Skip scan (xUnit `Skip=`, `[Ignore]`, `Assert.Skip`, `.Skip(`): 0 matches in `tests/`.
Test methods (`[Fact]`/`[Theory]`): 36. Effective tests = all 36 (none skipped).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, excl. obj/bin) | 1927 (prod 1266 / test 661) |
| Source files (.cs, excl. obj/bin) | 18 |
| Project files total (excl. obj/bin/.git/data) | 31 |
| Production dependencies | 0 (hand-rolled JSON-RPC + CSV reader) |
| Test dependencies | 3 (xunit, xunit.runner.visualstudio, Microsoft.NET.Test.Sdk) |
| Tests total | 36 |
| Tests effective | 36 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`) — none above `low`:

1. [low] Cross-file match dedup can collapse two distinct same-day meetings (`SoccerDatabase.cs:24` — fingerprint omits competition)
2. [info] Player position filter requires an exact FIFA position code (`SoccerDatabase.cs:203`)
3. [info] Standings aggregate any competition substring across all source files (`SoccerDatabase.cs:122`)

All three are design/edge-case observations, not spec violations; the run fully implements the pinned requirement set.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json                    # pinned 12-requirement checklist
grep -rnE "Skip\s*=|\[Ignore\]|Assert\.Skip|\.Skip\(" tests/ --include="*.cs"   # skip scan (0)
grep -rhoE "\[Fact|\[Theory" tests/ --include="*.cs" | wc -l                      # 36 test methods
find src tests -name "*.cs" -not -path "*/obj/*" -not -path "*/bin/*" -exec cat {} + | wc -l   # LOC
```
