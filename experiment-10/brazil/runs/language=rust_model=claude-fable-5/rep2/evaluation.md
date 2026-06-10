# Evaluation: language=rust_model=claude-fable-5 · rep 2

## Summary

- **Factors:** language=rust, model=claude-fable-5, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 38 passed / 0 failed / 0 skipped (38 effective)
- **Build:** pass — test_coverage=1.0 from scores.json
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** summary skill unavailable
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/server.rs:226-281` handle_request implements JSON-RPC 2.0 with initialize, tools/list, tools/call; 9 tools registered at `src/server.rs:29-143` |
| R2 | Loads provided datasets from data/kaggle/ | ✓ implemented | `src/data.rs:158-168` Dataset::load() reads all 6 CSV files; `tests/bdd_mcp_protocol.rs:134-159` verifies row counts match expected sizes |
| R3 | Match query: find by team (home, away, either) | ✓ implemented | `src/queries.rs:101-140` filtered() with team/opponent params; `src/data.rs:80-83` Match::involves() checks both home and away; `tests/bdd_match_queries.rs:32-57` |
| R4 | Match query: filter by date range and/or season | ✓ implemented | `src/queries.rs:119-128` date_from/date_to filtering; `src/queries.rs:114-116` season filtering; `tests/bdd_match_queries.rs:106-130` |
| R5 | Match query: filter by competition | ✓ implemented | `src/queries.rs:82-89` competition_filter(); `src/normalize.rs:182-197` normalize_competition() maps free-form names to canonical labels; `tests/bdd_match_queries.rs:81-103` |
| R6 | Team query: match history with W/L/D and goals | ✓ implemented | `src/queries.rs:223-265` team_stats() returns overall/home/away Tally with W/D/L/GF/GA/win_rate plus per-competition breakdown; `tests/bdd_team_and_player_queries.rs:28-74` |
| R7 | Player query: search by name | ✓ implemented | `src/queries.rs:413-458` search_players() with name filter using deaccented substring match; `src/queries.rs:460-479` get_player() for single profile; `tests/bdd_team_and_player_queries.rs:159-175` |
| R8 | Player query: filter by nationality/club with ratings | ✓ implemented | `src/queries.rs:413-458` PlayerFilters with nationality, club, position, min_overall; results sorted by overall desc; `tests/bdd_team_and_player_queries.rs:97-157` |
| R9 | Competition query: season standings from match results | ✓ implemented | `src/queries.rs:314-388` standings() computes points table (3pts/win, 1pt/draw) with relegation zone flags; `tests/bdd_competitions_and_stats.rs:19-56` verifies 2019 champion (Flamengo 90pts) and 2003 historical season |
| R10 | Statistical analysis: aggregate stats | ✓ implemented | `src/queries.rs:482-524` analyze_stats() returns avg goals/match, home/draw/away win rates, biggest wins; `tests/bdd_competitions_and_stats.rs:90-129` |
| R11 | Head-to-head records between two teams | ✓ implemented | `src/queries.rs:267-312` head_to_head() returns W1/W2/D/goals per side plus recent matches; `tests/bdd_team_and_player_queries.rs:77-94` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 38 `#[test]` functions across 5 test files exercising all tools end-to-end against real CSV data, including BDD match/team/player/competition/stats/protocol scenarios; test_coverage=1.0 |

## Build & Test

```text
Build + test results from scores.json (not re-run):
  test_coverage:    1.0    (build + all tests passed)
  code_quality:     0.8333
  defect_rate:      0.9739 (build+test success)
  maintainability:  0.5591
  idiomatic:        0.87
  token_efficiency: 0.0102
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 2499 (11 .rs files) |
| Files (excl. data/) | 21 |
| Dependencies | 3 (csv, serde, serde_json) |
| Tests total | 38 |
| Tests effective | 38 |
| Skip ratio | 0% |
| Build duration | N/A (from scores.json) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Nine MCP tools exceed the 12-requirement spec — additional tools improve usability
2. [info] Comprehensive cross-dataset deduplication for Serie A 2012-2019
3. [info] Extensive team name normalization with alias table and accent handling
4. [info] BDD test suite with 38 tests covering all capabilities and 20 sample questions

## Reproduce

```bash
cd experiment-10/brazil/runs/language=rust_model=claude-fable-5/rep2
cat scores.json
cat REQUIREMENTS.json  # (in experiment-10/brazil/)
grep -rE '#\[ignore\]|#\[cfg\(ignore\)\]' . --include="*.rs" | wc -l
find . -name "*.rs" -not -path "*/target/*" -exec wc -l {} +
grep -rcE '#\[test\]' . --include="*.rs"
```
