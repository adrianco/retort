# Evaluation: agent=hermes-local language=python prompt=none · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), framework=unknown, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 88 passed / 0 failed / 0 skipped (88 effective) — `test_coverage=0.9`, `defect_rate=1.0` from `scores.json`
- **Build:** pass — from stored scores (not re-run)
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:22` FastMCP + 22 `@mcp.tool()` handlers; `main()` runs `mcp.run()` |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `data_loader.py:116-224` reads all 6 CSVs; `data/kaggle/` has all 6 files |
| R3 | Match query by team | ✓ implemented | `query_engine.py:36 find_matches_by_team` → `_filter_matches` (home OR away) |
| R4 | Filter by date range / season | ✓ implemented | `query_engine.py:751 _filter_matches` season/date_from/date_to; tested `test_find_matches_by_team_with_season` |
| R5 | Filter by competition | ✓ implemented | competition param + Brasileirão/Copa/Libertadores loaders; `test_matches_by_competition` |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `query_engine.py:168 get_team_statistics`; `test_get_team_statistics` |
| R7 | Search players by name | ✓ implemented | `query_engine.py:359 search_player`; `test_search_player_by_name` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `query_engine.py:377,396 get_players_by_nationality/_by_club` |
| R9 | Standings from match results | ✓ implemented | `query_engine.py:490 get_standings` computes 3-1-0 points (see F2 caveat) |
| R10 | Aggregate statistics | ✓ implemented | `get_average_goals_per_match:571`, `get_biggest_wins:608`, `get_best_away_record:682` |
| R11 | Head-to-head between two teams | ✓ implemented | `query_engine.py:59 find_matches_between_teams` returns W/L/D; `test_h2h_head_to_head_record` |
| R12 | Automated tests | ✓ implemented | `tests/test_brazilian_soccer_mcp.py` — 88 tests, `test_coverage=0.9` |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill policy):

```text
test_coverage   = 0.9   (build + tests executed; pass-rate/coverage signal)
defect_rate     = 1.0   (build + tests succeeded)
code_quality    = 0.833
maintainability = 0.622
idiomatic       = 0.77
```

Agent's own report (`_agent_stdout.log`): "All 88 tests pass" across 10 test classes; 0 skips confirmed by grep. No `-failed` suffix on the run dir; `_meta.json.succeeded=true`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | ~1,550 (data_loader 284 + query_engine 765 + server 498 + init 3) |
| Test lines | 955 |
| Files (excl. `__pycache__`/`.coverage`) | ~22 (4 py modules, 1 test, 6 CSVs, README, pyproject, guide, etc.) |
| Dependencies | 3 runtime (mcp, pandas, pydantic) + 2 dev (pytest, pytest-asyncio) |
| Tests total | 88 |
| Tests effective | 88 |
| Skip ratio | 0% |
| MCP tools exposed | 22 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] F1 — `find_copa_do_brasil_final` filters `contains("copa")`, also matching Copa Libertadores (`query_engine.py:140`)
2. [medium] F2 — Standings double-count overlapping Brasileirão datasets sharing one competition label (`data_loader.py:123,207`; `query_engine.py:490`)
3. [low] F3 — Brazilian-club detection uses brittle substring regex; can misclassify non-Brazilian clubs (`query_engine.py:420`)
4. [low] F4 — `BRAZILIAN_CLUBS` constant is defined but never used (`data_loader.py:28`)
5. [info] F5 — Row-wise `iterrows` aggregation instead of vectorized pandas (still within perf gates)

No critical or high findings: the run builds, all 88 tests pass with no skips, and every pinned requirement is implemented.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-25-brazil-35b/brazil/runs/agent=hermes-local_language=python_prompt=none/rep2
cat scores.json                                   # stored mechanical scores (build/test/lint)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # 0 skips
# to re-run tests locally (optional, not required by eval):
python -m pytest tests/ -q
```
