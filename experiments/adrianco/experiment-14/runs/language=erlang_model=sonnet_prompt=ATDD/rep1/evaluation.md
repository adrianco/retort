# Evaluation: language=erlang_model=sonnet_prompt=ATDD · rep 1

## Summary

- **Factors:** language=erlang, model=sonnet, prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `experiment-14/REQUIREMENTS.json`)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — Common Test acceptance suite
- **Build:** pass — from `test_coverage=1.0` in `scores.json` (build + tests executed)
- **Lint:** pass — from `code_quality=1.0` in `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 2 info)

Mechanical scores read from `scores.json` (not re-run): `test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.643`, `idiomatic=0.72`, `token_efficiency=0.0`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/soccer_mcp.erl:46-94` JSON-RPC 2.0 (initialize/tools/list/tools/call); `src/soccer_tools.erl:9-94` 6 tool defs |
| R2 | Loads data/kaggle/ datasets | ✓ implemented | `src/soccer_data.erl:56-81` loads all 5 match CSVs + fifa_data.csv; `data/kaggle/` has all 6 files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/soccer_data.erl:178-179` team criterion checks home OR away; test ac03 |
| R4 | Filter by date range / season | ✓ implemented | `src/soccer_data.erl:186-191` season + date_from/date_to; test ac04 |
| R5 | Filter by competition | ✓ implemented | `src/soccer_data.erl:184-185`; tests ac04/ac14/ac15 cover brasileirao/copa_do_brasil/libertadores |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `src/soccer_data.erl:304-339` compute_team_stats; test ac06 |
| R7 | Player search by name | ✓ implemented | `src/soccer_data.erl:208-209`; test ac07 |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `src/soccer_data.erl:210-213`, format_player returns overall/potential; tests ac08/ac09 |
| R9 | Season standings from match results | ✓ implemented | `src/soccer_data.erl:261-302` computes points/positions; test ac11 (2019 champion) |
| R10 | Aggregate stats | ✓ implemented | `src/soccer_data.erl:341-382` biggest_wins + avg_goals/home-away rates; tests ac12/ac13 |
| R11 | Head-to-head between two teams | ✓ implemented | `src/soccer_data.erl:220-259` get_head_to_head; test ac10 |
| R12 | Automated tests for query capabilities | ✓ implemented | `test/soccer_mcp_SUITE.erl` 15 cases; test_coverage=1.0 |

**Prompt factor (ATDD):** The acceptance suite is written from an external user's perspective and exercises the SUT only through the MCP protocol (`send_request`/`call_tool` → `soccer_mcp:handle_message/1`), asserting on domain outcomes (find matches, team stats, standings) rather than internals — satisfying the ATDD prompt. Minor deviation: scenarios share a suite-wide read-only dataset rather than each starting from an empty system (finding P1, low).

## Build & Test

Not re-run — mechanical scores were already computed and stored in `scores.json`:

```text
test_coverage = 1.0   # build succeeded AND all tests executed and passed
code_quality  = 1.0
defect_rate   = 1.0   # build+test succeeded
```

Test suite: `test/soccer_mcp_SUITE.erl` declares 15 acceptance cases (`ac01..ac15`) in `all/0`. No skips/xfail/disabled cases found (`grep` for skip/ignore markers → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 900 (4 .erl modules + app.src) |
| Lines of code (tests) | 363 |
| Files (excl. data/, _build/) | 16 |
| Dependencies | 0 (rebar.config deps=[]) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json, not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] F1 — CSV load failures silently swallowed to an empty dataset (`src/soccer_data.erl:64-81` `catch _:_ -> []`)
2. [low] P1 — Acceptance tests share a suite-wide dataset rather than per-scenario empty/isolated state (ATDD independence directive)
3. [low] F2 — List queries support `limit` but no offset/pagination (`src/soccer_tools.erl:106-112,150-156`)
4. [info] F3 — Zero third-party deps; OTP `json` + bespoke CSV parser
5. [info] F4 — Team stats add home/away breakdown beyond the required W/L/D + goals

No critical or high-severity findings: the run builds, all 15 acceptance tests pass, and all 12 pinned requirements are implemented.

## Reproduce

```bash
cd experiment-14/runs/language=erlang_model=sonnet_prompt=ATDD/rep1
# Mechanical scores already stored — do not re-run. To verify independently:
rebar3 ct          # runs test/soccer_mcp_SUITE.erl (needs data/kaggle/ CSVs present)
# Skip detection:
grep -rEn '\{skip|ct:fail|\{skipped|\{ignore' src test | wc -l   # -> 0
```
