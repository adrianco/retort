# Evaluation: effort=low_language=java_model=claude-fable-5-2_prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=claude-fable-5-2, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `REQUIREMENTS.json`, R1–R12)
- **Tests:** 52 passed / 0 failed / 0 skipped (52 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — not re-run (scored inline; `test_coverage=1.0` ⇒ build + all tests passed)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** `run-summary` skill unavailable in this session; module overview summarised below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

The build/test/lint signals are read from `scores.json` (scored inline during `retort run`),
not re-run, per the evaluate-run contract. `test_coverage=1.0` is the build+test gate:
compilation succeeded and every test passed.

## Requirements

Pinned checklist from `brazil/REQUIREMENTS.json` (constant denominator across all runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `McpServer.java:92` JSON-RPC 2.0 dispatch (`initialize`/`tools/list`/`tools/call`); `Tools.java:273` tool catalogue |
| R2 | Loads & uses provided CSVs in data/kaggle/ | ✓ implemented | `DataStore.java:48-59` loads all 6 CSVs (Historical, Brasileirao, Cup, Libertadores, Extended, FIFA) via `Csv.read` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `SoccerService.java:558-590` `select()` with venue filter; tool `find_matches` (`Tools.java:191`) |
| R4 | Filter by date range and/or season | ✓ implemented | `SoccerService.java:576-581` season + date_from/date_to filtering |
| R5 | Filter by competition | ✓ implemented | `SoccerService.java:520-531` `resolveCompetition` (Brasileirão/Serie B/C, Copa do Brasil, Libertadores) |
| R6 | Team W/L/D record and goals for/against | ✓ implemented | `SoccerService.java:747` `teamStats`; `Rec` tally `SoccerService.java:416-432` |
| R7 | Player search by name | ✓ implemented | `SoccerService.java:1137` `searchPlayers` / `1100` `nameMatches`; tool `search_players` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `SoccerService.java:1116-1135` `selectPlayers` (nationality, club, position, overall); `playerLine` shows ratings |
| R9 | Season standings computed from results | ✓ implemented | `SoccerService.java:885-937` `table()`/`standings` — points from matches, champion + relegation marked |
| R10 | Aggregate statistics | ✓ implemented | `SoccerService.java:1005-1052` `aggregate`/`leagueStats` (avg goals, home/away rates, highest-scoring); `biggestWins` `1078` |
| R11 | Head-to-head between two teams | ✓ implemented | `SoccerService.java:707-743` `headToHead` (W/D/L, home/away split, per-competition) |
| R12 | Automated tests covering query capabilities | ✓ implemented | 52 `@Test` across 4 suites (`SoccerServiceTest` 32, `DataLoadingTest`/`McpServerTest` 8 each, `TeamNamesTest` 4); `test_coverage=1.0` |

Prompt factor `neutral` (prompts/neutral.md) prescribes no methodology and asks for tests —
satisfied by R12; no additional checkable `P*` instructions.

## Build & Test

Not re-run — scores read from `scores.json` (inline scoring during `retort run`):

```text
test_coverage = 1.0   → mvn build + all 52 JUnit tests passed (build+test gate)
code_quality  = 1.0   → lint/quality clean
defect_rate   = 1.0   → build+test succeeded
```

No `@Disabled`, `@Ignore`, `assumeTrue/assumeFalse`, or `enabled=false` markers found in `src/test`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, Java) | 1867 |
| Lines of code (test, Java) | 737 |
| Source files (excl. data/target/.git) | 25 |
| Dependencies | 2 (jackson-databind runtime, junit-jupiter test) |
| Tests total | 52 |
| Tests effective | 52 |
| Skip ratio | 0% |
| Build duration | not re-run (inline-scored) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Implementation substantially exceeds the spec — 15 MCP tools, two-legged tie aggregation, named-derby detection

No missing/partial requirements, no build/test failures, no skipped tests.

## Reproduce

```bash
cd experiments/adrianco/experiment-97-fable52-brazil/brazil/runs/effort=low_language=java_model=claude-fable-5-2_prompt=neutral/rep1
cat scores.json                                  # build/test/lint signals (not re-run)
cat ../../../REQUIREMENTS.json                   # pinned R1–R12 checklist
grep -rc '@Test' src/test/java/br/soccer/mcp/*.java   # 52 tests, 0 skips
# fallback full run (not needed — inline-scored): mvn -q test
```
