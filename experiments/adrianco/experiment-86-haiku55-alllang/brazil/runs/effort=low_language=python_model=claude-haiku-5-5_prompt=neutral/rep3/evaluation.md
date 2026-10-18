# Evaluation: effort=low language=python model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 54 functions passed / 0 failed / 0 skipped (54 effective)
- **Build:** pass — from `scores.json` (test_coverage=0.94, defect_rate=1.0; not re-run)
- **Lint:** code_quality=0.6667 (stored); no separate lint re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Checklist is the pinned `brazil/REQUIREMENTS.json` (R1–R12), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `mcp_server.py:MCPServer` — initialize/ping/tools.list/tools.call; `tools.py:TOOLS` (8 tools) |
| R2 | Loads/uses data/kaggle/ datasets | ✓ implemented | `loaders.py:load_all` reads all 6 CSVs; `test_loaders.py` + `conftest.py:data` fixture load real data |
| R3 | Match query by team (home/away/either) | ✓ implemented | `store.py:find_matches` with `venue` any/home/away; `test_queries.py:test_given_venue_home_then_only_home_games_return` |
| R4 | Filter by date range / season | ✓ implemented | `store.py:find_matches` `start`/`end`/`season`; `test_given_date_range_then_matches_fall_inside_it` |
| R5 | Filter by competition | ✓ implemented | `store.py:resolve_competition` (Brasileirão/Copa do Brasil/Libertadores); `test_given_copa_do_brasil_when_searched...` |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `store.py:team_record`/`_tally` → `Record`; `tools.py:_team_stats`; `test_given_two_teams_when...` |
| R7 | Player search by name | ✓ implemented | `store.py:find_players` name filter; `test_given_name_search_then_accents_are_ignored` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `store.py:find_players` nationality/club/min_overall, returns overall; `test_given_nationality_filter...` |
| R9 | Standings computed from matches | ✓ implemented | `store.py:standings` (3·W+D, GD tiebreak); `test_given_standings_2019_then_flamengo_top_with_90_points` |
| R10 | Aggregate statistics | ✓ implemented | `store.py:goals_per_match`/`home_win_rate`/`biggest_wins`/`best_away_records`; `test_given_brasileirao_then_average_goals...` |
| R11 | Head-to-head between two teams | ✓ implemented | `store.py:head_to_head` → `HeadToHead`; `test_given_two_teams_then_wins_draws_and_goals_add_up` |
| R12 | Automated tests for query capabilities | ✓ implemented | 54 tests across 4 files, test_coverage=0.94, 0 skips |

## Build & Test

Scores read from `scores.json` (inline gate during `retort run`) — build/tests **not** re-run per the skill:

```text
test_coverage   = 0.94   (build + tests ran and passed; 94% line coverage)
defect_rate     = 1.0    (build + test succeeded)
code_quality    = 0.6667
maintainability = 0.6555
idiomatic       = 0.60
token_efficiency= 0.0158
```

Skip scan (grep): 0 `pytest.skip`/`@pytest.mark.skip`/`xfail` across `tests/`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1309 |
| Lines of code (tests) | 445 |
| Files (excl. data/, __pycache__) | 26 |
| Runtime dependencies | 0 (stdlib only; pytest dev-only) |
| Tests total | 54 |
| Tests effective | 54 |
| Skip ratio | 0% |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Cross-source match de-dup keys on (competition, teams) + score within 1 day — a true duplicate recorded >1 day apart can survive (`store.py:104`).
2. [info] Statistical analysis exceeds the single-aggregate minimum (`store.py:295–339`).
3. [info] Test coverage is 94%, not 100% — a few error branches unexercised.

No critical/high/medium findings: all 12 requirements implemented, tests pass with no skips.

## Reproduce

```bash
cd experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=python_model=claude-haiku-5-5_prompt=neutral/rep3
cat scores.json                                    # stored build/test/quality scores (not re-run)
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py"
# optional full re-run:  python -m pytest -q
```
