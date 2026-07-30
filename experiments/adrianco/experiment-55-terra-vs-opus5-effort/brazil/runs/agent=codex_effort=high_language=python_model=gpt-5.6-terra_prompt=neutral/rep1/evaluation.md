# Evaluation: agent=codex effort=high language=python model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, effort=high, prompt=neutral
- **Status:** ok (build+tests pass) — one high-severity correctness defect in aggregates
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — `test_coverage=0.86`, `defect_rate=1.0`
- **Build:** pass — `test_coverage=0.86` from `scores.json` (build + tests ran)
- **Lint:** pass — `code_quality=0.7889` from `scores.json`
- **Architecture:** single-module stdlib-only MCP server; `run-summary` skill not available, so no `summary/` was generated
- **Findings:** 3 items in `findings.jsonl` (1 high, 1 low, 1 info)

## Requirements

Pinned list from `brazil/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `brazilian_soccer_mcp.py:344` TOOL_DEFINITIONS; `:361` handle_request (initialize/tools/list/tools/call); `:384` serve stdio JSON-RPC |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `:146` `_load` reads all 6 CSVs; `:139` utf-8-sig DictReader |
| R3 | Match query by team (home/away/either) | ✓ implemented | `:196` `search_matches(location=...)`, `:189` `_team_matches_team` |
| R4 | Filter by date range and/or season | ✓ implemented | `:207` start/end parsing; `:226` season filter |
| R5 | Filter by competition | ✓ implemented | `:82` `_competition_key`; `:224` competition filter |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `:239` `team_stats` |
| R7 | Player search by name | ✓ implemented | `:283` `search_players(name=...)` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `:287` name/nationality/club/position filters; returns overall/potential |
| R9 | Season standings from match results | ✓ implemented | `:298` `standings` computes points/positions (see F1: inflated for overlapping years) |
| R10 | Aggregate statistics | ✓ implemented | `:323` `competition_stats` (goals/match, home-win rate, biggest wins) |
| R11 | Head-to-head between two teams | ✓ implemented | `:263` `head_to_head` |
| R12 | Automated tests of query capabilities | ✓ implemented | `tests/test_brazilian_soccer_mcp.py` (7 tests, all pass) |

## Build & Test

Scores read from `scores.json` (not re-run per the evaluate-run skill):

```text
test_coverage   = 0.86   # build + all tests executed and passed
defect_rate     = 1.0    # build+test succeeded
code_quality    = 0.7889
maintainability = 0.7955
idiomatic       = 0.87
```

Skip scan: `grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/` → 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 403 (`brazilian_soccer_mcp.py`) + 86 (tests) = 489 |
| Files (excl. data/, __pycache__, egg-info) | 14 |
| Dependencies | 0 runtime (stdlib only); setuptools build-only |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. **[high] F1** — Overlapping source files triple-count matches. `standings(2019)` returns `matches_used=1140`, top team Flamengo `matches=114, points=270` vs the true 38-match / 90-point Serie A season. Root cause: `Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, and `BR-Football-Dataset.csv` all resolve to competition "Brasileirao" for overlapping seasons with no dedup. Affects `standings`, `team_stats`, and `competition_stats` for 2012–2019.
2. **[low] F2** — Standings/stats display use raw un-canonicalized team names (e.g. "Flamengo-RJ"); the label depends on which source row was seen first.
3. **[info] R12** — Tests assert W/D/L consistency and point ordering but not absolute counts, so F1 passes undetected.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/brazil/runs/agent=codex_effort=high_language=python_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l
python3 -c "from brazilian_soccer_mcp import SoccerData; t=SoccerData().standings(2019); print(t['matches_used'], t['standings'][0])"
```
