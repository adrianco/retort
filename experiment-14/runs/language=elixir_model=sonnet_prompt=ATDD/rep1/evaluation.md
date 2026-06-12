# Evaluation: language=elixir_model=sonnet_prompt=ATDD · rep 1

## Summary

- **Factors:** language=elixir, model=sonnet, prompt=ATDD (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json R1–R12)
- **Tests:** 28 passed / 0 failed / 0 skipped (28 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — from `test_coverage=1.0` / `defect_rate=1.0` (scores.json; not re-run)
- **Lint:** pass — `code_quality=1.0` from scores.json (0 warnings)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

Other stored scores: maintainability=0.67, idiomatic=0.87, token_efficiency=0.0.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `server.ex:33-61` tools/list + tools/call, `stdio_runner.ex` transport, 5 tools registered |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `data_store.ex:50-189` loads all 6 CSVs into ETS via NimbleCSV |
| R3 | Match by team (home/away/either) | ✓ implemented | `data_store.ex:310-319` `teams_match?`; `find_matches.ex` |
| R4 | Filter by date range and/or season | ✓ implemented | season filter `data_store.ex:265-266`, `find_matches.ex:11` (season; no explicit date-range — info finding) |
| R5 | Filter by competition | ✓ implemented | `data_store.ex:203-213` `resolve_datasets` maps Brasileirao/Copa/Libertadores |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `get_team_stats.ex:27-74` |
| R7 | Player search by name | ✓ implemented | `data_store.ex:334-338`, `find_players.ex` name filter |
| R8 | Player by nationality/club + ratings | ✓ implemented | `data_store.ex:340-354`; output includes Overall `find_players.ex:40-43` |
| R9 | Standings computed from matches | ✓ implemented | `get_competition_standings.ex:30-67` computes pts/W/D/L/GD |
| R10 | Aggregate stats | ✓ implemented | `get_statistics.ex` — biggest_wins, goals_per_match, home_away_record, best_home_teams |
| R11 | Head-to-head between two teams | ✓ implemented | `find_matches.ex:69-97` head_to_head_summary (attribution fragile — low finding) |
| R12 | Automated tests of query capabilities | ✓ implemented | `test/acceptance/mcp_tools_test.exs` 27 tests; `test_coverage=1.0` |

### Prompt-factor (ATDD) conformance

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Translate requirements into executable acceptance tests | ✓ implemented | `test/acceptance/mcp_tools_test.exs` covers all 5 tools / requirement categories |
| P2 | Exercise SUT only through public interface, no back-door | ✓ implemented | tests call `Server.handle_request/1` with JSON-RPC maps (`:25`, `:46`); no direct ETS/DataStore access |
| P3 | Assert on WHAT not HOW, in domain language | ✓ implemented | assertions on response text (scores, win counts, standings) not internals |
| P4 | Atomic/independent; each scenario starts empty, shares no data | ~ partial | `:7-11` shared pre-loaded dataset, no per-test fixtures/teardown |
| P5 | Tests fail first, then drive implementation | cannot-verify | final-state-only; no history available |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
code_quality=1.0  test_coverage=1.0  defect_rate=1.0
maintainability=0.6724  idiomatic=0.87  token_efficiency=0.0
```

`test_coverage=1.0` ⇒ `mix test` built and all tests passed. 28 tests (27 acceptance + 1 smoke), 0 skipped (no `@tag :skip`/`:pending` in test/).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (lib, source only) | 1380 |
| Lines of code (test) | 380 |
| Files (lib+test) | 15 |
| Dependencies | 2 (jason, nimble_csv) |
| Tests total | 28 |
| Tests effective | 28 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] P4 — Acceptance tests do not start from an empty system; they share the globally-loaded dataset (`mcp_tools_test.exs:7-11`).
2. [low] R11 — Head-to-head win attribution uses substring matching, fragile for overlapping team names (`find_matches.ex:75-86`).
3. [low] CSV per-row parse errors silently rescued and skipped (`data_store.ex:362-377`).
4. [info] R4 — Match filtering supports season only, not an explicit date range (`find_matches.ex:7-14`).

No critical or high findings — the run builds, lints clean, and passes all 28 tests with full requirement coverage.

## Reproduce

```bash
cd experiment-14/runs/language=elixir_model=sonnet_prompt=ATDD/rep1
cat scores.json                 # mechanical scores (build/test/lint already computed)
cat ../../../REQUIREMENTS.json  # pinned R1–R12 checklist
cat ../../../prompts/ATDD.md     # prompt-factor instructions (P1–P5)
grep -rEn "@tag :skip|@tag :pending" test/   # skip check (none)
# Optional re-run (not required; scores already stored):
# mix deps.get && mix test
```
