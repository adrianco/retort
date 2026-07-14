# Evaluation: language=erlang model=opus-4.8-fast prompt=TDD · rep 1

## Summary

- **Factors:** language=erlang, model=opus-4.8-fast, prompt=TDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 105 passed / 0 failed / 0 skipped (105 effective) — `test_coverage=1.0`
- **Build:** pass — from `test_coverage=1.0` in scores.json / retort.db (not re-run)
- **Lint:** pass — `code_quality=1.0` from scores.json / retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Scores read from `scores.json` and cross-checked against `experiment-14/retort.db`
(completed row): `test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`,
`maintainability=0.885`, `idiomatic=0.8`, `token_efficiency=0.0`. Build/tests/lint
were **not** re-run per the skill (stored scores stand in).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `bsmcp_mcp.erl` JSON-RPC 2.0 (initialize/tools.list/tools.call/ping); `bsmcp_server.erl` stdio loop; `bsmcp_tools:list/0` 6 tools |
| R2 | Loads & uses datasets in data/kaggle/ | ✓ implemented | `bsmcp_data.erl:18-23` 5 match CSVs + `load_players/1` fifa_data.csv via `bsmcp_csv` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `bsmcp_query.erl:27-47` `team`/`home_team`/`away_team` predicates + `involves/2` |
| R4 | Filter by date range and/or season | ✓ implemented | `bsmcp_query.erl:39` season predicate; date-range not exposed (low finding R4) |
| R5 | Filter by competition | ✓ implemented | `bsmcp_query.erl:41` competition predicate; comps tagged in `bsmcp_data.erl:66-105` |
| R6 | Team match history W/L/D + goals | ✓ implemented | `bsmcp_query:team_record/3` (`bsmcp_query.erl:79-133`) wins/draws/losses/goals_for/against/win_rate |
| R7 | Player search by name | ✓ implemented | `bsmcp_query.erl:159` name substring predicate; tool `find_players` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `bsmcp_query.erl:161-166` nationality/club/position; returns `overall`/`potential` |
| R9 | Season standings from match results | ✓ implemented | `bsmcp_query:standings/3` (`bsmcp_query.erl:183-224`) 3pts/win, GD tiebreak, computed |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `avg_goals/1`, `home_win_rate/1`, `biggest_wins/2`; tool `match_statistics` |
| R11 | Head-to-head between two teams | ✓ implemented | `bsmcp_query:head_to_head/3` (`bsmcp_query.erl:53-60`) a_wins/b_wins/draws |
| R12 | Automated tests covering queries | ✓ implemented | 105 eunit tests across 9 modules; `test_coverage=1.0` |
| P1 | TDD prompt: test-first, incremental | ✓ implemented | 105 fine-grained per-behavior tests, no skips; clean pure-function query layer makes test-first plausible |

## Build & Test

Build/test/lint not re-run — stored scores used per skill step 2.

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0, "test_coverage": 1.0,
              "defect_rate": 1.0, "maintainability": 0.885, "idiomatic": 0.8}
retort.db (completed): test_coverage=1.0  code_quality=1.0  defect_rate=1.0
```

```text
# eunit test functions (effective = passed, none skipped)
csv=11  data=15  normalize=17  format=10  query=12  query2=14  tools=11  mcp=12  server=5
total = 105 tests ; skip/ignore/disable grep over test/ = 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src, total) | 1,246 (1,074 non-blank) |
| Lines of code (test, total) | 814 (666 non-blank) |
| Source modules | 10 (+ .app.src) |
| Test modules | 9 |
| Files (excl _build/data/.git) | 32 |
| Dependencies | 0 (`{deps, []}`; uses OTP 27 built-in `json`) |
| Tests total | 105 |
| Tests effective | 105 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

Process metrics (from retort.db, informational): `_turns=112`,
`_tokens≈9.98M`, `_cost≈$17.44`, `token_efficiency=0.0` — very high token
spend for this task, though it produced a complete, fully-tested result.

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] find_matches tool exposes season but not an explicit date-range filter (R4) — `bsmcp_tools.erl:16-26`
2. [low] find_players sort places players with missing Overall rating first (Erlang atom > integer ordering) — `bsmcp_query.erl:147`
3. [info] Strong TDD adherence — 105 fine-grained tests, no skips (P1)
4. [info] Robustness beyond spec: cross-file dedup + accent/suffix normalization + team aliases

No critical, high, or medium findings.

## Reproduce

```bash
cd experiment-14/runs/language=erlang_model=opus-4.8-fast_prompt=TDD/rep1
cat scores.json                          # stored mechanical scores (build/test/lint)
sqlite3 -readonly ../../../retort.db "SELECT metric_name,value FROM run_results WHERE run_id=(SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'\$.language')='erlang' AND json_extract(run_config_json,'\$.model')='opus-4.8-fast' AND json_extract(run_config_json,'\$.prompt')='TDD' AND replicate=1 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
grep -rc "_test" test/*.erl              # test counts per module
grep -rEi "skip|ignore|disable" test/    # skip detection (none)
# To actually rebuild (optional, not part of eval): rebar3 eunit
```
