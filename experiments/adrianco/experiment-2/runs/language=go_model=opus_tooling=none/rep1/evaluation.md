# Evaluation: language=go model=opus tooling=none · rep 1

## Summary

- **Factors:** language=go, model=opus, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 2 passed / 0 failed / 11 skipped (2 effective) — skips are environmental (data/kaggle not archived)
- **Build:** pass — `test_coverage=0.051`, `defect_rate=1.0` from `scores.json` (build + tests ran without failure)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 0 low, 2 info)

Mechanical scores read from `scores.json` (inline gate output) — build/test/lint were NOT re-run.
Other stored scores: `maintainability=0.701`, `idiomatic=0.72`, `token_efficiency=0.0189`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `main.go:209` handle() (initialize/tools/list/tools/call), `main.go:44` tools() registers 10 tools |
| R2 | Load provided data/kaggle datasets | ✓ implemented | `soccer/loader.go:182` LoadAll reads 6 CSVs; `main.go:266` default dir `data/kaggle` |
| R3 | Match by team (home/away/either) | ✓ implemented | `soccer/query.go:37` MatchesByTeam; tool `matches_by_team` |
| R4 | Filter by date range and/or season | ✓ implemented | season+competition filter `main.go:134`; `soccer/query.go:83` MatchesBySeason (no explicit date range — see info finding) |
| R5 | Filter by competition | ✓ implemented | `main.go:143` competition substring filter; datasets tagged Brasileirão/Copa/Libertadores in loader |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `soccer/query.go:114` TeamStats; tool `team_stats` |
| R7 | Player search by name | ✓ implemented | `soccer/query.go:272` PlayersByName; tool `find_player` |
| R8 | Filter players by nationality/club, ratings | ✓ implemented | `soccer/query.go:308` TopPlayers (nationality/club/position), `:296` PlayersByClub |
| R9 | Standings computed from matches | ✓ implemented | `soccer/query.go:159` Standings aggregates points/GD from results |
| R10 | Aggregate stats | ✓ implemented | `soccer/query.go:252` AverageGoalsPerMatch, `:230` BiggestWins |
| R11 | Head-to-head between two teams | ✓ implemented | `soccer/query.go:63` H2H; tool `head_to_head` |
| R12 | Automated tests for query capabilities | ✓ implemented | `soccer/soccer_test.go` 13 tests; `test_coverage=0.051>0` ⇒ tests executed |

## Build & Test

Build/test were not re-run — stored mechanical scores stand in (per skill Step 2).

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0189, "test_coverage": 0.051,
              "defect_rate": 1.0, "maintainability": 0.701, "idiomatic": 0.72}
```

```text
go test ./...  (as scored)
defect_rate=1.0  -> build + tests passed (no failures)
test_coverage=0.051 -> low line coverage: 11/13 tests skip because data/kaggle
                       is not present in the archive (soccer_test.go:17 t.Skipf).
Tests that always run: TestNormalizeTeam, TestParseDate.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1139 (main.go + soccer/*.go incl. test) |
| Files | 13 (incl. docs/prompts; 4 .go source/test) |
| Dependencies | 0 (stdlib only; no go.sum) |
| Tests total | 13 |
| Tests effective | 2 (11 skipped on missing data) |
| Skip ratio | 84.6% (environmental — data not archived) |
| Build duration | n/a (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] 11 of 13 tests skip when `data/kaggle` is absent; line coverage only 5.1% — `soccer/soccer_test.go:17`
2. [info] Match filtering exposes season but not an explicit date range — `main.go:55`
3. [info] MCP protocol implemented by hand rather than via an official SDK — `main.go:15-263`

## Reproduce

```bash
cd experiment-2/runs/language=go_model=opus_tooling=none/rep1
cat scores.json                                   # stored mechanical scores
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go"   # skip detection
# tests need datasets to fully run:
SOCCER_DATA_DIR=path/to/data/kaggle go test ./...
```
