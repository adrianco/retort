# Evaluation: language=typescript_model=opus_tooling=beads · rep 1

## Summary

- **Factors:** language=typescript, model=opus, tooling=beads
- **Status:** failed (test_coverage=0.0 — tests did not execute in scoring environment)
- **Requirements:** 11/12 implemented, 1 partial, 0 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — test_coverage=0.0 from retort.db
- **Build:** fail — test_coverage=0.0 indicates build/test pipeline did not complete
- **Lint:** unavailable — code_quality=0.0 from retort.db
- **Architecture:** MCP server with 7 tools, custom CSV parser, team name normalization
- **Findings:** 2 items in `findings.jsonl` (1 critical, 1 high, 0 medium, 0 low, 0 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/index.ts:2-7,124-178` — Server from `@modelcontextprotocol/sdk`, 7 tools registered via ListToolsRequestSchema/CallToolRequestSchema |
| R2 | Loads datasets from data/kaggle/ | ✓ implemented | `src/data.ts:87-165` — reads all 6 CSVs (Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro, fifa_data) |
| R3 | Match query: find by team (home, away, either) | ✓ implemented | `src/queries.ts:17-20` — findMatches filters by `team`, `homeTeam`, `awayTeam` |
| R4 | Match query: filter by date range/season | ✓ implemented | `src/queries.ts:22-24` — `dateFrom`, `dateTo`, `season` filters |
| R5 | Match query: filter by competition | ✓ implemented | `src/queries.ts:21` — competition filter with case-insensitive includes across Brasileirão, Copa do Brasil, Libertadores |
| R6 | Team query: W/L/D record + goals for/against | ✓ implemented | `src/queries.ts:49-101` — `teamStats()` returns wins, draws, losses, goalsFor, goalsAgainst, home/away splits, points |
| R7 | Player query: search by name | ✓ implemented | `src/queries.ts:220-225` — `findPlayers()` name filter with case-insensitive includes |
| R8 | Player query: filter by nationality/club with ratings | ✓ implemented | `src/queries.ts:226-229` — nationality, club, position, minOverall filters; returns overall, potential ratings |
| R9 | Competition: season standings from matches | ✓ implemented | `src/queries.ts:156-208` — `standings()` computes W/L/D/points/GD from match results, sorted by points then GD |
| R10 | Statistical analysis: aggregate stats | ✓ implemented | `src/queries.ts:246-270` `overallStats()` (avg goals/match, home/away win rates) + `src/queries.ts:272-280` `biggestWins()` |
| R11 | Head-to-head records between two teams | ✓ implemented | `src/queries.ts:115-142` — `headToHead()` returns W/L/D, goals, and recent matches |
| R12 | Automated tests covering query capabilities | ~ partial | `test/queries.test.ts` has 12 tests covering all 7 query functions, BUT test_coverage=0.0 — tests did not execute |

## Build & Test

```text
Stored scores from retort.db (tests NOT re-run per skill constraints):
  test_coverage=0.0  (build+tests did NOT execute)
  code_quality=0.0
  defect_rate=0.0
  maintainability=0.0
  idiomatic=0.0
  token_efficiency=0.0

All scores are zero, indicating the scoring pipeline could not build/run this
project — most likely due to missing data/kaggle/ CSV files and/or npm install
failure in the scoring environment.

Test file: test/queries.test.ts (12 tests using node:test)
Test command: node --test --import tsx test/*.test.ts
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (TypeScript only) | 827 |
| Files (total excl. node_modules) | 20 |
| Source files (.ts) | 5 |
| Dependencies | 4 (1 runtime + 3 dev) |
| Tests written | 12 |
| Tests effective | 0 (did not execute) |
| Skip ratio | 0% (no skipped tests in source) |
| Build duration | N/A (scorer failed) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [critical] Test gate failed: test_coverage=0.0 — tests did not execute
2. [high] 12 tests written but none executed

## Code Quality Notes

Despite the test execution failure, the implementation is well-structured:
- Custom RFC-compliant CSV parser handles quoted fields and CRLF (`src/csv.ts`)
- Team name normalization strips state suffixes, handles accents via NFD decomposition (`src/data.ts:32-55`)
- All 6 required CSV files are loaded with schema-appropriate field mapping
- Query functions are cleanly separated from MCP server wiring
- Tests cover all 7 query tools with assertions on correctness invariants

## Reproduce

```bash
cd experiment-2/runs/language=typescript_model=opus_tooling=beads/rep1
# Verify stored scores:
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='typescript' AND json_extract(er.run_config_json,'\$.model')='opus' AND json_extract(er.run_config_json,'\$.tooling')='beads' AND er.replicate=1 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1) AND rr.metric_name IN ('test_coverage','code_quality','defect_rate');"
# Check for skipped tests:
grep -rE '\.skip\(|xit\(|xdescribe\(|it\.todo\(' test/ --include="*.ts" 2>/dev/null | wc -l
```
