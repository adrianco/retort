# Evaluation: language=python model=claude-opus-4-8-fast · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-4-8-fast, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 44 test functions, 0 skipped (44 effective) — `test_coverage=0.94` ⇒ build + suite pass
- **Build:** pass (import/collection succeeded — `test_coverage=0.94` from scores.json)
- **Lint:** pass — `code_quality=0.6667` from scores.json (moderate)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:36` FastMCP + 13 `@mcp.tool`; `tests/test_server_tools.py:test_all_expected_tools_are_registered` |
| R2 | Load/use datasets in data/kaggle/ | ✓ implemented | `data_loader.py:186` loaders for all 6 CSVs; `tests/test_data_loading.py:test_all_match_files_contribute_rows` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `knowledge_graph.py:86 find_matches` + `_team_mask` side='either'; `test_match_queries.py:test_find_matches_between_two_teams` |
| R4 | Filter by date range and/or season | ✓ implemented | `knowledge_graph.py:116-123` season + start/end_date; `test_find_matches_by_date_range`, `test_find_matches_by_team_and_season` |
| R5 | Filter by competition | ✓ implemented | `knowledge_graph.py:111` competition mask; `test_find_matches_by_competition` (Brasileirão/Copa do Brasil/Libertadores) |
| R6 | Team match history W/L/D + goals | ✓ implemented | `knowledge_graph.py:145 team_record`; `test_team_queries.py:test_team_record_has_consistent_totals` |
| R7 | Player search by name | ✓ implemented | `knowledge_graph.py:251 search_players` name; `test_player_queries.py:test_search_player_by_name` |
| R8 | Players by nationality/club + ratings | ✓ implemented | `search_players` nationality/club/Overall; `test_find_all_brazilian_players`, `test_filter_players_by_club` |
| R9 | Standings computed from matches | ✓ implemented | `knowledge_graph.py:320 standings` (3/1/0 pts); `test_competition_queries.py:test_2019_brasileirao_champion_is_flamengo` |
| R10 | Aggregate stats | ✓ implemented | `average_goals` :380, `biggest_wins` :409, `best_record` :439; `test_statistics.py:test_average_goals_is_plausible` |
| R11 | Head-to-head between two teams | ✓ implemented | `knowledge_graph.py:210 head_to_head`; `test_team_queries.py:test_head_to_head_is_symmetric` |
| R12 | Automated tests covering queries | ✓ implemented | 44 tests across 7 files; `test_coverage=0.94` (suite executes) |

No `prompt` factor in `stack.json` (language/model only) — no `P*` instructions to verify.

## Build & Test

Build/test not re-run — stored mechanical scores used per skill policy.

```text
scores.json
test_coverage   = 0.94   # build + full pytest suite passed (94% coverage)
code_quality    = 0.6667 # ruff/quality scorer
defect_rate     = 0.9985 # build+test succeeded
maintainability = 0.6025
idiomatic       = 0.78
token_efficiency= 1.0
```

```text
Skipped-test scan: grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ → 0 matches
Test functions: grep -rE "def test_" tests/ → 44
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (package source) | 1,399 |
| Files (excl. venv/caches/egg-info) | 34 |
| Dependencies | 3 (pandas, mcp, pytest) |
| Tests total | 44 |
| Tests effective | 44 |
| Skip ratio | 0% |
| Build | pass (test_coverage=0.94) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Moderate code_quality (0.6667) / maintainability (0.6025) per scores.json — no functional impact
2. [info] Discovery/competition tools beyond spec (champion, relegated, list_competitions, list_seasons)
3. [info] Multi-source dedup avoids inflated standings (`data_loader.py:198`)
4. [info] BDD test approach mirrors the Gherkin feature spec

## Reproduce

```bash
cd experiment-7/brazil/runs/language=python_model=claude-opus-4-8-fast/rep1
cat scores.json
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l
grep -rE "def test_" tests/ --include="*.py" | wc -l
ls data/kaggle   # 6 provided CSVs
```
