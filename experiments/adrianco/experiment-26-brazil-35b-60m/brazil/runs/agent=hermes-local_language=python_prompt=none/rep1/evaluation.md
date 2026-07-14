# Evaluation: agent=hermes-local · language=python · prompt=none · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (model `Qwen3.6-35B-A3B`, 90 API calls), framework=unknown, prompt=none
- **Status:** ok (build + tests pass) — but the MCP server entrypoint is broken and cannot start (see R1); one aggregation is incorrect (R6)
- **Requirements:** 10/12 implemented, 2 partial (R1, R6), 0 missing
- **Tests:** 47 passed / 0 failed / 0 skipped (47 effective) — from `defect_rate=1.0` in `scores.json`
- **Build:** pass — `test_coverage=1.0` gate not applicable; suite executed (`test_coverage=0.56` line coverage)
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 2 high, 3 medium, 1 low)

Scores read from `{run_dir}/scores.json` (run not yet in `retort.db` — inline eval gate):
`code_quality=0.833, test_coverage=0.56, defect_rate=1.0, maintainability=0.727, idiomatic=0.38, token_efficiency=0.0071`.
Per the skill, build/test/lint were **not** re-run — stored scores stand in.

## Requirements

Pinned checklist from `brazil/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | Implements an MCP server exposing tools/handlers | ~ partial | `server.py:22-253` declares 10 tools; `server.py:255` dispatches them. But `server.py:451` calls `server.run_stdio()` (no such SDK method) and `stdio_server` (imported line 8) is unused — **server can't start** |
| R2 | Loads/uses datasets in `data/kaggle/` | ✓ implemented | `data_loader.py:211-252` reads all 6 CSVs; `load_all_data` at `data_loader.py:332` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `repository.py:26` `search_matches(team, home_team, away_team, ...)` |
| R4 | Filter by date range and/or season | ✓ implemented | `repository.py:85-98` date_from/date_to/season masks |
| R5 | Filter by competition | ✓ implemented | `repository.py:91-93`; competition tagged per source in `data_loader.py:214/221/229` |
| R6 | Team W/L/D record + goals for/against | ~ partial | `repository.py:130` `get_team_stats` exists, but W/L/D are double-counted and away goals mis-attributed (`repository.py:182-197`) — values are wrong |
| R7 | Player search by name | ✓ implemented | `repository.py:304-306` name filter on FIFA data |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `repository.py:308-336` returns Name/Overall/Potential/Club |
| R9 | Season standings computed from matches | ✓ implemented | `repository.py:374-462` points = 3·W + D, sorted by pts/GD/GF |
| R10 | Aggregate stats (avg goals, biggest wins, home/away) | ✓ implemented | `repository.py:489` `get_average_goals`, `repository.py:464` `get_biggest_wins` |
| R11 | Head-to-head between two teams | ✓ implemented | `repository.py:218` `get_head_to_head` tallies W/L/D per team |
| R12 | Automated tests covering the query capabilities | ✓ implemented | `tests/test_repository.py` (27 unit) + `tests/*.feature` (20 BDD scenarios); coverage=0.56 > 0 |

Enhancement beyond spec: `get_competitions`, `get_all_teams`, `get_top_scorers` tools (the last reports *team* goal totals, not player scorers — see finding Q1).

## Build & Test

Not re-run — stored scores used per the evaluate-run skill.

```text
scores.json: defect_rate=1.0  => build + test suite succeeded
scores.json: test_coverage=0.56  => 56% line coverage (repository/data_loader; server.py untested)
tests: 27 unit (tests/test_repository.py) + 20 BDD scenarios (tests/*.feature)
skips: 0 (grep for pytest.skip/xfail found none)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only: server/repository/data_loader) | 1,370 |
| Lines of code (incl. tests) | 2,357 |
| Files (excl. data/kaggle, __pycache__) | 33 |
| Runtime dependencies | 2 (mcp, pandas) + 3 dev (pytest, pytest-bdd, pytest-flask) |
| Tests total | 47 |
| Tests effective | 47 |
| Skip ratio | 0% |
| Line coverage | 56% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R1 — MCP server cannot start: `server.run_stdio()` is not a real SDK method (`server.py:451`); `stdio_server` imported but unused.
2. [high] R6 — `get_team_stats` W/L/D double-counted from both perspectives and away goals mis-attributed (`repository.py:182-197`) — team stats are numerically wrong.
3. [medium] R6b — `away_matches` mask indexed against a subset with a full-df mask (`repository.py:175`), relying on implicit pandas index alignment.
4. [medium] Q2 — Server layer untested: `server.py` handlers/`main()` never invoked, so the broken entrypoint escapes the suite.
5. [medium] Q1 — `get_top_scorers` reports team goal totals, not player scorers, despite its name (`repository.py:338`).

## Reproduce

```bash
cd experiment-26-brazil-35b-60m/brazil/runs/agent=hermes-local_language=python_prompt=none/rep1
cat scores.json                     # stored mechanical scores (build/test/lint not re-run)
grep -n "run_stdio\|stdio_server" server.py   # confirm broken entrypoint
sed -n '177,214p' repository.py     # confirm W/L/D double-count in calc_match_stats
grep -rn "pytest.skip\|xfail" tests/          # confirm 0 skips
```
