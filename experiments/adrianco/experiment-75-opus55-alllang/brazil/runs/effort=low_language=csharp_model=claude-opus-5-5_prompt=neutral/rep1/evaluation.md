# Evaluation: effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=csharp, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** all pass / 0 failed / 0 skipped (test_coverage=1.0 from scores.json) — 41 test methods (38 `[Fact]` + 3 `[Theory]`, 25 `[InlineData]` ⇒ ~63 executable cases)
- **Build:** pass (test_coverage=1.0 ⇒ build+tests ran; not re-run per skill)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

Source: pinned `brazil/REQUIREMENTS.json` (constant 12-item denominator across runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/SoccerMcp/McpServer.cs:25` JSON-RPC initialize/tools/list/tools/call; `Tools.cs:30` 15 tool defs; verified by `McpProtocolTests.cs` |
| R2 | Loads/uses datasets in data/kaggle | ✓ implemented | `src/SoccerMcp/DataStore.cs:41` Load reads all 6 CSVs; `QueryScenarios.cs:20` asserts row counts |
| R3 | Match query by team (home/away/either) | ✓ implemented | `SoccerService.cs:67-73` venue-aware team filter; `search_matches` tool `Tools.cs:83` |
| R4 | Filter by date range and/or season | ✓ implemented | `SoccerService.cs:45-48` season+from/to; `QueryScenarios.cs:49,65` |
| R5 | Filter by competition | ✓ implemented | `SoccerService.cs:44` + `Competitions.Parse` `Data.cs:31`; Brasileirão/Copa/Libertadores |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `SoccerService.cs:106` GetTeamRecord / `TeamRecord` `SoccerService.cs:6`; `QueryScenarios.cs:91` |
| R7 | Player search by name | ✓ implemented | `SoccerService.cs:208` SearchPlayers(name); `QueryScenarios.cs:207` (Neymar) |
| R8 | Filter players by nationality/club, with ratings | ✓ implemented | `SoccerService.cs:217-243` nationality/club/position/min_overall; `QueryScenarios.cs:200,216` |
| R9 | Standings computed from match results | ✓ implemented | `SoccerService.cs:153` GetStandings (points from W/D); `QueryScenarios.cs:132` (2019 Flamengo 90 pts) |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `SoccerService.cs:181` GetCompetitionStats, `:174` BiggestWins; `QueryScenarios.cs:164,181` |
| R11 | Head-to-head between two teams | ✓ implemented | `SoccerService.cs:80` GetHeadToHead; `QueryScenarios.cs:116` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 3 test files, ~63 cases, test_coverage=1.0 |

## Build & Test

Not re-run — stored scores read from `scores.json` (skill step 2, avoids duplicate toolchain runs):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.6998, "idiomatic": 0.88, "token_efficiency": 0.0138}
```

test_coverage=1.0 ⇒ `dotnet build` + `dotnet test` succeeded with all tests passing.
No skipped/ignored tests found (grep for `Skip=`, `[Fact(Skip`, `[Theory(Skip` → none).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests, .cs excl obj/bin) | 1,345 |
| Source modules | 6 |
| Test files | 3 (+ fixture) |
| Files (excl obj/bin/data/.git) | 23 |
| MCP tools | 15 |
| Tests total (methods) | 41 (38 Fact + 3 Theory); ~63 cases with InlineData |
| Tests effective (pass+fail, skips excluded) | ~63 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] Relegation tag assumes a 20-team full-season table — `Tools.cs:128,131` (R9 otherwise fully satisfied)
2. [low] Very terse helpers reduce readability — `Tools.cs:22-26` (`S`/`I`/`D`/`l0`); stored maintainability=0.70
3. [info] MCP server is hand-rolled JSON-RPC, not the official MCP SDK — `McpServer.cs:7` (acceptable per R1)
4. [info] 15 tools, well beyond the spec's query categories — `Tools.cs:30`
5. [info] Cross-dataset dedup + single-source-per-season standings avoid double counting — `SoccerService.cs:37,145`

## Reproduce

```bash
cd experiments/adrianco/experiment-75-opus55-alllang/brazil/runs/effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral/rep1
cat scores.json                    # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json     # pinned 12-item checklist
grep -rnE "Skip=|\[Fact\(Skip|\[Theory\(Skip" tests/ --include="*.cs"   # → none
find src tests -name '*.cs' -not -path '*/obj/*' -not -path '*/bin/*' | xargs wc -l | tail -1
# Full re-run (optional, slow): dotnet test
```
