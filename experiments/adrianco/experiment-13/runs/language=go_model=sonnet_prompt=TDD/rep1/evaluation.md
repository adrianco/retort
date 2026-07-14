# Evaluation: language=go_model=sonnet_prompt=TDD · rep 1

## Summary

- **Factors:** language=go, model=sonnet, prompt=TDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+ prompt instruction P1 followed)
- **Tests:** 47 passed / 0 failed / 0 skipped (47 effective) — coverage 78.7%
- **Build:** pass (test_coverage=0.787 from scores.json ⇒ build + tests ran)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** `run-summary` skill unavailable in this environment — see module notes below
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 2 info)

Pinned checklist used: `experiment-13/REQUIREMENTS.json` (12 fixed requirements). Prompt factor `TDD` (`experiment-13/prompts/TDD.md`) adds P1.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools/handlers | ✓ implemented | `server.go` JSON-RPC 2.0: initialize/tools/list/tools/call (`server.go:103`), 6 tools in `allTools()` `server.go:485`; `server_test.go` TestServerInitialize/ToolsList/ToolCall* |
| R2 | Loads & uses datasets in `data/kaggle/` | ✓ implemented | `loadAllData` `loader.go:288` reads all 6 CSVs; `loader_test.go` TestParse{Brasileirao,Cup,Libertadores,BRFootball,Historical,FIFA}CSV |
| R3 | Match query: by team (home/away/either) | ✓ implemented | `SearchMatches` Team filter `queries.go:36`; TestSearchMatchesByTeam, ByHomeAndAway |
| R4 | Match query: date range and/or season | ✓ implemented | `queries.go:31,49-54`; TestSearchMatchesBySeason, ByDateRange |
| R5 | Match query: by competition | ✓ implemented | `competitionKey` `normalize.go:161` + filter `queries.go:28`; TestSearchMatchesByCompetition |
| R6 | Team query: W/L/D record + goals for/against | ✓ implemented | `GetTeamStats` `queries.go:152`; TestGetTeamStatsBasic/HomeOnly/BySeason |
| R7 | Player query: search by name | ✓ implemented | `SearchPlayers` Name filter `queries.go:295`; TestSearchPlayersByName |
| R8 | Player query: nationality/club + ratings | ✓ implemented | `queries.go:298-309` returns Overall/Potential; TestSearchPlayersByNationality/ByClub/ByMinOverall |
| R9 | Competition: standings computed from matches | ✓ implemented | `GetStandings` `queries.go:209` accumulates points from results; TestGetStandings/Sorted |
| R10 | Statistical analysis (avg goals, home vs away, biggest wins) | ✓ implemented | `GetStatistics` `queries.go:341`; TestGetStatisticsGoalsPerMatch/BiggestWins/HomeWinRate |
| R11 | Head-to-head between two teams | ✓ implemented | `GetHeadToHead` `queries.go:89`; TestGetHeadToHead/Goals |
| R12 | Automated tests covering query capabilities | ✓ implemented | 47 Test funcs, test_coverage=0.787 (>0); 0 skips |
| P1 | Follow TDD (test-first, incremental) | ✓ followed (outcome) | Thorough one-behavior-per-test unit suite across all layers; fixture `testDB()` `queries_test.go:7`. Process (red/green sequencing) not verifiable from the final artifact, but the result conforms |

## Build & Test

Scores read from `scores.json` (computed during scoring; not re-run per skill guidance):

```text
test_coverage = 0.787   # build + tests executed and passed; 78.7% coverage
code_quality  = 1.0     # lint/quality clean
defect_rate   = 1.0     # build+test succeeded
idiomatic     = 0.7
maintainability = 0.583
```

```text
go test ./...   (not re-run; stored test_coverage=0.787)
47 Test functions, 0 t.Skip — all effective
  loader_test.go: 6   server_test.go: 11   normalize_test.go: 6   queries_test.go: 24
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go source, excl. tests) | 1647 |
| Lines of code (tests) | 825 |
| Source files (Go) | 7 (loader, normalize, queries, server, types, main + tests) |
| Total files (excl .git) | 26 (incl. 6 data CSVs + built binary) |
| Dependencies | 0 external (stdlib only) |
| Tests total | 47 |
| Tests effective | 47 |
| Skip ratio | 0% |
| Coverage | 78.7% |

## Findings

Top findings (full list in `findings.jsonl`) — no critical/high/medium items:

1. [info] P1 — TDD prompt satisfied in outcome: one-behavior-per-test suite across loader/server/normalize/queries
2. [info] R12 — Test coverage 78.7% with all query capabilities exercised, 0 skips
3. [low] Q1 — `json.Unmarshal` errors ignored in tool argument decoding (`server.go:213,260,...`)
4. [low] Q2 — Standings team-alias mapping hardcoded (`normalize.go:96-146`)
5. [low] Q3 — Date-range filter uses lexical string comparison; unparsed dates compare incorrectly (`queries.go:49-54`)

## Reproduce

```bash
cd experiment-13/runs/language=go_model=sonnet_prompt=TDD/rep1
cat scores.json                      # stored mechanical scores (no re-run)
grep -rE "^func Test" *.go | wc -l   # 47 test functions
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
# Full re-verify (optional, slow): go test ./...
```
