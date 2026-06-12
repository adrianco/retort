# Evaluation: language=python_model=claude-opus-4-8-fast · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-4-8-fast (agent/framework unknown; no prompt/tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 71 test functions (+ 10 BDD scenarios) / 0 failed / 0 skipped (71 effective) — build+tests passed at 89% coverage
- **Build:** pass — test_coverage=0.89 from scores.json (1.0 import/build gate cleared; coverage 89%)
- **Lint:** pass — code_quality=0.6667 from scores.json
- **Architecture:** thin FastMCP adapter (`server.py`) over a single in-memory `KnowledgeGraph`; data via stdlib-only `data_loader.py`; `normalize.py`/`models.py`/`formatting.py` support. (run-summary not invoked; described inline.)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:32` `FastMCP("brazilian-soccer")`, 14 `@mcp.tool()` defs; `test_all_tools_registered` |
| R2 | Loads datasets in data/kaggle/ | ✓ implemented | `data_loader.py:50` `find_data_dir`→`data/kaggle`; 6 CSVs present; `test_all_six_csv_files_exist`, `test_matches_and_players_loaded` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `knowledge_graph.py:205` `find_matches(..., venue=)`; `test_find_matches_tool`, `test_home_venue_filter` |
| R4 | Filter by date range and/or season | ✓ implemented | `knowledge_graph.py:230-251` start/end/season filters; `test_date_range_filter`, `test_team_and_season_filter` |
| R5 | Filter by competition (Brasileirão/Copa/Liberta.) | ✓ implemented | `knowledge_graph.py:612` `_resolve_competition` alias table; `test_competition_filter`, `test_palmeiras_plays_in_all_three_majors` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `knowledge_graph.py:295` `team_record`; `test_team_record_tool`, `test_record_fields_are_internally_consistent` |
| R7 | Player search by name | ✓ implemented | `knowledge_graph.py:360` `search_players(name=)`; `test_search_by_name_substring` |
| R8 | Players by nationality/club + ratings | ✓ implemented | `knowledge_graph.py:371-400` nat/club/overall filters; `test_search_by_club`, `test_find_brazilian_players_sorted_by_overall` |
| R9 | Standings computed from match results | ✓ implemented | `knowledge_graph.py:425` `standings` (3pt win/1pt draw, computed); `test_standings_sorted_by_points`, `test_2019_brasileirao_champion_is_flamengo` |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `knowledge_graph.py:505` `average_goals`, `:538` `biggest_wins`; `test_brasileirao_average_is_realistic`, `test_home_advantage_exists` |
| R11 | Head-to-head between two teams | ✓ implemented | `knowledge_graph.py:257` `head_to_head`; `test_head_to_head_tool`, `test_head_to_head_symmetry` |
| R12 | Automated tests covering capabilities | ✓ implemented | 71 test fns across 9 test files + BDD feature; test_coverage=0.89 |

No prompt factor in `stack.json`, so there are no `P*` requirements.

## Build & Test

Build/test not re-run — stored scores read from `scores.json` (skill step 2):

```text
test_coverage   = 0.89   # build+import gate cleared (1.0 ⇒ tests executed); 89% line coverage
defect_rate     = 0.9946 # build+test succeeded
code_quality    = 0.6667 # lint/quality
maintainability = 0.2882
idiomatic       = 0.77
token_efficiency= 1.0
```

Skip scan (skill step 5): `grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail"` → 0 matches. No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1706 (brazilian_soccer_mcp) |
| Lines of code (tests) | 646 |
| Files (.py, excl. pycache) | 16 |
| Dependencies | 2 (mcp, pytest) |
| Tests total | 71 (+10 BDD scenarios) |
| Tests effective | 71 |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] knowledge_graph.py is a 658-line god module driving a low maintainability score (0.2882)
2. [low] Lint/quality score below 1.0 (code_quality=0.6667)
3. [low] Line coverage at 89%, not full
4. [info] Server exposes 14 MCP tools, beyond the required queries
5. [info] Overlapping CSV sources de-duplicated via per-competition source priority

## Reproduce

```bash
cd experiment-7/brazil/runs/language=python_model=claude-opus-4-8-fast/rep2
cat scores.json                                   # cached mechanical scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests --include="*.py"   # skip scan
grep -rhE "def test_" tests --include="*.py" | wc -l                       # test count
```
