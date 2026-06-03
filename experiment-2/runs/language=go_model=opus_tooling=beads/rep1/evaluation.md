# Evaluation: language=go_model=opus_tooling=beads · rep 1

## Summary

- **Factors:** language=go, model=opus, tooling=beads
- **Status:** ok (archive incomplete — internal/data/ missing)
- **Requirements:** 11/12 implemented, 1 partial, 0 missing
- **Tests:** 11 defined / 0 skipped (11 effective); test_coverage=0.33325 from retort.db
- **Build:** pass — defect_rate=1.0 from retort.db (archive cannot reproduce; missing internal/data package and go.sum)
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 4 items in `findings.jsonl` (0 critical, 2 high, 1 medium, 1 low)

## Requirements

Source: pinned `REQUIREMENTS.json` (12 requirements, constant denominator across all runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `internal/mcp/server.go` JSON-RPC 2.0 MCP server; `tools.go:14-263` registers 8 tools (find_matches, team_stats, head_to_head, standings, find_players, overall_stats, biggest_wins, dataset_info) |
| R2 | Loads data/kaggle/ datasets as data source | ~ partial | `main.go:16` calls `data.Load(*dataDir)` with `--data` flag; `internal/data/` package missing from archive — CSV parsing unverifiable. defect_rate=1.0 confirms it worked at scoring time. |
| R3 | Match query: find by team (home, away, either) | ✓ implemented | `query/match.go:44-47` MatchFilter.Team checks home OR away via `data.TeamMatches`; also supports dedicated HomeTeam/AwayTeam fields |
| R4 | Match query: filter by date range and/or season | ✓ implemented | `query/match.go:26-27` Season filter; `match.go:32-36` From/To date range; `tools.go:28-29` exposes as `from`/`to` ISO-8601 params |
| R5 | Match query: filter by competition | ✓ implemented | `query/match.go:29-30` case-insensitive substring match on Competition |
| R6 | Team query: W/L/D record and goals for/against | ✓ implemented | `query/team.go:35-75` ComputeTeamStats with wins/draws/losses, goals for/against, home/away splits, points |
| R7 | Player query: search by name | ✓ implemented | `query/player.go:22-24` case-insensitive substring name match |
| R8 | Player query: filter by nationality/club with ratings | ✓ implemented | `query/player.go:25-35` filters Nationality, Club, Position, MinOverall; sorted by Overall descending |
| R9 | Competition query: season standings from results | ✓ implemented | `query/team.go:78-118` Standings() computes from match results, sorted by points → GD → GF |
| R10 | Statistical analysis: aggregate stats | ✓ implemented | `query/stats.go:19-44` Overall() — avg goals/match, home win rate; `stats.go:47-67` BiggestWins() by goal difference |
| R11 | Head-to-head records between two teams | ✓ implemented | `query/match.go:76-105` H2H() returns W/L/D, goals, and recent match examples |
| R12 | Automated tests covering query capabilities | ✓ implemented | `server_test.go` (4 tests: MCP init, tools list, tool call, notifications) + `query_test.go` (7 tests: match search, team stats, H2H, standings, players, overall stats, biggest wins); 0 skipped; test_coverage=0.33325 from retort.db |

## Build & Test

Stored scores from retort.db (build/test NOT re-run per evaluation protocol):

```text
test_coverage    = 0.33325  (tests executed; ~33% code coverage)
code_quality     = 1.0      (lint clean)
defect_rate      = 1.0      (build + tests succeeded)
idiomatic        = 0.67
maintainability  = 0.546
token_efficiency = 0.044
```

Note: The `internal/data` package (data models, CSV loading, team name normalization) is missing from the archived workspace. All source files import it. `go.sum` is also absent. The code cannot be compiled from the archive alone, but `defect_rate=1.0` confirms the original run compiled and passed tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go source) | 1165 |
| Go source files | 10 |
| Total files in archive | 24 |
| Dependencies (go.mod) | 1 (golang.org/x/text) |
| Tests total | 11 |
| Tests effective | 11 |
| Tests skipped | 0 |
| Skip ratio | 0% |
| MCP tools registered | 8 |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [high] R2 — Data loading package missing from archive; cannot verify CSV loading from data/kaggle/
2. [high] archive-incomplete — Archived workspace missing internal/data package; code cannot compile from archive
3. [medium] metric-low-coverage — Test code coverage at 33.3%
4. [low] dep-go-version — go.mod specifies future Go version 1.25.4

## Reproduce

```bash
cd experiment-2/runs/language=go_model=opus_tooling=beads/rep1
# Archive is incomplete (internal/data missing, go.sum missing); build commands will not work as-is:
# go build ./...
# go test ./... -v -cover
# Stored scores from retort.db were used instead:
sqlite3 -readonly ../../retort.db \
  "SELECT rr.metric_name, rr.value FROM run_results rr
   WHERE rr.run_id = (SELECT er.id FROM experiment_runs er
     WHERE json_extract(er.run_config_json,'$.language')='go'
       AND json_extract(er.run_config_json,'$.model')='opus'
       AND json_extract(er.run_config_json,'$.tooling')='beads'
       AND er.replicate=1 AND er.status='completed'
     ORDER BY er.finished_at DESC LIMIT 1);"
```
