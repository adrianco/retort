# Evaluation: agent=hermes-local language=go model=Qwen3-Coder-Next-4bit prompt=neutral stack=m80 · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Task:** brazilian-soccer-mcp-server (**REPAIR** run — prior attempt failed for "No MCP server implemented", requirement_coverage 0.92)
- **Status:** ok — build + tests passed (defect_rate=1.0, test_coverage=0.639 from scores.json)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** executed and passed (test_coverage=0.639), 32 test funcs, 1 conditional skip, 31 effective
- **Build:** pass (defect_rate=1.0 from scores.json — not re-run)
- **Lint:** pass (code_quality=1.0 from scores.json); idiomatic=0.78, maintainability=0.51
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 1 high, 3 medium, 2 low)

The repair succeeded on its central goal: the prior attempt shipped no MCP server;
this run wires a real one using `github.com/modelcontextprotocol/go-sdk` v1.6.1
(`mcp.NewServer` + 16 `mcp.AddTool` registrations + `StdioTransport`) in
`cmd/main.go`. All 12 pinned requirements are now satisfied and the test gate passes.
Remaining findings are quality/robustness issues, not requirement failures.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `cmd/main.go:29` `mcp.NewServer`; `:43-337` `addTools` registers 16 tools; `:38` `StdioTransport` |
| R2 | Load datasets from data/kaggle | ✓ implemented | `store/loader.go:32` `LoadAll` reads all 6 CSVs; `cmd/main.go:17` `"./data/kaggle"` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `store/database.go:56` `FindMatchesByTeam` matches Home or Away; tool `find_matches_by_team` |
| R4 | Filter by date range and/or season | ✓ implemented | `database.go:56` season filter; `:72` `FindMatchesByDateRange`; tool `find_matches_by_season` |
| R5 | Filter by competition | ✓ implemented | `database.go:107` `FindMatchesByCompetition`; tool `find_matches_by_competition` (heuristic fallback — see finding) |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `database.go:204` `GetTeamStats`; tool `get_team_stats` |
| R7 | Player search by name | ✓ implemented | `database.go:145/156` `FindPlayerByName`/`FindPlayersByName`; tool `find_player_by_name` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `database.go:168/180` nationality/club filters; `Player.Overall` returned; tools present |
| R9 | Season standings computed from matches | ✓ implemented | `database.go:336` `CalculateLeagueStandings` (points from results); tool `get_league_standings` |
| R10 | Aggregate stats | ✓ implemented | `database.go:439` avg goals, `:466` home win rate, `:291` big wins; tools present |
| R11 | Head-to-head between two teams | ✓ implemented | `database.go:255` `GetHeadToHead`; tool `get_head_to_head` |
| R12 | Automated tests | ✓ implemented | `store/store_test.go`, `server/server_test.go`; test_coverage=0.639>0 — but see hardcoded-path finding |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (skill step 2):

```text
scores.json: {"code_quality":1.0, "token_efficiency":0.0096, "test_coverage":0.639,
              "defect_rate":1.0, "maintainability":0.506, "idiomatic":0.78}
```

`defect_rate=1.0` ⇒ build + tests succeeded at run time; `test_coverage=0.639` ⇒ tests
executed and measured coverage. Caveat: the tests hardcode absolute paths under
`~/.retort/work/retort-local-0xabe5kx/retort-*/data/kaggle` (those temp dirs still
exist on this machine, so a re-run would still pass here, but the suite is not
portable — see the high finding).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, source + tests) | 2523 (cloc, all .go) |
| Go files | 8 |
| Dependencies (go.sum modules) | 10 (1 direct: modelcontextprotocol/go-sdk) |
| Tests total | 32 funcs |
| Tests effective (asserting) | ~13 with behavioural assertions |
| Skips | 1 (conditional) |
| MCP tools registered | 16 |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] All tests hardcode ephemeral absolute data paths instead of `./data/kaggle` — non-portable; R12 only verifiable on the original run's temp dir (`store_test.go:9`, `server_test.go:11`).
2. [medium] `CalculateLeagueStandings` conflates Brasileirao and historical datasets (empty-Tournament matches counted for any competition) — standings can double-count (`database.go:353`).
3. [medium] `GetTeamStats(team, 0)` drops all seasoned matches, so `CompareTeams` stats are near-empty (`database.go:209`).
4. [medium] Most tests print rather than assert — only ~13 of 32 check returned values.
5. [low] `format*Text` helpers duplicated across `cmd/main.go` and `internal/server/server.go`.
6. [low] `TestFormatPlayerText` conditionally skips instead of failing on missing player (`server_test.go:294`).

## Reproduce

```bash
cd experiments/adrianco/experiment-50-brazil-80b-uncapped/brazil/runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1
cat scores.json                                    # mechanical scores (build/test/lint — not re-run)
grep -rn "t\.Skip(" --include="*.go" .             # skip detection
grep -rn "\.retort/work" --include="*.go" .        # hardcoded test-data paths
cloc . --exclude-dir=.git,summary                  # LOC
# build/test intentionally NOT re-run — scores.json already has them (skill step 2)
```
