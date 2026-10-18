# Evaluation: effort=low language=python model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 44 test functions (test_real_dataset adds 24 parametrized cases → ~68 effective); 0 skipped; all passed (`defect_rate=1.0`)
- **Build:** pass — stdlib only, no build step (import succeeds; tests ran)
- **Lint:** `code_quality=0.6667` from scores.json (stored); not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores from `scores.json` (inline gate — this run is not yet in `retort.db`):
`test_coverage=0.97`, `defect_rate=1.0`, `code_quality=0.6667`, `maintainability=0.7888`,
`idiomatic=0.70`, `token_efficiency=0.0059`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `server.py:225` JSON-RPC `initialize`/`tools/list`/`tools/call`; `SoccerTools` registers 11 tools (`server.py:43`) |
| R2 | Load & use data/kaggle/ datasets | ✓ implemented | `data.py:189 load_matches` reads 5 match CSVs; `data.py:220 load_players` reads `fifa_data.csv`; `test_real_dataset.py:44` asserts all six contribute |
| R3 | Match query by team (home/away/either) | ✓ implemented | `queries.py:159 find_matches` + `_involves` (`queries.py:192`) honour `venue` home/away/any |
| R4 | Filter by date range and/or season | ✓ implemented | `queries.py:182` `_in_range` + `season` filter; `test_match_queries` + sample Q "date range" |
| R5 | Filter by competition (Brasileirão/Copa/Libertadores) | ✓ implemented | `queries.py:178` competition filter via `names.py:105 resolve_competition`; all three families present (`test_real_dataset.py:49`) |
| R6 | Team W/L/D record with goals for/against | ✓ implemented | `queries.py:200 team_record` → `TeamRecord` (wins/draws/losses/gf/ga/win_rate) |
| R7 | Player search by name | ✓ implemented | `queries.py:355 search_players` folds name, ranks by overall |
| R8 | Filter players by nationality/club with ratings | ✓ implemented | `queries.py:360 list_players` + `_filter_players` (`queries.py:380`); `Player.overall/potential` returned |
| R9 | Standings computed from match results | ✓ implemented | `queries.py:272 standings` tallies points (3/win) from matches, sorts; not hardcoded |
| R10 | Aggregate statistics | ✓ implemented | `queries.py:295 season_stats` (goals/match, home/draw/away rates) + `biggest_wins` (`queries.py:260`) |
| R11 | Head-to-head between two teams | ✓ implemented | `queries.py:234 head_to_head` → `HeadToHead` (a_wins/b_wins/draws) |
| R12 | Automated tests covering the queries | ✓ implemented | 44 test fns across 5 files; `test_coverage=0.97`, `defect_rate=1.0`; 0 skips |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill (inline gate wrote `scores.json`).

```text
scores.json: {"test_coverage": 0.97, "defect_rate": 1.0, "code_quality": 0.667,
              "maintainability": 0.789, "idiomatic": 0.70, "token_efficiency": 0.0059}
# defect_rate=1.0 ⇒ build + all tests passed; test_coverage=0.97 ⇒ 97% line coverage
```

```text
# test functions by file (grep 'def test_')
tests/test_match_queries.py   19
tests/test_mcp_server.py       9
tests/test_player_queries.py   7
tests/test_names.py            3
tests/test_real_dataset.py     6  (+24 parametrized sample questions)
# skipped/xfail: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1146 (`brazilian_soccer_mcp/`) |
| Lines of code (tests) | 612 |
| Files (source + tests) | 12 |
| Dependencies | 0 (standard library only; no requirements.txt/pyproject.toml) |
| Tests total | 44 functions (~68 effective incl. parametrization) |
| Tests effective | ~68 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (no build step) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] `names-1` — Unknown competition filter silently returns zero results instead of signalling (`names.py:113`).
2. [info] `R1` — MCP protocol implemented by hand rather than via the official `mcp` SDK (`server.py:225`); zero-dependency, correctly implemented.
3. [info] `cov-1` — Line coverage is 97%, not 100% (`scores.json`).

No critical/high/medium findings. This is a clean pass: all 12 pinned requirements implemented, all tests pass, no skipped tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=python_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (build/test/lint)
grep -cE "def test_" tests/*.py                   # test counts
grep -rnE "pytest\.skip|xfail" tests/             # skip detection (none)
python -m pytest -q                               # (optional) re-run the suite; stdlib only
python -m brazilian_soccer_mcp.server --data-dir data/kaggle   # launch the MCP stdio server
```
