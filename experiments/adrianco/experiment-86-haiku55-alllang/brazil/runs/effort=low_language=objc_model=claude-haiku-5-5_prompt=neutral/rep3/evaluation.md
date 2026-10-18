# Evaluation: effort=low language=objc model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=objc, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 102 passed / 0 failed / 0 skipped (102 effective)
- **Build:** pass (clang `-fobjc-arc`, `-framework Foundation`) — from `scores.json` test_coverage=1.0
- **Lint:** pass — code_quality=1.0 (built with `-Wall -Wextra`, no warnings surfaced)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

All 12 pinned requirements from `REQUIREMENTS.json` are implemented and exercised by the
test suite. The suite runs against the real `data/kaggle` datasets (20,106 matches,
18,207 players) — the real-dataset scenario is **not** skipped in this archive. The agent
fixed its one initial test failure (a head-to-head display-name assertion) before the run
finished; the final state is 102 passed, 0 failed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/MCPServer.m:34` initialize/tools-list/tools-call/ping; `src/Tools.m:106` 6 tool descriptors |
| R2 | Loads provided data/kaggle datasets | ✓ implemented | `src/DataStore.m:85` storeFromDirectory loads all 6 CSVs; log: "Loaded 20106 matches and 18207 players from data/kaggle" |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/DataStore.m:155` matchesForTeam with MatchVenue; `src/Tools.m:175` search_matches |
| R4 | Filter by date range / season | ✓ implemented | `src/DataStore.m:163` season filter; `src/Tools.m:32` SeasonArg; test `ScenarioMatchQueries` in2023 |
| R5 | Filter by competition (Brasileirão/Copa/Libertadores) | ✓ implemented | `src/DataStore.m:162` competition filter; `src/Tools.m:45` CompetitionArg; sources span all competitions |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/DataStore.m:189` tallyForTeam; `src/Tools.m:211` team_stats; test `ScenarioTeamStatistics` |
| R7 | Player search by name | ✓ implemented | `src/DataStore.m:264` playersMatching name; `src/Tools.m:295` search_players; test `ScenarioPlayerSearch` messi |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `src/DataStore.m:272-275` nationality/club/position/overall; returns Overall/Position/Club |
| R9 | Season standings computed from matches | ✓ implemented | `src/DataStore.m:203` standingsForCompetition (points/GD/GF tiebreak); test `ScenarioStandings`; 2019 table in log |
| R10 | Aggregate statistics | ✓ implemented | `src/DataStore.m:225` statisticsForCompetition (avg goals, home/draw/away %, biggest wins) |
| R11 | Head-to-head between two teams | ✓ implemented | `src/Tools.m:239` head_to_head; `src/DataStore.m:155` opponent filter; test `ScenarioHeadToHead` |
| R12 | Automated tests covering queries | ✓ implemented | `tests/test_main.m` 14 scenarios; 102 passed / 0 failed; test_coverage=1.0 |

## Build & Test

```text
make test
cc -fobjc-arc -Wall -Wextra -Wno-unused-parameter -O2 -Isrc -o build/tests \
   src/CSVParser.m src/Text.m src/Models.m src/DataStore.m src/Tools.m src/MCPServer.m \
   tests/test_main.m -framework Foundation
./build/tests
```

```text
Scenario: CSV parsing handles quotes, CRLF, BOM and embedded newlines
...
Scenario: Given the provided Kaggle datasets, every file is queryable
102 passed, 0 failed
```

(Scores read from `scores.json`: test_coverage=1.0, code_quality=1.0, defect_rate=1.0 —
build/test not re-run, per skill.)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `.m`+`.h`) | 1237 |
| Lines of code (tests) | 454 |
| Source files | 14 (13 src + 1 test) |
| Dependencies | 0 (Foundation only) |
| Tests total | 102 (assertions across 14 scenarios) |
| Tests effective | 102 |
| Skip ratio | 0% |
| test_coverage | 1.0 |
| code_quality | 1.0 |
| maintainability | 0.757 |
| idiomatic | 0.35 |
| token_efficiency | 0.0142 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Implementation exceeds spec: stdio transport, ping, Serie B/C, venue filters
2. [info] Low idiomatic score (0.35) despite code_quality=1.0 — stylistic metric only

No correctness, build, test, or requirement defects found.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=objc_model=claude-haiku-5-5_prompt=neutral/rep3
cat scores.json                 # stored mechanical scores (no re-run)
make test                       # 102 passed, 0 failed (requires data/kaggle)
grep -rniE "t\.Skip|@skip|#\[ignore\]" tests/   # 0 skips
```
