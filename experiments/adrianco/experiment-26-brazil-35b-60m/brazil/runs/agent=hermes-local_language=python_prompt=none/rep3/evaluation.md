# Evaluation: agent=hermes-local language=python prompt=none · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local (Qwen3.6-35B-A3B, local), framework=unknown, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (two implemented tools carry correctness caveats — see Findings)
- **Tests:** 121 passed / 0 failed / 0 skipped (121 effective) — per `_agent_stdout.log` "All 121 tests pass" and `scores.json` defect_rate=1.0
- **Build:** pass — from `scores.json` defect_rate=1.0 (build+test succeeded; not re-run)
- **Lint:** pass — code_quality=0.8333 from `scores.json`
- **Coverage:** test_coverage=0.96 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low)

## Requirements

Pinned checklist from `../../../REQUIREMENTS.json` (12 fixed requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:7` FastMCP + 11 `@mcp.tool()` handlers; `mcp.run()` entrypoint |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `data_loader.py:10,58` reads all 6 CSVs from `data/kaggle/`; files present on disk |
| R3 | Match query by team (home/away/either) | ✓ implemented | `query_handlers.py:38-44` team mask on home\|away (caveat: limit-before-sort, unanchored substring) |
| R4 | Match query by date range / season | ✓ implemented | `query_handlers.py:65-72` season, date_from, date_to filters |
| R5 | Match query by competition | ✓ implemented | `query_handlers.py:60-63` competition mask; `all_matches()` tags each CSV with a competition |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `query_handlers.py:98-168` `get_team_statistics` |
| R7 | Player search by name | ✓ implemented | `query_handlers.py:263-265` FIFA name filter |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `query_handlers.py:267-298` nationality/club/position/min_rating; returns overall/potential |
| R9 | Season standings computed from matches | ✓ implemented | `query_handlers.py:303-364` `get_standings` (3pts/win, GD tiebreak) |
| R10 | Aggregate statistics | ✓ implemented | `query_handlers.py:367-416` `get_biggest_wins`, `get_average_goals` (home/away/draw rates) |
| R11 | Head-to-head between two teams | ✓ implemented | `query_handlers.py:171-248` `get_head_to_head` |
| R12 | Automated tests over query capabilities | ✓ implemented | `tests/test_brazilian_soccer.py` — 121 tests / 23 classes, test_coverage=0.96 |

## Build & Test

Scores read from `scores.json` (inline-gate eval; this run has no `retort.db` row). Build/test/lint **not re-run** per skill.

```text
scores.json
  test_coverage   = 0.96   (tests ran; ~96% coverage)
  defect_rate     = 1.0    (build + tests succeeded)
  code_quality    = 0.8333 (lint/quality)
  maintainability = 0.6838
  idiomatic       = 0.73
  token_efficiency= 0.0207 (local 35B, 35 API calls, 1.52M total tokens)
```

```text
_agent_stdout.log
  "All 121 tests pass."
  skip scan (tests/*.py): 0 pytest.skip / mark.skip / xfail
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test) | 1064 |
| Lines of code (tests) | 888 |
| Files (source + tests) | 6 .py + pyproject.toml |
| Dependencies | 4 (mcp, pandas; dev: pytest, pytest-asyncio) |
| Tests total | 121 |
| Tests effective | 121 |
| Skip ratio | 0% |
| MCP tools exposed | 11 |

## Findings

Full list in `findings.jsonl` (top by severity):

1. [medium] R3 — `find_matches` calls `.head(limit)` BEFORE `sort_values('date')`, so large result sets return an arbitrary (non-recent) subset then sort within it (`query_handlers.py:74-75`).
2. [low] Team filtering uses unanchored `str.contains`, over-matching substrings like `America` → `Americano` across find/stats/h2h (`query_handlers.py:41,110,185`).

No critical/high findings — this is a strong run: all 12 requirements implemented, 121 tests pass, 0 skips.

## Reproduce

```bash
cd experiment-26-brazil-35b-60m/brazil/runs/agent=hermes-local_language=python_prompt=none/rep3
cat scores.json                                   # stored build/test/lint scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0 skips
grep -oE "[A-Za-z_-]+\.csv" brazilian_soccer_mcp/data_loader.py | sort -u           # 6 CSVs
wc -l brazilian_soccer_mcp/*.py tests/*.py        # LOC
# Requirements checklist: ../../../REQUIREMENTS.json
# Architecture: summary/index.md
```
