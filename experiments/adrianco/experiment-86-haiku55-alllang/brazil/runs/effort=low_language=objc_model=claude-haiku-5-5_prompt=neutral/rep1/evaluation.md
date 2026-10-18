# Evaluation: effort=low_language=objc_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 40 scenarios / 153 checks, 0 failed, 0 skipped (all 5 data-gated scenarios ran — data present)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass — code_quality=1.0 from scores.json (clang `-Wall -Wextra`, ARC, clean)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores (scores.json): `test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`,
`maintainability=0.750`, `idiomatic=0.600`, `token_efficiency=0.0139`.

## Requirements

Checklist is the pinned `brazil/REQUIREMENTS.json` (12 entries, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/MCPServer.m` — JSON-RPC 2.0, `initialize`/`tools/list`/`tools/call`/`ping`, 8 tools in `+toolDefinitions`; stdio transport `-runWithInput:output:` |
| R2 | Loads & uses data/kaggle/ datasets | ✓ implemented | `src/SoccerDataset.m -loadDirectory:`; all 6 CSVs present in `data/kaggle/`; test `Scenario_AllSixFilesLoad` loads 18,207 players + 5 match sources |
| R3 | Match query by team (home/away/either) | ✓ implemented | `QueryEngine -searchMatches:limit:error:` + `MatchFilter.teamQuery`/`.venue` (MatchVenueHome/Away/Any) |
| R4 | Filter by date range / season | ✓ implemented | `MatchFilter.season`/`.fromDate`/`.toDate`; test `Scenario_FilterMatchesByDateRange` |
| R5 | Filter by competition | ✓ implemented | `MatchFilter.competitionQuery`; `SoccerText +competitionForQuery:` resolves Brasileirão/Copa do Brasil/Libertadores; test `Scenario_FilterMatchesByCompetition` |
| R6 | Team record W/L/D + goals for/against | ✓ implemented | `QueryEngine -teamRecord:error:`; tests `Scenario_TeamHomeRecord`/`TeamAwayRecord` |
| R7 | Player search by name | ✓ implemented | `QueryEngine -searchPlayersNamed:...` name arg; tool `search_players` |
| R8 | Players by nationality/club + ratings | ✓ implemented | same method: `nationality`/`club`/`minOverall`; test `Scenario_FindBrazilianForwards` returns Neymar Jr |
| R9 | Season standings computed from results | ✓ implemented | `QueryEngine -standingsForCompetition:season:error:` (3 pts win/1 draw); test `Scenario_RealStandings2019` asserts Flamengo 90 pts, Santos/Palmeiras 74, 20 clubs |
| R10 | Aggregate statistics | ✓ implemented | `-leagueStats:` (avg goals, home/draw/away %), `-biggestWins:limit:`; tests `Scenario_LeagueStatisticsAverages`/`BiggestWinsOrderedByMargin` |
| R11 | Head-to-head between two teams | ✓ implemented | `QueryEngine -headToHead:error:`; tool `head_to_head`; test `Scenario_HeadToHeadSummary` |
| R12 | Automated tests over the queries | ✓ implemented | `tests/test_main.m` 40 scenarios / 153 checks; test_coverage=1.0 |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill (test_coverage=1.0 ⇒ build + all
tests passed). Build is `make` (Foundation only, ARC, clang `-Wall -Wextra -O2`); tests
`make test`. The agent's own final run logged:

```text
40 scenarios, 0 failed; 153 checks, 0 failed
```

(An earlier mid-development run showed `40 scenarios, 2 failed`; the agent fixed both before finishing.)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: src/*.m + *.h) | 1,639 |
| Lines of code (tests) | 736 |
| Files (src + tests + Makefile) | 12 |
| Dependencies | 0 (Foundation only) |
| Tests total (scenarios) | 40 |
| Tests effective | 40 (0 skipped in scored run) |
| Checks | 153 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`. No critical/high/medium/low — both items are info:

1. [info] 5 integration scenarios self-skip when `data/kaggle` is absent (they ran here; signal for cross-run comparison).
2. [info] Cross-source match de-duplication beyond spec (2019 Brasileirão → exactly 380 matches, real table).

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=objc_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                      # stored mechanical scores (build/test/lint)
make                                 # build (Foundation only, ARC)
make test                            # 40 scenarios / 153 checks
```
