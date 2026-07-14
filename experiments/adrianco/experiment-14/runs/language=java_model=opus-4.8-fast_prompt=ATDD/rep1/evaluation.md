# Evaluation: language=java_model=opus-4.8-fast_prompt=ATDD · rep 1

## Summary

- **Factors:** language=java, model=opus-4.8-fast, prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 22 passed / 0 failed / 0 skipped (22 effective) — from `test_coverage=1.0`
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests passed, from retort.db run_id=21)
- **Lint:** pass — code_quality=1.0 (retort.db)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

Mechanical scores read from `scores.json` / `retort.db` (not re-run, per skill):
`test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.665`,
`idiomatic=0.8`, `token_efficiency=0.0099`.

## Requirements

Checklist is the pinned `experiment-14/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `McpServer.java:31` JSON-RPC handle; `registerTools` registers 6 tools; `McpProtocolAcceptanceTest` handshake/discovery |
| R2 | Loads provided `data/kaggle` CSVs | ✓ implemented | `DataStore.java:51` loads all 6 CSVs via Commons CSV; files present in `data/kaggle/` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `SoccerService.java:39` toolFindMatches + `matchesVenue`; test `restricts_a_team_to_its_home_fixtures` |
| R4 | Filter matches by date range and/or season | ✓ implemented | `SoccerService.java:43` season filter; test `finds_the_matches_a_team_played_in_a_given_season` (date-range not a param — see finding R4) |
| R5 | Filter by competition | ✓ implemented | `SoccerService.java:42` Competition.resolve; `Competition.java`; test `filters_matches_by_competition` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `SoccerService.java:117` toolTeamStats; test `reports_a_teams_record_consistently` |
| R7 | Player search by name | ✓ implemented | `SoccerService.java:163` toolSearchPlayers name filter; test `looks_up_a_player_by_name` |
| R8 | Players by nationality/club + ratings | ✓ implemented | `SoccerService.java:174-180` nationality/club/position/minOverall; tests `finds_brazilian_players_sorted_by_rating`, `filters_players_by_club` |
| R9 | Season standings computed from matches | ✓ implemented | `SoccerService.java:193` toolStandings (points=3W+D); test `calculates_the_2019_brasileirao_final_standings` (Flamengo 90 pts) |
| R10 | Aggregate statistics | ✓ implemented | `SoccerService.java:238` toolLeagueStatistics (avg goals, home/away rates, biggest wins); tests `computes_league_wide_statistics`, `surfaces_the_biggest_wins_ordered_by_margin` |
| R11 | Head-to-head between two teams | ✓ implemented | `SoccerService.java:73` toolHeadToHead; test `compares_two_teams_head_to_head` |
| R12 | Automated tests covering queries | ✓ implemented | 22 JUnit 5 tests across 6 classes; test_coverage=1.0 |

### Prompt factor (ATDD)

The `prompt=ATDD` factor was in effect. The run conforms to it:
- Tests exercise the SUT **only through the public MCP interface** — `McpTestClient.java:16` does JSON-RPC `initialize`/`tools/list`/`tools/call` with no internal access.
- Tests assert on **what** the system does in domain language (e.g. `finds_all_matches_between_two_rival_teams`, `calculates_the_2019_brasileirao_final_standings`), not implementation mechanics.
- Each scenario boots a **fresh server** in `@BeforeEach setUp()` — atomic and independent.
- Finer-grained unit TDD underneath (`TeamNamesTest`) covers the normalization internals.

## Build & Test

Not re-run — mechanical results read from retort.db (skill step 2).

```text
test_coverage = 1.0   ⇒ Maven build succeeded AND all 22 tests passed
defect_rate   = 1.0   ⇒ build + test success
code_quality  = 1.0   ⇒ clean lint/quality
(retort.db experiment_runs id=21, status=completed, replicate=1)
```

Skip scan: `grep -rE "@Disabled|assumeTrue|@Ignore" src/test` → 0 matches. No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, src/) | 1775 (main 1286 / test 489) |
| Java files | 15 (8 main + 7 test) |
| Files (excl data/, target/) | 26 |
| Maven dependencies | 3 (Jackson, Commons CSV, JUnit) |
| Tests total | 22 |
| Tests effective | 22 |
| Skip ratio | 0% |
| maintainability | 0.665 |
| idiomatic | 0.80 |
| token_efficiency | 0.0099 (3.02M tokens, 42 turns, $8.50, 915s) |

## Findings

Top items (full list in `findings.jsonl` — 0 critical/high/medium):

1. [low] R4 — match filtering is season-only; no explicit date-range params (requirement met via "and/or").
2. [info] ATDD acceptance tests correctly drive the SUT only through the MCP protocol.
3. [info] Tool schema advertises serie_b/serie_c beyond the three required competitions.
4. [info] Low token efficiency for this run (long ATDD build-up; comparison context only).

## Reproduce

```bash
cd experiment-14/runs/language=java_model=opus-4.8-fast_prompt=ATDD/rep1
cat scores.json                                  # mechanical scores (build/test/lint)
grep -rE "@Disabled|assumeTrue|@Ignore" src/test # skip scan (0)
grep -rc "@Test" src/test                        # 22 tests
mvn -q test                                       # (only if re-verifying; build+tests pass)
```
