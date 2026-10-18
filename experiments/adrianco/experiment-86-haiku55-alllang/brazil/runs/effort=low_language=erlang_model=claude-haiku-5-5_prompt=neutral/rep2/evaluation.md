# Evaluation: effort=low language=erlang model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=erlang, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 72 passed / 0 failed / 0 skipped (72 effective)
- **Build:** pass — `test_coverage=1.0` from scores.json
- **Lint:** pass — `code_quality=1.0` from scores.json (`warnings_as_errors` is on, so a clean build already means zero warnings)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `bsm_mcp.erl` JSON-RPC 2.0 (initialize/tools/list/tools/call); `bsm_tools:definitions/0` (7 tools); tested `bsm_mcp_tests.erl` |
| R2 | Load & use data/kaggle datasets | ✓ implemented | `bsm_loader.erl:121` reads all 6 CSVs; BDD "All six CSV files contribute data" `bsm_bdd_tests.erl:110` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `bsm_query:find_matches/2` + `side/3`/`teams_ok/2` with venue; `bsm_query_tests.erl:41` |
| R4 | Filter by date range / season | ✓ implemented | `season_ok/2`, `date_ok/3` `bsm_query.erl:424-429`; tested `bsm_query_tests.erl:49` |
| R5 | Filter by competition across datasets | ✓ implemented | `competition_ok/2` substring; Serie A + Copa do Brasil + Libertadores loaded `bsm_loader.erl:122` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `bsm_query:team_record/3` → `summarise/2`; `bsm_query_tests.erl:63` |
| R7 | Player search by name | ✓ implemented | `bsm_query:search_players/2` name fold; `bsm_tools.erl` search_players tool |
| R8 | Players by nationality/club + ratings | ✓ implemented | `player_ok/2` nationality/club/min_overall `bsm_query.erl:523`; returns overall/potential |
| R9 | Season standings computed from matches | ✓ implemented | `bsm_query:standings/2` 3/1/0 points; BDD reproduces exact 2019 table `bsm_bdd_tests.erl:54` |
| R10 | Aggregate statistics | ✓ implemented | `bsm_query:league_stats/2` avg goals, home/draw/away %, biggest wins; `bsm_query_tests.erl:97` |
| R11 | Head-to-head between two teams | ✓ implemented | `bsm_query:head_to_head/4`; `bsm_query_tests.erl:88` |
| R12 | Automated tests over query capabilities | ✓ implemented | 4 EUnit modules, 72 tests, `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (computed by retort's scorers — not re-run per skill guidance):

```text
{"code_quality": 1.0, "token_efficiency": 0.0, "test_coverage": 1.0,
 "defect_rate": 1.0, "maintainability": 0.893, "idiomatic": 0.85}
```

```text
rebar3 eunit  (from _agent_stdout.log, final run)
All 72 tests passed.
```

`test_coverage=1.0` ⇒ build succeeded and every test executed and passed. Intermediate runs in the log show transient failures during development that were fixed before the final green run. `rebar.config` sets `warnings_as_errors`, so the clean build also implies no compiler warnings.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. header) | 912 |
| Lines of code (tests) | 479 |
| Source files (.erl/.hrl, src+include) | 11 |
| Test files | 4 |
| Dependencies (external) | 0 (OTP `json` + `persistent_term` only) |
| Tests total | 72 |
| Tests effective | 72 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`) — no critical/high/medium items:

1. [low] 2019/2012 standings reproduce the spec exactly; the 2023 Serie A table derives from an incomplete feed (377 matches). Standings logic is correct; it is a data-coverage limitation the agent documented.
2. [info] Zero external dependencies; read-only dataset held in `persistent_term`.
3. [info] Thorough domain normalisation — team aliases, UF/country states, accent folding, cross-source de-duplication.
4. [info] MCP protocol exercised via piped JSON-RPC and unit tests, not a live MCP client.

## Reproduce

```bash
cd experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=erlang_model=claude-haiku-5-5_prompt=neutral/rep2
cat scores.json                        # stored mechanical scores (no re-run)
cat ../../REQUIREMENTS.json            # pinned 12-requirement checklist
grep -c "All 72 tests passed" _agent_stdout.log
# To re-run tests manually (requires OTP 27+):  rebar3 eunit
```
