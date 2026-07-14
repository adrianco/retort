# Evaluation: agent=hermes-local · language=python · prompt=none · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown, prompt=none
- **Status:** failed — the MCP server entrypoint (`server.py`) does not import (`@app.tool()` on a low-level `mcp.server.Server`), so the primary deliverable (R1) cannot run, even though the data layer and its tests pass.
- **Requirements:** 9/12 implemented, 2 partial (R1, R9), 1 missing (R7)
- **Tests:** 64 passed / 0 failed / 0 skipped (64 effective) — **but 29 query tests in `tests/test_queries.py` are silently uncollected**
- **Build:** pass (test_coverage=1.0-gate met; test_coverage=0.72 coverage, defect_rate=1.0 from scores.json) — note: `import server` itself fails
- **Lint:** n/a — code_quality=0.83 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (1 critical, 3 high, 2 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ~ partial | `server.py:23` Server + 13 `@app.tool()` handlers, but `server.py:133` `@app.tool()` → `AttributeError: 'Server' object has no attribute 'tool'`; module unimportable, server can't start |
| R2 | Load/use datasets in data/kaggle/ | ✓ implemented | `data_loader.py:90` load_all reads all 6 CSVs; verified 23,954 matches + 18,207 players load |
| R3 | Match query by team (home/away/either) | ✓ implemented | `data_loader.py:318` filters `home_team==team_norm or away_team==team_norm` |
| R4 | Match query: date range and/or season | ✓ implemented | `data_loader.py:322-333` date_from/date_to/season filters |
| R5 | Match query: filter by competition | ✓ implemented | `data_loader.py:328` competition substring filter; Brasileirao/Copa do Brasil/Libertadores all loaded |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `data_loader.py:337` get_team_statistics aggregates W/L/D + goals |
| R7 | Player query: search by name | ✗ missing | `data_loader.py:433` get_players_by_filter has no name param; `server.py:208` search_players exposes none — no name search path |
| R8 | Player query: nationality/club + ratings | ✓ implemented | `data_loader.py:444-450` nationality/club/position filters, returns overall/potential |
| R9 | Competition: standings from match results | ~ partial | `data_loader.py:495` computes from matches but `:522` credits only the away side + double-counts datasets → 2019 top team 41 pts (real champion had 90) |
| R10 | Statistical analysis: aggregate stats | ✓ implemented | `data_loader.py:476` avg goals/home-away rates; `:462` biggest-scoring matches |
| R11 | Head-to-head between two teams | ✓ implemented | `data_loader.py:379` get_head_to_head returns W/L/D between two teams |
| R12 | Automated tests covering queries | ✓ implemented | 64 tests pass, test_coverage=0.72>0; `test_data_loader.py` (49) exercises query fns — but see disabled_test finding (test_queries.py 29 tests uncollected) |

## Build & Test

```text
# stored scores (scores.json) — not re-run per skill
test_coverage=0.72  defect_rate=1.0  code_quality=0.83  maintainability=0.71  idiomatic=0.40

# pytest --collect-only -q
tests/test_data_loader.py: 49
tests/test_knowledge_graph.py: 15
# → 64 collected; tests/test_queries.py (29 methods) NOT collected (classes named Feature*)
```

```text
# python3 -c "import server"
File "server.py", line 133, in <module>
    @app.tool()
AttributeError: 'Server' object has no attribute 'tool'
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,387 |
| Lines of code (tests) | 829 |
| Files (excl. artifacts/data/summary) | 20 |
| Dependencies | 6 |
| Tests collected / passing | 64 / 64 |
| Tests uncollected (dead) | 29 (test_queries.py) |
| Tests effective | 64 |
| Skip ratio | 0% (but 29 uncollected) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] MCP server fails to import — `@app.tool()` on low-level Server (`server.py:133`) → the whole server is non-functional.
2. [high] No player search by name (R7) — `data_loader.py:433` has no name filter.
3. [high] Season standings computed incorrectly (R9) — only away side credited + dataset double-count (`data_loader.py:522`); 2019 top team shows 41 pts.
4. [high] 29 query tests uncollected — `tests/test_queries.py` classes named `Feature*`, no `python_classes` config; "64/64 passing" excludes them.
5. [medium] `get_connected_teams` references undefined `next_hop` (`knowledge_graph.py:119`) — find_team_connections tool broken.

## Reproduce

```bash
cd experiment-25-brazil-35b/brazil/runs/agent=hermes-local_language=python_prompt=none/rep3
python3 -c "import server"                              # AttributeError at server.py:133
python3 -m pytest --collect-only -q | tail             # 64 collected; test_queries.py absent
python3 -c "import sys;sys.path.insert(0,'.');from data_loader import MatchDataset as M;d=M();d.load_all();print(d.get_standings_by_season(2019)[0])"  # top team ~41 pts
```
