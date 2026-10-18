# Evaluation: effort=low_language=swift_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=swift, model=claude-haiku-5-5, effort=low, prompt=neutral, agent=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 58 passed / 0 failed / 0 skipped (58 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` ⇒ `swift build` + `swift test` succeeded (not re-run)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Clean run: all twelve pinned requirements implemented, a 58-test suite with no skips, build and tests green. Scores from the inline gate (`scores.json`): `test_coverage=1.0`, `defect_rate=1.0`, `code_quality=0.83`, `maintainability=0.74`, `idiomatic=0.62`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `MCPServer.swift` (initialize/ping/tools/list/tools/call); `SoccerTools.all` registers 7 tools; `main.swift` serve loop |
| R2 | Loads datasets in data/kaggle | ✓ implemented | `DataLoader.swift:matchFiles` (5 match CSVs) + `fifa_data.csv`; all 6 present in `data/kaggle/` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `find_matches` tool + `MatchFilter.venue` any/home/away; `SoccerDatabase.isMatch:521` |
| R4 | Filter by date range and/or season | ✓ implemented | `MatchFilter.from/to/season`; `isMatch:537-539` inclusive bounds; `testGivenDateRange...BoundsAreInclusive` |
| R5 | Filter by competition (Brasileirão/Copa/Libertadores) | ✓ implemented | `competition` filter; `Libertadores_Matches.csv` + `Brazilian_Cup_Matches.csv` loaded; `canonicalCompetition` |
| R6 | Team record W/L/D + goals for/against | ✓ implemented | `team_record` tool → `SoccerDatabase.record:550`; `TeamRecord` wins/draws/losses/GF/GA |
| R7 | Search players by name | ✓ implemented | `search_players` `name` arg → `searchPlayers:653`; `testGivenNameFragment...` |
| R8 | Filter players by nationality/club with ratings | ✓ implemented | `searchPlayers` nationality/club/position/min_overall; returns Overall/Potential (see finding R8 re dataset) |
| R9 | Standings computed from match results | ✓ implemented | `standings` tool → `SoccerDatabase.standings:566` (3-1-0, GD/GF tiebreak); `testGiven...FlamengoIsChampion` |
| R10 | Aggregate stats (avg goals, home vs away, biggest wins) | ✓ implemented | `league_stats` tool: summary/biggest_wins/best_home_record/best_away_record; `leagueStats:588`, `biggestWins:605` |
| R11 | Head-to-head between two teams | ✓ implemented | `head_to_head` tool → `MatchFilter(team,opponent)` + `record`; `testGivenHeadToHead...` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 58 tests across Parsing/Query/Integration; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate):

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.8333
             maintainability=0.7355  idiomatic=0.62  token_efficiency=0.0058
```

`test_coverage=1.0` ⇒ `swift build` succeeded and all tests passed. Skip scan over
`Tests/` (XCTSkip / disabled / XCTExpectFailure) returned none, so all 58 tests are
effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Sources only) | 1228 |
| Lines of code (incl. tests) | 1729 |
| Test LOC | 501 |
| Files (excl. data/build/.git) | 23 |
| Swift source files | 8 (+3 test files) |
| Tests total | 58 |
| Tests effective | 58 |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both info:

1. [info] R8: player club filter works but FIFA dataset contains no Brazilian clubs (dataset property, tested)
2. [info] arch-1: match-dataset overlap deduped by competition-season priority (documented, tested)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=swift_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # mechanical scores (not re-run)
cat ../../REQUIREMENTS.json                        # pinned 12-item checklist
grep -rE "XCTSkip|\.disabled|XCTExpectFailure" Tests/   # skip scan → none
grep -rc "func test" Tests/                        # 58 test functions
# To verify locally (optional; not required by this skill):
#   swift test
```
