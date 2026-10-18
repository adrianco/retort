# Evaluation: effort=low language=c model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 130 passed / 0 failed / 0 skipped (130 effective) — 119 unit assertions + 11 protocol checks
- **Build:** pass (not re-run; `test_coverage=1.0`, `defect_rate=1.0` from scores.json)
- **Lint:** pass (`code_quality=1.0` from scores.json; `-Wall -Wextra -Wpedantic` clean build)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `brazil/REQUIREMENTS.json` (R1–R12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/mcp.c:130` `mcp_serve`; JSON-RPC initialize/tools/list/tools/call; 7 tools in `src/query.c:38` |
| R2 | Loads/uses data/kaggle datasets | ✓ implemented | `src/db.c:56` SOURCES → `csv_load`; `data/kaggle/` holds all 6 CSVs; no external APIs |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/query.c:271` `tool_find_matches` + `involves`/`venue` at `query.c:181,204` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/query.c:145` `read_filter` date_from/date_to/season → `match_ok` `query.c:194-199` |
| R5 | Filter by competition | ✓ implemented | `match_ok` `query.c:188` substring; spans Brasileirão/Copa do Brasil/Libertadores via `db.c:56` |
| R6 | Team record W/L/D + goals | ✓ implemented | `src/query.c:309` `tool_team_record` (wins/draws/losses, GF/GA, win rate) |
| R7 | Player search by name | ✓ implemented | `src/query.c:592` `tool_search_players`, `name` filter via `player_ok` `query.c:581` |
| R8 | Players by nationality/club with ratings | ✓ implemented | `player_ok` `query.c:583-586` + overall/position/age in output `query.c:617` |
| R9 | Season standings from matches | ✓ implemented | `src/query.c:440` `tool_standings` computes 3/1/0 points, GD tiebreaks `query.c:419` |
| R10 | Aggregate statistics | ✓ implemented | `src/query.c:517` `tool_match_stats` avg goals, home/draw/away rates, biggest wins |
| R11 | Head-to-head between two teams | ✓ implemented | `src/query.c:359` `tool_head_to_head` (W/W/D + recent meetings) |
| R12 | Automated tests of query capabilities | ✓ implemented | `tests/test_unit.c` 119 assertions; `tests/test_mcp.sh` 11 protocol checks; `test_coverage=1.0` |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and adds no checkable requirement beyond "include tests", which R12 covers.

## Build & Test

Scores read from `scores.json` (computed by retort's scorers during the run — not re-run here):

```text
test_coverage = 1.0   → build + all tests passed
defect_rate   = 1.0   → build + test succeeded
code_quality  = 1.0   → lint/quality clean
maintainability = 0.464
idiomatic     = 0.3
token_efficiency = 0.0088
```

Build is dependency-free (`make`: `cc -std=c11 -Wall -Wextra -Wpedantic -O2`). Test target runs the unit binary then the stdio protocol script; `test_mcp.sh` additionally exercises the real `data/kaggle` datasets (asserts 2019 Brasileirão champion Flamengo on 90 pts).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | ~2,659 |
| Source files (c/h/sh) | 15 |
| Dependencies | 0 (pure libc) |
| Tests total | 130 (119 unit + 11 protocol) |
| Tests effective | 130 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

No requirement gaps, build/test failures, or skipped tests. Two info-level enhancement notes (full list in `findings.jsonl`):

1. [info] Exceeds spec — 7 tools (adds club_summary, venue filtering), accent/state-suffix team-name unification, cross-source (competition, season) dedup.
2. [info] Integration test validates against the real datasets, not only fixtures.

## Reproduce

```bash
cd experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=c_model=claude-haiku-5-5_prompt=neutral/rep1
cat scores.json                                   # stored build/test/lint scores
grep -rniE "\bskip\b|#if 0|TODO|FIXME" src tests  # skip detection → 0
make test                                         # rebuild + run tests (optional; already scored)
```
