# Evaluation: language=erlang · model=opus-4.8-fast · prompt=ATDD · rep 1

## Summary

- **Factors:** language=erlang, model=opus-4.8-fast, prompt=ATDD, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 31 passed / 0 failed / 0 skipped (31 effective) — from `test_coverage=1.0`
- **Build:** pass — via stored `test_coverage=1.0` (build+test gate) in `retort.db` / `scores.json`
- **Lint:** pass — `code_quality=1.0` (stored)
- **Architecture:** run-summary skill unavailable in this environment — see module map below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Checklist is the pinned `experiment-14/REQUIREMENTS.json` (12 fixed items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/bsoccer_mcp.erl:30` `handle/1` JSON-RPC 2.0; `tool_specs/0:130` advertises 7 tools; initialize/tools/list/tools/call dispatched at `:49-55` |
| R2 | Load & use provided datasets in data/kaggle | ✓ implemented | `src/bsoccer_data.erl:79-87` loads all 6 CSVs into ETS; `data/kaggle/` holds all 6 files; acceptance `all_datasets_are_loaded_and_queryable:117` asserts >10000 matches |
| R3 | Match query by team (home/away/either) | ✓ implemented | `bsoccer_query:find_matches/1:28`; tested `find_all_matches_between_two_teams:137` |
| R4 | Filter by date range and/or season | ✓ implemented | `find_matches` reads `start_date`/`end_date` (`bsoccer_query.erl:33-34`) and `season`; tested `find_matches_for_a_team_in_a_season:150` |
| R5 | Filter by competition | ✓ implemented | `find_matches` competition arg; tested `find_matches_by_competition:163` (Libertadores) |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `bsoccer_query:team_statistics/1:109`; tested `team_statistics_for_a_season:188` (exact 28W/6D/4L/90pts) |
| R7 | Player search by name | ✓ implemented | `bsoccer_query:search_players/1:258`; tested `search_player_by_name:255` (Neymar overall=92) |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `search_players` nationality/club/position/sort args; tested `search_brazilian_players:263`, `search_players_by_club:272` |
| R9 | Season standings computed from matches | ✓ implemented | `bsoccer_query:competition_standings/1:152` (3 pts/win); tested `league_standings_crown_the_champion:236` (Flamengo 90 pts, sorted) |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `bsoccer_query:aggregate_statistics/1:221`; tested `aggregate_statistics_for_a_competition:292`, `biggest_wins_are_reported:304` |
| R11 | Head-to-head between two teams | ✓ implemented | `bsoccer_query:head_to_head/1:68`; tested `head_to_head_record_is_consistent:173` (W1+W2+D==Total) |
| R12 | Automated tests covering queries | ✓ implemented | `test/bsoccer_acceptance_tests.erl` (20 scenarios) + `bsoccer_csv_tests.erl` (5) + `bsoccer_norm_tests.erl` (6); `test_coverage=1.0` |

### Prompt-factor (ATDD) adherence

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Acceptance tests through public interface only, no back-door | ✓ implemented | `bsoccer_acceptance_tests.erl:337-365` — rpc/call/raw_call go only through `bsoccer_mcp:handle/1`; header comment :5-9 makes the "no internal access" intent explicit |
| P2 | Assert WHAT not HOW, in domain language | ✓ implemented | Scenario names + assertions are domain-level (head-to-head invariant `:182`, standings sorted `:248`, partition invariants `:201`) |
| P3 | Finer-grained unit TDD underneath | ✓ implemented | `bsoccer_csv_tests.erl`, `bsoccer_norm_tests.erl` cover CSV parsing & name normalisation internals |
| P4 | Tests written as executable spec, fail-first then drive impl | ✓ implemented | Suite is structured as an executable specification (see header :2-20); fail-first ordering can't be verified post-hoc from the archive but structure is consistent |

## Build & Test

Not re-run — stored mechanical scores used per skill policy.

```text
scores.json: {"test_coverage": 1.0, "code_quality": 1.0, "defect_rate": 1.0,
              "maintainability": 0.642, "idiomatic": 0.87, "token_efficiency": 0.0}
retort.db (completed run): test_coverage=1.0  defect_rate=1.0  code_quality=1.0
```

`test_coverage=1.0` ⇒ `rebar3 eunit` built and all tests passed. No skips found
(`{timeout, 30, ...}` wrappers in the acceptance suite are eunit per-test
timeouts, not skips).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src) | 1,495 |
| Lines of code (test) | 451 |
| Source files (src/) | 10 (9 .erl + app.src) |
| Test files | 3 |
| Dependencies (rebar) | 0 (OTP-only; `json` from OTP 27+) |
| Tests total | 31 |
| Tests effective | 31 |
| Skip ratio | 0% |
| Build | pass (stored) |

## Findings

Full list in `findings.jsonl` (no critical/high/medium):

1. [low] Extended match stats (shots/corners) loaded but never surfaced by any tool — `bsoccer_data.erl:183-186`
2. [info] ATDD followed: acceptance suite drives impl through the public MCP interface only
3. [info] token_efficiency=0.0 (verbose run) — correctness/quality unaffected

## Reproduce

```bash
cd experiment-14/runs/language=erlang_model=opus-4.8-fast_prompt=ATDD/rep1
cat scores.json                     # stored mechanical scores (build+test gate)
rebar3 eunit                        # re-run suite if desired (31 tests, all pass)
```
