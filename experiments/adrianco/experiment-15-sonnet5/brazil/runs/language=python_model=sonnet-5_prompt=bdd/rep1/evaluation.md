# Evaluation: language=python_model=sonnet-5_prompt=bdd · rep 1

## Summary

- **Factors:** language=python, model=sonnet-5, prompt=bdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 85 passed / 0 failed / 0 skipped (85 effective) — from defect_rate=1.0
- **Build:** pass — import/collection succeeds (test_coverage=0.92 from scores.json)
- **Lint:** pass — code_quality=0.83 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Pinned checklist from `experiment-15-sonnet5/brazil/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py` FastMCP("brazilian-soccer"), 14 `@mcp.tool()` handlers, `main()`→`mcp.run()` |
| R2 | Load/use provided datasets in data/kaggle/ | ✓ implemented | `data_loader.py:65` reads `data/kaggle`; 6 `read_csv` loaders → `load_all()`; all 6 CSVs present |
| R3 | Match query by team (home/away/either) | ✓ implemented | `queries.py:search_matches` filters `home_team_key`/`away_team_key`; `test_queries.py` TestSearchMatches |
| R4 | Match query by date range / season | ✓ implemented | `search_matches` season + date_from/date_to via `parse_datetime`; tested |
| R5 | Match query by competition | ✓ implemented | `search_matches` competition filter + `resolve_competition`; spans Brasileirão/Cup/Libertadores |
| R6 | Team record W/L/D + goals for/against | ✓ implemented | `queries.py:team_record` returns wins/draws/losses/goals_for/against/win_rate; `test_queries.py` |
| R7 | Player search by name | ✓ implemented | `queries.py:search_players` name filter (accent-folded contains); `search_players` tool |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `search_players` nationality/club/position/min_overall; `brazilian_players_by_club` |
| R9 | Season standings computed from matches | ✓ implemented | `queries.py:standings` builds points/GD table from results; `_primary_source` avoids double-count |
| R10 | Aggregate statistics | ✓ implemented | `get_statistics` (avg goals/match, home win rate), `get_biggest_wins`, `get_best_away_record`, `top_scoring_teams` |
| R11 | Head-to-head between two teams | ✓ implemented | `queries.py:head_to_head` returns wins_a/wins_b/draws; `get_head_to_head` tool |
| R12 | Automated tests covering queries | ✓ implemented | 6 test modules, 85 tests, test_coverage=0.92, all pass (defect_rate=1.0) |

### Prompt-factor instructions (prompt=bdd)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Given/When/Then structure | ✓ implemented | G/W/T comments in every test module (e.g. `test_queries.py:13-19`) |
| P2 | Names describe observable behaviour | ✓ implemented | e.g. `test_given_a_team_name_when_searching_matches_then_every_result_features_that_team` |
| P3 | One assertion per scenario where practical | ✓ implemented | scenarios assert a single observable outcome (`test_queries.py` TestSearchMatches) |
| P4 | Descriptive `given_..._when_..._then_...` names | ✓ implemented | consistent naming across `test_queries.py`, `test_normalize.py`, `test_server.py`, `test_graph.py` |

## Build & Test

Scores read from `scores.json` (mechanical scorers already ran; not re-run per skill guidance):

```text
test_coverage = 0.92   # build + all 85 tests pass; 92% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.8333
maintainability = 0.7790
idiomatic     = 0.88
```

Skip scan (`grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/`): **0** — no skipped/xfail tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,533 (brazilian_soccer_mcp/*.py) |
| Lines of code (tests) | 893 |
| Files (source + tests) | 14 |
| Dependencies | 2 runtime (mcp, pandas) + pytest |
| Tests total | 85 |
| Tests effective | 85 |
| Skip ratio | 0% |
| Line coverage | 92% |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no correctness or conformance defects:

1. [info] Line coverage 92% (8% of source lines unexercised)
2. [info] Enhancement: 14 tools exceed the required capability set (Serie B/C, biggest wins, best away record)
3. [info] Enhancement: cross-source dedup + authoritative-source selection prevents double-counting standings

## Reproduce

```bash
cd experiment-15-sonnet5/brazil/runs/language=python_model=sonnet-5_prompt=bdd/rep1
cat scores.json                       # stored mechanical scores (no re-run)
grep -rE "pytest\.skip|xfail" tests/  # skip scan → 0
# optional live re-run:
pip install -e . && pytest -q
```
