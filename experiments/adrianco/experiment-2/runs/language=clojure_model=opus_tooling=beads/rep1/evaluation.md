# Evaluation: language=clojure_model=opus_tooling=beads · rep 1

## Summary

- **Factors:** language=clojure, model=opus, tooling=beads
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=0.833 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (0 critical, 2 high)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server with tools/handlers | ✓ implemented | `src/soccer/mcp.clj:1-189` — JSON-RPC over stdio server with initialize, tools/list, tools/call; 9 tools registered |
| R2 | Loads provided CSV datasets from data/kaggle/ | ✓ implemented | `src/soccer/data.clj:61-169` — loads all 6 CSVs (Brasileirao, Copa do Brasil, Libertadores, BR-Football, novo, FIFA); test confirms >20k matches, >18k players |
| R3 | Match query: filter by team (home/away/either) | ✓ implemented | `src/soccer/query.clj:28-38` `matches-by-team` with side param `:home`/`:away`/`:either`; exposed via `team_matches` and `list_matches_between` MCP tools |
| R4 | Match query: filter by date range and/or season | ~ partial | `query.clj:55-60` `matches-by-date-range` exists but not exposed in any MCP tool schema. Season filter param exists on MCP tools but `mcp.clj:83` has cond->> arg-order bug — threads matches as last arg to `(matches-by-season season ...)` instead of first |
| R5 | Match query: filter by competition | ✓ implemented | `src/soccer/query.clj:52-53` `matches-by-competition`; exposed in `team_matches`, `standings`, `biggest_wins`, `statistics` tools |
| R6 | Team query: W/L/D record with goals for/against | ✓ implemented | `src/soccer/query.clj:66-93` `team-record` returns W/D/L/GF/GA with optional side restriction; exposed via `team_record` MCP tool |
| R7 | Player query: search by name | ✓ implemented | `src/soccer/query.clj:197-199` `players-by-name` case-insensitive substring match; exposed via `search_players` tool |
| R8 | Player query: filter by nationality/club with ratings | ✓ implemented | `src/soccer/query.clj:201-211` `players-by-nationality`/`players-by-club`/`players-by-position`; `search_players` and `top_players` tools return overall/potential ratings |
| R9 | Competition standings from match results | ✓ implemented | `src/soccer/query.clj:122-154` computes standings (3/1/0 points, sorted by pts/GD/GF); exposed via `standings` MCP tool |
| R10 | Statistical analysis: aggregate stats | ✓ implemented | `src/soccer/query.clj:163-194` avg goals/match, home win rate, biggest wins, top scoring teams; exposed via `statistics` and `biggest_wins` MCP tools |
| R11 | Head-to-head records between two teams | ✓ implemented | `src/soccer/query.clj:95-118` `head-to-head` returns per-side W/D/L and goals; exposed via `head_to_head` MCP tool; tested in both query_test and mcp_test |
| R12 | Automated tests covering query capabilities | ✓ implemented | `test/soccer/{data,query,mcp}_test.clj` — 15 deftest functions covering data loading, all query types, and MCP dispatch; test_coverage=1.0 |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage    = 1.0   (build + all tests passed)
  code_quality     = 0.833
  defect_rate      = 1.0   (build+test succeeded)
  idiomatic        = 0.780
  maintainability  = 0.788
  token_efficiency = 0.009
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 583 (3 files) |
| Lines of test code | 143 (3 files) |
| Total Clojure lines | 726 |
| Files | 20 |
| Dependencies | 3 (clojure 1.11.3, data.csv 1.1.0, data.json 2.5.0) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] Date range filtering not exposed via MCP; season filtering broken in MCP layer — `matches-by-date-range` exists in `query.clj:55` but no MCP tool exposes it; `filter-matches` in `mcp.clj:83` swaps args for `matches-by-season` in `cond->>`
2. [high] `filter-matches` `cond->>` passes season with wrong argument order — `mcp.clj:83` threads matches as last arg to `(matches-by-season season ...)` but function expects `[matches season]`; affects all season-filtered MCP calls. Tests pass because `query_test.clj` calls `matches-by-season` directly, never through MCP dispatch.

## Reproduce

```bash
cd experiment-2/runs/language=clojure_model=opus_tooling=beads/rep1
cat stack.json
# Scores retrieved from retort.db — build/test not re-run
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='clojure' AND json_extract(er.run_config_json,'\$.model')='opus' AND json_extract(er.run_config_json,'\$.tooling')='beads' AND er.replicate=1 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
```
