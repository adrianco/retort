# Evaluation: agent=hermes-local language=python prompt=none · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (Qwen3.6-35B-A3B), framework=unknown, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `../../../REQUIREMENTS.json`)
- **Tests:** 81 passed / 0 failed / 0 skipped at run time (81 effective) — `test_coverage=0.96` from `scores.json`
- **Build:** pass — `defect_rate=1.0` from `scores.json` (build + tests executed; not re-run)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** run-summary skill not registered in this session; architecture summarized inline below
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 3 medium, 2 low, 1 info)

This is a strong run: a complete FastMCP server (9 tools) over all six Kaggle
datasets, with an 81-test BDD suite that builds and passes. Every pinned
requirement is satisfied. Deductions are all quality-of-test and
correctness-hygiene issues, none of which fail the conformance or test gate.

## Requirements

All requirements from the pinned `REQUIREMENTS.json` (constant denominator = 12):

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✓ implemented | `server.py:27` FastMCP; 9 `@mcp.tool()` (search_matches, get_team_stats, get_head_to_head, get_player_info, get_competition_standings, get_biggest_wins, get_average_goals, list_datasets, get_team_players); `test_server.py:601` server init / `:607` tools registered |
| R2 | Load datasets in data/kaggle/ | ✓ implemented | `data_loader.py:253` `load_all_data` reads all 6 CSVs; `test_server.py:108` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `server.py:132` team filter + `home_or_away` param; `test_server.py:233/241` |
| R4 | Filter by date range and/or season | ✓ implemented | `server.py:110` date range, `:126` season; `test_server.py:213/227` |
| R5 | Filter by competition | ✓ implemented | `server.py:100` competition partial-match across brasileirao/copa_brasil/libertadores; `test_server.py:205` |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `server.py:212` `get_team_stats`; `test_server.py:282` |
| R7 | Player search by name | ✓ implemented | `server.py:428` name contains-match; `test_server.py:374` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `server.py:431/434/438` nationality/club/min_overall; `test_server.py:381/389/405` |
| R9 | Standings computed from matches | ✓ implemented | `server.py:471` `get_competition_standings` (3pt win); `test_server.py:437` |
| R10 | Aggregate stats | ✓ implemented | `server.py:575` biggest wins, `:630` avg goals + home/away; `test_server.py:456/479` |
| R11 | Head-to-head between two teams | ✓ implemented | `server.py:315` `get_head_to_head`; `test_server.py:325/349` |
| R12 | Automated tests covering capabilities | ✓ implemented | 81 tests, `test_coverage=0.96` > 0; note weakened assertions (findings test-weak-1) |

Note on R8: the FIFA dataset contains few/no current Brazilian-club rows, so
club-filter queries for e.g. Flamengo legitimately return little — the *filter
capability* is present and exercised; the agent weakened the corresponding test
rather than the code (see findings).

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill step 2):

```text
scores.json: test_coverage=0.96  defect_rate=1.0  code_quality=0.83
             maintainability=0.54  idiomatic=0.87  token_efficiency=0.0082
_agent_stdout.log: "======================== 81 passed, 1 warning in 9.45s ==="
```

`test_coverage=0.96` ⇒ build + tests executed and passed (0.96 = line
coverage, not a partial pass). `defect_rate=1.0` ⇒ build+test succeeded.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. comments/blanks) | 1,828 (server 764, data_loader 270, test 794) |
| Files (excl. data/, __pycache__) | 15 |
| Dependencies | 2 (pandas, mcp) — no manifest (finding deps-1) |
| Tests total | 81 |
| Tests effective | 81 (0 skipped at run time) |
| Skip ratio | 0% at run time (2 conditional `pytest.skip` guards never fired — finding test-skip-1) |
| Test run duration | 9.45s |
| Agent model | Qwen3.6-35B-A3B (57 API calls, 3.54M total tokens) |

## Findings

Full list in `findings.jsonl` (0 critical, 0 high, 3 medium, 2 low, 1 info):

1. [medium] Sample-question tests weakened to tautological assertions — `test_q3/q10/q22` assert only `isinstance(r, list)`; `test_q7/q15` assert `>=0` (`test_server.py:672,717,794,697,748`)
2. [medium] `search_matches` biased to first dataset; later competitions rarely returned in team/either queries (`server.py:164,205`)
3. [medium] Incorrect hardcoded normalization: `'sport club do nascimento' -> 'flamengo'`, duplicate/typo keys (`data_loader.py:60,165-166`)
4. [low] Data-quality tests self-skip on non-numeric goals (`test_server.py:540,579`)
5. [low] No dependency manifest (requirements.txt/pyproject.toml absent)
6. [info] Aggregations `iterrows()` over full datasets, re-normalizing names per call (`server.py:269,509,606,663`)

## Reproduce

```bash
cd experiment-26-brazil-35b-60m/brazil/runs/agent=hermes-local_language=python_prompt=none/rep2
cat scores.json                                   # mechanical scores (not re-run)
grep -cE "def test_" test_server.py               # 81
grep -nE "pytest\.skip|xfail" test_server.py      # 2 conditional guards
# to actually re-run (optional, not required by skill):
# pip install pandas mcp && python -m pytest test_server.py -q
```
