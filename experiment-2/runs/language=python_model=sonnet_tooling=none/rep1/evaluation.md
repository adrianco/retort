# Evaluation: language=python · model=sonnet · tooling=none · rep 1

## Summary

- **Factors:** language=python, model=sonnet, tooling=none
- **Status:** ok — tests executed and largely pass (`test_coverage=0.96` from retort.db). See *Scoring source* note: the archive's `scores.json` is a degenerate all-zeros artifact and was NOT used.
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 78 functions, 0 skipped (78 effective); ~96% pass/coverage (`test_coverage=0.96`, `defect_rate=0.905` from retort.db)
- **Build:** pass — import/test gate cleared during scoring (`test_coverage>0`)
- **Lint / code quality:** `code_quality=0.667`, `maintainability=0.566`, `idiomatic=0.77` (retort.db)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 1 high, 2 medium, 2 info)

### Scoring source (important)

Per the skill, mechanical scores are read, not recomputed. Two sources disagreed:

| Metric | archive `scores.json` | retort.db `completed` row |
|--------|----------------------|---------------------------|
| test_coverage | 0.0 | **0.96** |
| code_quality | 0.0 | **0.667** |
| defect_rate | 0.0 | **0.905** |
| requirement_coverage | — | **0.917** |

`scores.json` is all-zeros, which is impossible for this code: `code_quality` is computed by
static analysis that needs neither the `mcp` package nor the datasets, yet it reads 0.0. The
zeros reflect a re-evaluation in a clean environment where `mcp` and `data/kaggle/` were absent
(confirmed locally: `ModuleNotFoundError: No module named 'mcp'`, no `data/` dir). The retort.db
`completed` row (finished 2026-04-13) is the genuine scoring run and is treated as authoritative.
The discrepancy is filed as a finding.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:20` `FastMCP(...)`, 11 `@mcp.tool()`, `mcp.run()` @708 |
| R2 | Loads datasets in data/kaggle/ | ✓ implemented | `data_loader.py:9` `DATA_DIR=.../data/kaggle`, 6 `pd.read_csv` loaders; tests loaded them (`test_coverage=0.96`) |
| R3 | Match query by team (home/away/either) | ✓ implemented | `server.py:50 search_matches(role=...)` → `data_loader.py:187 filter_by_team` |
| R4 | Filter by date range / season | ✓ implemented | `server.py:99` season + `season_from`/`season_to` filters |
| R5 | Filter by competition (Brasileirão/Copa/Liberta.) | ✓ implemented | `server.py:77` competition routing to per-comp loaders |
| R6 | Team match history W/L/D + goals for/against | ✓ implemented | `server.py:124 get_team_stats` — wins/draws/losses, GF/GA, home/away split |
| R7 | Player search by name | ✓ implemented | `server.py:308 search_players(name=)`, `:623 get_player_details` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `server.py:330-357` nationality/club/min_overall filters; emits Overall/Potential |
| R9 | Season standings computed from matches | ✓ implemented | `server.py:384 get_standings` builds table from results (pts/GD/GF) |
| R10 | Aggregate stats (avg goals, home vs away, biggest wins) | ✓ implemented | `server.py:526 get_competition_stats`, `:474 get_biggest_wins` |
| R11 | Head-to-head between two teams | ✓ implemented | `server.py:221 head_to_head` — W/L/D + recent matches |
| R12 | Automated tests covering queries; tests execute | ✓ implemented | `tests/test_server.py` 78 tests across 9 classes; `test_coverage=0.96>0` |

Enhancements beyond spec: `list_teams`, `get_player_details`, `get_team_seasons`, `get_biggest_wins` (not deductions).

## Build & Test

Not re-run — stored scores used per skill (re-running needs `mcp` + the un-archived Kaggle CSVs).

```text
# from retort.db (completed row, finished 2026-04-13 21:30):
test_coverage = 0.96     # import/test gate cleared; ~96% pass/coverage
defect_rate   = 0.905    # build+test largely succeeded
code_quality  = 0.667
requirement_coverage = 0.917
```

```text
# skipped-test scan (skill step 5):
grep -rEc "pytest.skip|@pytest.mark.skip|xfail" tests/  ->  0
# 78 test functions, 0 skipped -> 78 effective tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source .py) | 1533 (server 708, data_loader 205, tests 620) |
| Files (excl. __pycache__) | 12 |
| Dependencies (declared) | 0 — no manifest (uses `mcp`, `pandas`) |
| Tests total | 78 |
| Tests effective | 78 |
| Skip ratio | 0% |
| token_efficiency / cost | 0.028 · $0.72 · 879k tokens · 329s (retort.db) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] No dependency manifest (requirements.txt / pyproject.toml) — server imports `mcp`/`pandas` with nothing pinning them.
2. [medium] Tests do not all pass (`test_coverage=0.96`, `defect_rate=0.905`) — ~4% failing/uncovered; un-pinpointable without the datasets.
3. [medium] Archive `scores.json` is degenerate all-zeros, conflicting with canonical DB scores.
4. [info] `data/kaggle/` datasets not archived — blocks local re-run (expected).
5. [info] Four query tools beyond the 12 required capabilities.

## Reproduce

```bash
cd experiment-2/runs/language=python_model=sonnet_tooling=none/rep1
cat scores.json                                   # degenerate all-zeros — do NOT use
# authoritative scores:
sqlite3 -readonly ../../../retort.db "
  SELECT rr.metric_name, rr.value FROM run_results rr
  WHERE rr.run_id=(SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'\$.language')='python'
      AND json_extract(er.run_config_json,'\$.model')='sonnet'
      AND json_extract(er.run_config_json,'\$.tooling')='none'
      AND er.replicate=1 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"
grep -rEc "pytest.skip|@pytest.mark.skip|xfail" tests/   # -> 0
# local test re-run requires: pip install mcp pandas  AND  restore data/kaggle/*.csv
```
